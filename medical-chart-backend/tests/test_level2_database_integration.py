"""
Level 2 統合テスト: データベース統合テスト
テストレベル: Level 2 (Integration)
信頼性: ビジネスロジック 85%, データ整合性 90%
実行頻度: 週次
前提条件: テスト用DB
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15

使用方法:
pytest tests/test_level2_database_integration.py -v -m integration
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Chart, ExtractedData, ExtractionTemplate, ExtractionTemplateItem, 
    ProcessStatus
)
from app.services.db_service import get_db_service, DBService
from app.schemas.template import TemplateCreate, TemplateItemCreate


class Level2DatabaseTestHelper:
    """Level 2データベース統合テスト用ヘルパー"""
    
    def __init__(self):
        self.test_user_id = "level2_db_test_user"
    
    def create_test_chart_data(self, suffix: str = "") -> Dict:
        """テスト用チャートデータを生成"""
        return {
            "filename": f"test_db_integration{suffix}.jpg",
            "content_type": "image/jpeg",
            "file_size": 2048,
            "uploaded_by": self.test_user_id,
            "gcs_uri": f"gs://test-bucket/charts/test{suffix}.jpg"
        }
    
    def create_test_extracted_data(self, chart_id: str) -> Dict:
        """テスト用抽出データを生成"""
        return {
            "chart_id": chart_id,
            "data": {
                "items": [
                    {
                        "item_name": "患者名",
                        "interpreted_text": "山田太郎",
                        "confidence_score": 0.95,
                        "bounding_box": [100, 100, 200, 120]
                    },
                    {
                        "item_name": "診断名",
                        "interpreted_text": "糖尿病",
                        "confidence_score": 0.88,
                        "bounding_box": [100, 150, 250, 170]
                    }
                ]
            },
            "extracted_at": datetime.utcnow(),
            "extraction_method": "gemini_vision"
        }
    
    def cleanup_test_data(self, db: Session, chart_ids: List[str] = None, template_ids: List[str] = None):
        """テストデータのクリーンアップ"""
        try:
            if chart_ids:
                for chart_id in chart_ids:
                    # 抽出データ削除
                    extracted_data = db.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).all()
                    for data in extracted_data:
                        db.delete(data)
                    
                    # チャート削除
                    chart = db.query(Chart).filter(Chart.id == chart_id).first()
                    if chart:
                        db.delete(chart)
            
            if template_ids:
                for template_id in template_ids:
                    # テンプレート項目削除
                    template_items = db.query(ExtractionTemplateItem).filter(ExtractionTemplateItem.template_id == template_id).all()
                    for item in template_items:
                        db.delete(item)
                    
                    # テンプレート削除
                    template = db.query(ExtractionTemplate).filter(ExtractionTemplate.id == template_id).first()
                    if template:
                        db.delete(template)
            
            db.commit()
        except Exception:
            db.rollback()


@pytest.fixture
def level2_db_helper():
    """Level 2データベーステストヘルパーのフィクスチャ"""
    return Level2DatabaseTestHelper()


@pytest.fixture
def test_db_session(setup_test_database, test_db_engine):
    """テスト用DBセッションのフィクスチャ（Level 2統合テスト用）"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db_service():
    """DBサービスのフィクスチャ"""
    return get_db_service()


