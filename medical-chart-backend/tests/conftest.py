"""
Level 2 統合テスト用 pytest 設定
テストレベル: Level 2 (Integration)
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Base


# テストマーカー定義
def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "integration: Level 2統合テストマーカー"
    )
    config.addinivalue_line(
        "markers", "api: API統合テストマーカー"
    )
    config.addinivalue_line(
        "markers", "service: サービス統合テストマーカー"
    )
    config.addinivalue_line(
        "markers", "database: データベース統合テストマーカー"
    )
    config.addinivalue_line(
        "markers", "performance: パフォーマンステストマーカー"
    )


# テスト用データベース設定
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "postgresql://test_user:test_password@localhost:5432/test_medical_charts"
)

# テスト用エンジンとセッション
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    echo=False  # テスト時はSQLログを無効化
)

TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=test_engine
)


@pytest.fixture(scope="session")
def test_db_engine():
    """テスト用データベースエンジンのセッションスコープフィクスチャ"""
    return test_engine


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """テスト用データベースセッションのファンクションスコープフィクスチャ"""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def test_client(test_db_session: Session) -> TestClient:
    """テスト用FastAPIクライアントのフィクスチャ"""
    
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def setup_test_database(test_db_engine):
    """テスト用データベースのセットアップ（Level 2統合テスト用）"""
    # テーブル作成
    Base.metadata.create_all(bind=test_db_engine)
    yield
    # テーブル削除
    Base.metadata.drop_all(bind=test_db_engine)


@pytest.fixture
def integration_test_config():
    """統合テスト用設定のフィクスチャ"""
    return {
        "test_timeout": 60,  # 統合テストのタイムアウト（秒）
        "max_retry_count": 3,  # リトライ回数
        "test_bucket": "test-medical-charts-integration",
        "test_api_key": "test-api-key-level2-integration",
        "performance_thresholds": {
            "api_response_time": 2.0,  # API応答時間閾値（秒）
            "db_operation_time": 1.0,  # DB操作時間閾値（秒）
            "file_upload_time": 5.0,   # ファイルアップロード時間閾値（秒）
        }
    }


@pytest.fixture
def mock_external_services():
    """外部サービスのモック設定フィクスチャ"""
    return {
        "gcs_enabled": os.getenv("TEST_GCS_ENABLED", "false").lower() == "true",
        "gemini_enabled": os.getenv("TEST_GEMINI_ENABLED", "false").lower() == "true",
        "mock_responses": {
            "gcs_upload_success": True,
            "gemini_extraction_success": True,
        }
    }


# テスト実行時の環境変数設定
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """テスト環境の設定（セッション開始時に自動実行）"""
    # テスト用環境変数設定
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"  # テスト時はログレベルを上げる
    
    # テスト用GCS設定
    if not os.getenv("TEST_GCS_ENABLED"):
        os.environ["TEST_GCS_ENABLED"] = "false"
    
    # テスト用Gemini設定
    if not os.getenv("TEST_GEMINI_ENABLED"):
        os.environ["TEST_GEMINI_ENABLED"] = "false"
    
    yield
    
    # クリーンアップ
    test_env_vars = ["TESTING", "LOG_LEVEL", "TEST_GCS_ENABLED", "TEST_GEMINI_ENABLED"]
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


# テスト結果収集用フィクスチャ
@pytest.fixture(scope="session")
def test_results_collector():
    """テスト結果収集用のフィクスチャ"""
    results = []
    yield results
    
    # セッション終了時にレポート生成
    if results:
        from test_level2_report_generator import Level2TestReportGenerator
        
        generator = Level2TestReportGenerator()
        for result in results:
            generator.add_test_result(result)
        
        summary = generator.generate_summary()
        
        # レポート保存
        json_path = generator.save_json_report(summary)
        md_path = generator.save_markdown_report(summary)
        
        print(f"\n📊 Level 2統合テストレポート生成完了:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")


# パフォーマンステスト用フィクスチャ
@pytest.fixture
def performance_monitor():
    """パフォーマンス監視用のフィクスチャ"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.get_duration()
        
        def get_duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0
        
        def add_metric(self, name: str, value: float):
            self.metrics[name] = value
        
        def get_metrics(self):
            return self.metrics.copy()
    
    return PerformanceMonitor()


# データベーステスト用ヘルパーフィクスチャ
@pytest.fixture
def db_test_helper(test_db_session: Session):
    """データベーステスト用ヘルパーのフィクスチャ"""
    
    class DBTestHelper:
        def __init__(self, session: Session):
            self.session = session
            self.created_records = []
        
        def create_test_chart(self, **kwargs):
            from app.db.models import Chart, ProcessStatus
            
            chart_data = {
                "filename": "test_chart.jpg",
                "content_type": "image/jpeg",
                "file_size": 1024,
                "uploaded_by": "test_user",
                "status": ProcessStatus.PENDING,
                **kwargs
            }
            
            chart = Chart(**chart_data)
            self.session.add(chart)
            self.session.commit()
            self.session.refresh(chart)
            
            self.created_records.append(("chart", chart.id))
            return chart
        
        def create_test_template(self, **kwargs):
            from app.db.models import Template
            
            template_data = {
                "name": "Test Template",
                "description": "Test template description",
                "type": "user",
                "created_by": "test_user",
                "is_active": True,
                **kwargs
            }
            
            template = Template(**template_data)
            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)
            
            self.created_records.append(("template", template.id))
            return template
        
        def cleanup(self):
            """作成したテストレコードをクリーンアップ"""
            from app.db.models import Chart, Template, ExtractedData, TemplateItem
            
            for record_type, record_id in reversed(self.created_records):
                try:
                    if record_type == "chart":
                        # 関連する抽出データも削除
                        extracted_data = self.session.query(ExtractedData).filter(
                            ExtractedData.chart_id == record_id
                        ).all()
                        for data in extracted_data:
                            self.session.delete(data)
                        
                        chart = self.session.query(Chart).filter(Chart.id == record_id).first()
                        if chart:
                            self.session.delete(chart)
                    
                    elif record_type == "template":
                        # 関連するテンプレート項目も削除
                        template_items = self.session.query(TemplateItem).filter(
                            TemplateItem.template_id == record_id
                        ).all()
                        for item in template_items:
                            self.session.delete(item)
                        
                        template = self.session.query(Template).filter(Template.id == record_id).first()
                        if template:
                            self.session.delete(template)
                    
                    self.session.commit()
                except Exception as e:
                    self.session.rollback()
                    print(f"クリーンアップエラー: {e}")
            
            self.created_records.clear()
    
    helper = DBTestHelper(test_db_session)
    yield helper
    helper.cleanup()


# テスト実行時のフック
def pytest_runtest_setup(item):
    """各テスト実行前のセットアップ"""
    # 統合テストマーカーがある場合の特別な設定
    if item.get_closest_marker("integration"):
        # 統合テスト用の追加設定があればここに記述
        pass


def pytest_runtest_teardown(item, nextitem):
    """各テスト実行後のクリーンアップ"""
    # 統合テストマーカーがある場合の特別なクリーンアップ
    if item.get_closest_marker("integration"):
        # 統合テスト用の追加クリーンアップがあればここに記述
        pass 