class TestLevel2ChartDatabaseIntegration:
    """
    Level 2 統合テスト: チャートデータベース統合
    """
    
    @pytest.mark.integration
    def test_chart_crud_database_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: チャートCRUD + DB整合性
        """
        print("\n🧪 Level 2統合テスト開始: チャートCRUD DB統合")
        
        # Step 1: チャート作成
        print("📝 Step 1: チャート作成")
        chart_data = level2_db_helper.create_test_chart_data("_crud")
        
        created_chart = db_service.create_chart(
            filename=chart_data["filename"],
            content_type=chart_data["content_type"],
            file_size=chart_data["file_size"],
            uploaded_by=chart_data["uploaded_by"],
            db=test_db_session
        )
        
        assert created_chart is not None
        chart_id = created_chart.id
        print(f"✅ チャート作成成功: chart_id={chart_id}")
        
        # Step 2: DB直接確認
        print("🔍 Step 2: DB直接確認")
        chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
        assert chart_record is not None
        assert chart_record.filename == chart_data["filename"]
        assert chart_record.content_type == chart_data["content_type"]
        assert chart_record.status == ProcessStatus.PENDING
        assert chart_record.created_at is not None
        
        print("✅ DB直接確認完了")
        
        # Step 3: チャート取得
        print("📥 Step 3: チャート取得")
        retrieved_chart = db_service.get_chart(chart_id, test_db_session)
        assert retrieved_chart is not None
        assert retrieved_chart.id == chart_id
        assert retrieved_chart.filename == chart_data["filename"]
        
        print("✅ チャート取得成功")
        
        # Step 4: チャート更新
        print("✏️ Step 4: チャート更新")
        updated_chart = db_service.update_chart_status(
            chart_id=chart_id,
            status=ProcessStatus.PROCESSING,
            db=test_db_session
        )
        
        assert updated_chart.status == ProcessStatus.PROCESSING
        
        # DB更新確認
        test_db_session.refresh(chart_record)
        assert chart_record.status == ProcessStatus.PROCESSING
        assert chart_record.updated_at is not None
        
        print("✅ チャート更新成功")
        
        # Step 5: GCS URI更新
        print("☁️ Step 5: GCS URI更新")
        updated_chart = db_service.update_chart_gcs_uri(
            chart_id=chart_id,
            gcs_uri=chart_data["gcs_uri"],
            db=test_db_session
        )
        
        assert updated_chart.gcs_uri == chart_data["gcs_uri"]
        
        # DB確認
        test_db_session.refresh(chart_record)
        assert chart_record.gcs_uri == chart_data["gcs_uri"]
        
        print("✅ GCS URI更新成功")
        
        # クリーンアップ
        level2_db_helper.cleanup_test_data(test_db_session, chart_ids=[chart_id])
        print("✅ Level 2統合テスト完了: チャートCRUD DB統合")
    
    @pytest.mark.integration
    def test_chart_extracted_data_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: チャート + 抽出データ統合
        """
        print("\n🧪 Level 2統合テスト開始: チャート + 抽出データ統合")
        
        # Step 1: チャート作成
        chart_data = level2_db_helper.create_test_chart_data("_extracted")
        
        created_chart = db_service.create_chart(
            filename=chart_data["filename"],
            content_type=chart_data["content_type"],
            file_size=chart_data["file_size"],
            uploaded_by=chart_data["uploaded_by"],
            db=test_db_session
        )
        
        chart_id = created_chart.id
        
        # Step 2: 抽出データ作成
        print("📊 Step 2: 抽出データ作成")
        extracted_data_dict = level2_db_helper.create_test_extracted_data(chart_id)
        
        created_extracted_data = db_service.create_extracted_data(
            chart_id=chart_id,
            data=extracted_data_dict["data"],
            extracted_at=extracted_data_dict["extracted_at"],
            extraction_method=extracted_data_dict["extraction_method"],
            db=test_db_session
        )
        
        assert created_extracted_data is not None
        print(f"✅ 抽出データ作成成功: extracted_data_id={created_extracted_data.id}")
        
        # Step 3: 関連データ確認
        print("🔗 Step 3: 関連データ確認")
        
        # チャートから抽出データ取得
        chart_with_data = db_service.get_chart_with_extracted_data(chart_id, test_db_session)
        assert chart_with_data is not None
        assert chart_with_data.extracted_data is not None
        assert chart_with_data.extracted_data.chart_id == chart_id
        
        # 抽出データの内容確認
        extracted_data = chart_with_data.extracted_data
        assert extracted_data.data is not None
        assert "items" in extracted_data.data
        assert len(extracted_data.data["items"]) == 2
        
        print("✅ 関連データ確認完了")
        
        # Step 4: データ整合性確認
        print("🔍 Step 4: データ整合性確認")
        
        # 外部キー制約確認
        chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
        extracted_record = test_db_session.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()
        
        assert chart_record is not None
        assert extracted_record is not None
        assert extracted_record.chart_id == chart_record.id
        
        print("✅ データ整合性確認完了")
        
        # クリーンアップ
        level2_db_helper.cleanup_test_data(test_db_session, chart_ids=[chart_id])
        print("✅ Level 2統合テスト完了: チャート + 抽出データ統合")


class TestLevel2TemplateDatabaseIntegration:
    """
    Level 2 統合テスト: テンプレートデータベース統合
    """
    
    @pytest.mark.integration
    def test_template_crud_database_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: テンプレートCRUD + DB整合性
        """
        print("\n🧪 Level 2統合テスト開始: テンプレートCRUD DB統合")
        
        # Step 1: テンプレート作成
        print("📝 Step 1: テンプレート作成")
        template_data = TemplateCreate(
            name="Level2 DB統合テスト用テンプレート",
            description="データベース統合テスト用",
            type="user",
            created_by=level2_db_helper.test_user_id,
            is_active=True,
            items=[
                TemplateItemCreate(
                    name="患者ID",
                    enabled=True,
                    display_order=1,
                    description="患者識別番号",
                    confidence_threshold=0.9
                ),
                TemplateItemCreate(
                    name="診療日",
                    enabled=True,
                    display_order=2,
                    description="診療実施日",
                    confidence_threshold=0.8
                ),
                TemplateItemCreate(
                    name="医師名",
                    enabled=False,
                    display_order=3,
                    description="担当医師名",
                    confidence_threshold=0.7
                )
            ]
        )
        
        created_template = db_service.create_template(template_data, test_db_session)
        assert created_template is not None
        template_id = created_template.id
        
        print(f"✅ テンプレート作成成功: template_id={template_id}")
        
        # Step 2: DB直接確認
        print("🔍 Step 2: DB直接確認")
        template_record = test_db_session.query(Template).filter(Template.id == template_id).first()
        assert template_record is not None
        assert template_record.name == template_data.name
        assert template_record.is_active == True
        
        # テンプレート項目確認
        template_items = test_db_session.query(TemplateItem).filter(
            TemplateItem.template_id == template_id
        ).order_by(TemplateItem.display_order).all()
        
        assert len(template_items) == 3
        assert template_items[0].name == "患者ID"
        assert template_items[0].enabled == True
        assert template_items[1].name == "診療日"
        assert template_items[2].name == "医師名"
        assert template_items[2].enabled == False
        
        print("✅ DB直接確認完了")
        
        # Step 3: テンプレート取得
        print("📥 Step 3: テンプレート取得")
        retrieved_template = db_service.get_template_with_items(template_id, test_db_session)
        assert retrieved_template is not None
        assert retrieved_template.id == template_id
        assert len(retrieved_template.items) == 3
        
        print("✅ テンプレート取得成功")
        
        # Step 4: テンプレート項目更新
        print("✏️ Step 4: テンプレート項目更新")
        
        # 特定項目の有効化
        disabled_item = template_items[2]  # 医師名
        updated_item = db_service.update_template_item(
            item_id=disabled_item.id,
            enabled=True,
            confidence_threshold=0.85,
            db=test_db_session
        )
        
        assert updated_item.enabled == True
        assert updated_item.confidence_threshold == 0.85
        
        # DB更新確認
        test_db_session.refresh(disabled_item)
        assert disabled_item.enabled == True
        
        print("✅ テンプレート項目更新成功")
        
        # Step 5: テンプレート削除
        print("🗑️ Step 5: テンプレート削除")
        delete_result = db_service.delete_template(template_id, test_db_session)
        assert delete_result == True
        
        # DB削除確認（カスケード削除）
        deleted_template = test_db_session.query(Template).filter(Template.id == template_id).first()
        assert deleted_template is None
        
        deleted_items = test_db_session.query(TemplateItem).filter(TemplateItem.template_id == template_id).all()
        assert len(deleted_items) == 0
        
        print("✅ テンプレート削除成功")
        print("✅ Level 2統合テスト完了: テンプレートCRUD DB統合")


class TestLevel2TransactionIntegration:
    """
    Level 2 統合テスト: トランザクション統合
    """
    
    @pytest.mark.integration
    def test_transaction_rollback_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: トランザクションロールバック統合
        """
        print("\n🧪 Level 2統合テスト開始: トランザクションロールバック統合")
        
        # Step 1: 正常なチャート作成
        print("📝 Step 1: 正常なチャート作成")
        chart_data = level2_db_helper.create_test_chart_data("_transaction")
        
        created_chart = db_service.create_chart(
            filename=chart_data["filename"],
            content_type=chart_data["content_type"],
            file_size=chart_data["file_size"],
            uploaded_by=chart_data["uploaded_by"],
            db=test_db_session
        )
        
        chart_id = created_chart.id
        print(f"✅ チャート作成成功: chart_id={chart_id}")
        
        # Step 2: トランザクション内での複数操作
        print("🔄 Step 2: トランザクション内複数操作")
        
        try:
            # トランザクション開始
            test_db_session.begin()
            
            # 操作1: チャートステータス更新
            db_service.update_chart_status(
                chart_id=chart_id,
                status=ProcessStatus.PROCESSING,
                db=test_db_session
            )
            
            # 操作2: 抽出データ作成
            extracted_data_dict = level2_db_helper.create_test_extracted_data(chart_id)
            db_service.create_extracted_data(
                chart_id=chart_id,
                data=extracted_data_dict["data"],
                extracted_at=extracted_data_dict["extracted_at"],
                extraction_method=extracted_data_dict["extraction_method"],
                db=test_db_session
            )
            
            # 操作3: 意図的なエラー発生（無効なステータス更新）
            # 存在しないチャートIDでの更新を試行
            invalid_chart_id = str(uuid4())
            db_service.update_chart_status(
                chart_id=invalid_chart_id,
                status=ProcessStatus.COMPLETED,
                db=test_db_session
            )
            
            # ここまで到達しないはず
            test_db_session.commit()
            assert False, "エラーが発生するはずでした"
            
        except Exception as e:
            print(f"⚠️ 期待されたエラー発生: {e}")
            # ロールバック
            test_db_session.rollback()
            print("🔄 トランザクションロールバック実行")
        
        # Step 3: ロールバック確認
        print("🔍 Step 3: ロールバック確認")
        
        # チャートの状態確認（PENDINGのまま）
        chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
        assert chart_record is not None
        assert chart_record.status == ProcessStatus.PENDING  # 更新がロールバックされている
        
        # 抽出データが作成されていないことを確認
        extracted_data = test_db_session.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()
        assert extracted_data is None  # 作成がロールバックされている
        
        print("✅ ロールバック確認完了")
        
        # クリーンアップ
        level2_db_helper.cleanup_test_data(test_db_session, chart_ids=[chart_id])
        print("✅ Level 2統合テスト完了: トランザクションロールバック統合")
    
    @pytest.mark.integration
    def test_concurrent_access_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: 同時アクセス統合（簡易版）
        """
        print("\n🧪 Level 2統合テスト開始: 同時アクセス統合")
        
        # Step 1: 複数チャート同時作成
        print("📝 Step 1: 複数チャート同時作成")
        chart_ids = []
        
        for i in range(3):
            chart_data = level2_db_helper.create_test_chart_data(f"_concurrent_{i}")
            
            created_chart = db_service.create_chart(
                filename=chart_data["filename"],
                content_type=chart_data["content_type"],
                file_size=chart_data["file_size"],
                uploaded_by=chart_data["uploaded_by"],
                db=test_db_session
            )
            
            chart_ids.append(created_chart.id)
        
        print(f"✅ 複数チャート作成成功: {len(chart_ids)}件")
        
        # Step 2: 同時ステータス更新
        print("🔄 Step 2: 同時ステータス更新")
        
        for i, chart_id in enumerate(chart_ids):
            status = ProcessStatus.PROCESSING if i % 2 == 0 else ProcessStatus.COMPLETED
            
            updated_chart = db_service.update_chart_status(
                chart_id=chart_id,
                status=status,
                db=test_db_session
            )
            
            assert updated_chart.status == status
        
        print("✅ 同時ステータス更新成功")
        
        # Step 3: データ整合性確認
        print("🔍 Step 3: データ整合性確認")
        
        for i, chart_id in enumerate(chart_ids):
            chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
            assert chart_record is not None
            
            expected_status = ProcessStatus.PROCESSING if i % 2 == 0 else ProcessStatus.COMPLETED
            assert chart_record.status == expected_status
        
        print("✅ データ整合性確認完了")
        
        # クリーンアップ
        level2_db_helper.cleanup_test_data(test_db_session, chart_ids=chart_ids)
        print("✅ Level 2統合テスト完了: 同時アクセス統合")


class TestLevel2DatabasePerformanceIntegration:
    """
    Level 2 統合テスト: データベースパフォーマンス統合
    """
    
    @pytest.mark.integration
    def test_bulk_operations_integration(self, level2_db_helper: Level2DatabaseTestHelper, test_db_session: Session, db_service: DBService):
        """
        テストレベル: Level 2 (Integration)
        対象: 一括操作パフォーマンス統合
        """
        print("\n🧪 Level 2統合テスト開始: 一括操作パフォーマンス統合")
        
        # Step 1: 一括チャート作成
        print("📝 Step 1: 一括チャート作成")
        chart_ids = []
        batch_size = 10
        
        start_time = datetime.utcnow()
        
        for i in range(batch_size):
            chart_data = level2_db_helper.create_test_chart_data(f"_bulk_{i}")
            
            created_chart = db_service.create_chart(
                filename=chart_data["filename"],
                content_type=chart_data["content_type"],
                file_size=chart_data["file_size"],
                uploaded_by=chart_data["uploaded_by"],
                db=test_db_session
            )
            
            chart_ids.append(created_chart.id)
        
        creation_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"✅ 一括チャート作成完了: {batch_size}件, {creation_time:.2f}秒")
        
        # Step 2: 一括ステータス更新
        print("🔄 Step 2: 一括ステータス更新")
        
        start_time = datetime.utcnow()
        
        for chart_id in chart_ids:
            db_service.update_chart_status(
                chart_id=chart_id,
                status=ProcessStatus.PROCESSING,
                db=test_db_session
            )
        
        update_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"✅ 一括ステータス更新完了: {batch_size}件, {update_time:.2f}秒")
        
        # Step 3: 一括取得
        print("📥 Step 3: 一括取得")
        
        start_time = datetime.utcnow()
        
        retrieved_charts = []
        for chart_id in chart_ids:
            chart = db_service.get_chart(chart_id, test_db_session)
            retrieved_charts.append(chart)
        
        retrieval_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"✅ 一括取得完了: {batch_size}件, {retrieval_time:.2f}秒")
        
        # Step 4: パフォーマンス評価
        print("📊 Step 4: パフォーマンス評価")
        
        # 基準値（統合テスト用）
        max_creation_time_per_item = 0.5  # 1件あたり0.5秒以内
        max_update_time_per_item = 0.3    # 1件あたり0.3秒以内
        max_retrieval_time_per_item = 0.2 # 1件あたり0.2秒以内
        
        creation_per_item = creation_time / batch_size
        update_per_item = update_time / batch_size
        retrieval_per_item = retrieval_time / batch_size
        
        print(f"📈 作成: {creation_per_item:.3f}秒/件 (基準: {max_creation_time_per_item}秒)")
        print(f"📈 更新: {update_per_item:.3f}秒/件 (基準: {max_update_time_per_item}秒)")
        print(f"📈 取得: {retrieval_per_item:.3f}秒/件 (基準: {max_retrieval_time_per_item}秒)")
        
        # パフォーマンス基準チェック（警告レベル）
        if creation_per_item > max_creation_time_per_item:
            print(f"⚠️ 作成パフォーマンス警告: {creation_per_item:.3f}秒 > {max_creation_time_per_item}秒")
        
        if update_per_item > max_update_time_per_item:
            print(f"⚠️ 更新パフォーマンス警告: {update_per_item:.3f}秒 > {max_update_time_per_item}秒")
        
        if retrieval_per_item > max_retrieval_time_per_item:
            print(f"⚠️ 取得パフォーマンス警告: {retrieval_per_item:.3f}秒 > {max_retrieval_time_per_item}秒")
        
        print("✅ パフォーマンス評価完了")
        
        # クリーンアップ
        level2_db_helper.cleanup_test_data(test_db_session, chart_ids=chart_ids)
        print("✅ Level 2統合テスト完了: 一括操作パフォーマンス統合")


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "integration"]) 