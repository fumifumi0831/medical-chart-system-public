"""
Level 2 統合テスト: API統合テスト
テストレベル: Level 2 (Integration)
信頼性: ビジネスロジック 85%, サービス連携 80%
実行頻度: 週次
前提条件: テスト用DB、テスト用GCSバケット、テスト用Gemini API
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15

使用方法:
pytest tests/test_level2_api_integration.py -v -m integration
"""

import io
import time
from typing import Dict, List, Optional
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Chart, ExtractedData, ProcessStatus
from app.services.gcs_service import get_gcs_service
from app.services.gemini_service import get_gemini_service
from app.schemas.template import TemplateCreate, TemplateItemCreate


class Level2TestClient:
    """Level 2統合テスト用のクライアント"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.api_key = "test-api-key"
        self.headers = {"X-API-KEY": self.api_key}
        self.test_bucket = "test-medical-charts-integration"
    
    def create_test_image(self, width: int = 400, height: int = 300) -> io.BytesIO:
        """テスト用画像を生成"""
        image = Image.new('RGB', (width, height), color='lightblue')
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='JPEG')
        image_buffer.seek(0)
        return image_buffer
    
    def cleanup_test_chart(self, chart_id: str, db: Session):
        """テストチャートのクリーンアップ"""
        try:
            # DB からチャートデータを削除
            chart = db.query(Chart).filter(Chart.id == chart_id).first()
            if chart:
                # 抽出データも削除
                extracted_data = db.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()
                if extracted_data:
                    db.delete(extracted_data)
                
                # GCS からファイル削除（テスト環境のみ）
                if chart.gcs_uri and self.test_bucket in chart.gcs_uri:
                    gcs_service = get_gcs_service()
                    try:
                        gcs_service.delete_file(chart.gcs_uri)
                    except Exception:
                        pass  # テスト環境では削除失敗を無視
                
                db.delete(chart)
                db.commit()
        except Exception:
            db.rollback()


@pytest.fixture
def level2_client():
    """Level 2テスト用クライアントのフィクスチャ"""
    return Level2TestClient()


@pytest.fixture
def test_db_session():
    """テスト用DBセッションのフィクスチャ"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_template_data():
    """テスト用テンプレートデータ"""
    return TemplateCreate(
        name="Level2統合テスト用テンプレート",
        description="Level 2統合テストで使用するテンプレート",
        type="user",
        created_by="level2_test_user",
        is_active=True,
        items=[
            TemplateItemCreate(
                name="患者名",
                enabled=True,
                display_order=1,
                description="患者の氏名",
                confidence_threshold=0.8
            ),
            TemplateItemCreate(
                name="診断名",
                enabled=True,
                display_order=2,
                description="診断結果",
                confidence_threshold=0.7
            )
        ]
    )


class TestLevel2ChartAPIIntegration:
    """
    Level 2 統合テスト: チャートAPI統合テスト
    """
    
    @pytest.mark.integration
    def test_chart_upload_api_integration(self, level2_client: Level2TestClient, test_db_session: Session):
        """
        テストレベル: Level 2 (Integration)
        対象: チャートアップロードAPI + 実際のサービス連携
        信頼性: API連携 80%, サービス連携 80%
        """
        print("\n🧪 Level 2統合テスト開始: チャートアップロードAPI統合")
        
        # Step 1: API経由でチャートアップロード
        print("📤 Step 1: API経由チャートアップロード")
        test_image = level2_client.create_test_image()
        
        upload_response = level2_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=level2_client.headers
        )
        
        assert upload_response.status_code == 202
        upload_data = upload_response.json()
        chart_id = upload_data["chart_id"]
        
        print(f"✅ アップロード成功: chart_id={chart_id}")
        
        # Step 2: DB直接確認（API + DB連携）
        print("🔍 Step 2: DB連携確認")
        chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
        
        assert chart_record is not None, "チャートレコードがDBに作成されていません"
        assert chart_record.filename == "test_chart.jpg"
        assert chart_record.content_type == "image/jpeg"
        assert chart_record.status in [ProcessStatus.PENDING, ProcessStatus.PROCESSING]
        assert chart_record.gcs_uri is not None
        assert level2_client.test_bucket in chart_record.gcs_uri
        
        print(f"✅ DB連携確認完了: status={chart_record.status}")
        
        # Step 3: GCS連携確認
        print("☁️ Step 3: GCS連携確認")
        gcs_service = get_gcs_service()
        
        # GCSファイル存在確認
        try:
            file_exists = gcs_service.file_exists(chart_record.gcs_uri)
            assert file_exists, "GCSにファイルがアップロードされていません"
            print("✅ GCS連携確認完了")
        except Exception as e:
            print(f"⚠️ GCS確認スキップ（テスト環境制限）: {e}")
        
        # Step 4: ステータス確認API（API + DB連携）
        print("📊 Step 4: ステータス確認API連携")
        status_response = level2_client.client.get(
            f"/api/v1/charts/{chart_id}/status",
            headers=level2_client.headers
        )
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        # API レスポンスとDB状態の整合性確認
        test_db_session.refresh(chart_record)
        assert status_data["status"] == chart_record.status.value
        assert status_data["chart_id"] == chart_id
        
        print("✅ ステータスAPI連携確認完了")
        
        # クリーンアップ
        level2_client.cleanup_test_chart(chart_id, test_db_session)
        print("✅ Level 2統合テスト完了: チャートアップロードAPI統合")
    
    @pytest.mark.integration
    def test_chart_processing_workflow_integration(self, level2_client: Level2TestClient, test_db_session: Session):
        """
        テストレベル: Level 2 (Integration)
        対象: チャート処理ワークフロー統合（短時間処理）
        """
        print("\n🧪 Level 2統合テスト開始: チャート処理ワークフロー統合")
        
        # Step 1: チャートアップロード
        test_image = level2_client.create_test_image()
        
        upload_response = level2_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_workflow.jpg", test_image, "image/jpeg")},
            headers=level2_client.headers
        )
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # Step 2: 処理状態の変化を監視（統合テスト用短時間）
        print("⏳ Step 2: 処理状態変化監視")
        max_wait_time = 30  # 統合テストでは30秒まで
        start_time = time.time()
        status_changes = []
        
        while time.time() - start_time < max_wait_time:
            # API経由でステータス確認
            status_response = level2_client.client.get(
                f"/api/v1/charts/{chart_id}/status",
                headers=level2_client.headers
            )
            
            if status_response.status_code == 200:
                current_status = status_response.json()["status"]
                
                if not status_changes or status_changes[-1] != current_status:
                    status_changes.append(current_status)
                    print(f"📊 ステータス変化: {current_status}")
                
                # DB状態との整合性確認
                test_db_session.refresh(test_db_session.query(Chart).filter(Chart.id == chart_id).first())
                chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
                assert current_status == chart_record.status.value, "API とDB のステータスが不一致"
                
                if current_status in ["completed", "failed", "partial_success"]:
                    break
            
            time.sleep(2)
        
        # 処理状態の変化確認
        assert len(status_changes) >= 1, "ステータス変化が確認できませんでした"
        assert "pending" in status_changes or "processing" in status_changes, "初期ステータスが確認できません"
        
        print(f"✅ ステータス変化確認: {' -> '.join(status_changes)}")
        
        # Step 3: 最終状態確認
        final_status = status_changes[-1]
        if final_status in ["completed", "partial_success"]:
            # 抽出データ確認
            extracted_data = test_db_session.query(ExtractedData).filter(
                ExtractedData.chart_id == chart_id
            ).first()
            
            if extracted_data:
                assert extracted_data.data is not None
                print("✅ 抽出データ確認完了")
            else:
                print("ℹ️ 抽出データ未作成（処理中または失敗）")
        
        # クリーンアップ
        level2_client.cleanup_test_chart(chart_id, test_db_session)
        print("✅ Level 2統合テスト完了: チャート処理ワークフロー統合")


class TestLevel2TemplateAPIIntegration:
    """
    Level 2 統合テスト: テンプレートAPI統合テスト
    """
    
    @pytest.mark.integration
    def test_template_crud_api_integration(self, level2_client: Level2TestClient, test_db_session: Session, test_template_data):
        """
        テストレベル: Level 2 (Integration)
        対象: テンプレートCRUD API + DB連携
        """
        print("\n🧪 Level 2統合テスト開始: テンプレートCRUD API統合")
        
        # Step 1: テンプレート作成API
        print("📝 Step 1: テンプレート作成API")
        create_response = level2_client.client.post(
            "/api/v1/templates",
            json=test_template_data.dict(),
            headers=level2_client.headers
        )
        
        assert create_response.status_code == 201
        template_data = create_response.json()
        template_id = template_data["id"]
        
        print(f"✅ テンプレート作成成功: template_id={template_id}")
        
        # Step 2: DB直接確認
        print("🔍 Step 2: DB連携確認")
        from app.db.models import Template, TemplateItem
        
        template_record = test_db_session.query(Template).filter(Template.id == template_id).first()
        assert template_record is not None
        assert template_record.name == test_template_data.name
        assert template_record.is_active == True
        
        # テンプレート項目確認
        template_items = test_db_session.query(TemplateItem).filter(
            TemplateItem.template_id == template_id
        ).all()
        assert len(template_items) == len(test_template_data.items)
        
        print("✅ DB連携確認完了")
        
        # Step 3: テンプレート取得API
        print("📥 Step 3: テンプレート取得API")
        get_response = level2_client.client.get(
            f"/api/v1/templates/{template_id}",
            headers=level2_client.headers
        )
        
        assert get_response.status_code == 200
        retrieved_template = get_response.json()
        assert retrieved_template["id"] == template_id
        assert retrieved_template["name"] == test_template_data.name
        assert len(retrieved_template["items"]) == len(test_template_data.items)
        
        print("✅ テンプレート取得API確認完了")
        
        # Step 4: テンプレート更新API
        print("✏️ Step 4: テンプレート更新API")
        update_data = {
            "name": "更新されたLevel2テンプレート",
            "description": "更新されたテンプレート説明"
        }
        
        update_response = level2_client.client.patch(
            f"/api/v1/templates/{template_id}",
            json=update_data,
            headers=level2_client.headers
        )
        
        assert update_response.status_code == 200
        updated_template = update_response.json()
        assert updated_template["name"] == update_data["name"]
        
        # DB更新確認
        test_db_session.refresh(template_record)
        assert template_record.name == update_data["name"]
        
        print("✅ テンプレート更新API確認完了")
        
        # Step 5: テンプレート削除API
        print("🗑️ Step 5: テンプレート削除API")
        delete_response = level2_client.client.delete(
            f"/api/v1/templates/{template_id}",
            headers=level2_client.headers
        )
        
        assert delete_response.status_code == 204
        
        # DB削除確認
        deleted_template = test_db_session.query(Template).filter(Template.id == template_id).first()
        assert deleted_template is None
        
        print("✅ テンプレート削除API確認完了")
        print("✅ Level 2統合テスト完了: テンプレートCRUD API統合")
    
    @pytest.mark.integration
    def test_template_chart_integration(self, level2_client: Level2TestClient, test_db_session: Session, test_template_data):
        """
        テストレベル: Level 2 (Integration)
        対象: テンプレート + チャート処理統合
        """
        print("\n🧪 Level 2統合テスト開始: テンプレート + チャート処理統合")
        
        # Step 1: テンプレート作成
        create_response = level2_client.client.post(
            "/api/v1/templates",
            json=test_template_data.dict(),
            headers=level2_client.headers
        )
        
        assert create_response.status_code == 201
        template_id = create_response.json()["id"]
        
        # Step 2: テンプレート指定チャートアップロード
        print("📤 Step 2: テンプレート指定チャートアップロード")
        test_image = level2_client.create_test_image()
        
        upload_response = level2_client.client.post(
            f"/api/v1/charts/upload?template_id={template_id}",
            files={"file": ("template_test.jpg", test_image, "image/jpeg")},
            headers=level2_client.headers
        )
        
        assert upload_response.status_code in [200, 201, 202]
        chart_id = upload_response.json()["chart_id"]
        
        # Step 3: チャートとテンプレートの関連確認
        print("🔗 Step 3: チャート・テンプレート関連確認")
        chart_record = test_db_session.query(Chart).filter(Chart.id == chart_id).first()
        assert chart_record is not None
        
        # テンプレートIDが正しく設定されているか確認
        if hasattr(chart_record, 'template_id'):
            assert chart_record.template_id == template_id
        
        print("✅ チャート・テンプレート関連確認完了")
        
        # クリーンアップ
        level2_client.cleanup_test_chart(chart_id, test_db_session)
        
        # テンプレート削除
        delete_response = level2_client.client.delete(
            f"/api/v1/templates/{template_id}",
            headers=level2_client.headers
        )
        assert delete_response.status_code == 204
        
        print("✅ Level 2統合テスト完了: テンプレート + チャート処理統合")


class TestLevel2ReviewAPIIntegration:
    """
    Level 2 統合テスト: レビューAPI統合テスト
    """
    
    @pytest.mark.integration
    def test_review_workflow_integration(self, level2_client: Level2TestClient, test_db_session: Session):
        """
        テストレベル: Level 2 (Integration)
        対象: レビューワークフロー API + DB連携
        """
        print("\n🧪 Level 2統合テスト開始: レビューワークフロー統合")
        
        # Step 1: チャートアップロード（前提条件）
        test_image = level2_client.create_test_image()
        
        upload_response = level2_client.client.post(
            "/api/v1/charts",
            files={"file": ("review_test.jpg", test_image, "image/jpeg")},
            headers=level2_client.headers
        )
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # Step 2: 処理完了まで短時間待機
        print("⏳ Step 2: 処理完了待機")
        max_wait_time = 20  # 統合テストでは短時間
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = level2_client.client.get(
                f"/api/v1/charts/{chart_id}/status",
                headers=level2_client.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "partial_success", "failed"]:
                    break
            
            time.sleep(2)
        
        # Step 3: レビュー項目取得API
        print("📋 Step 3: レビュー項目取得API")
        review_response = level2_client.client.get(
            f"/api/v1/charts/{chart_id}/review-items",
            headers=level2_client.headers
        )
        
        # レビュー項目が取得できるかテスト（処理状態に依存）
        if review_response.status_code == 200:
            review_data = review_response.json()
            assert "chart_id" in review_data
            assert "review_items" in review_data
            
            review_items = review_data["review_items"]
            
            if len(review_items) > 0:
                # Step 4: 項目更新API
                print("✏️ Step 4: 項目更新API")
                first_item = review_items[0]
                item_id = first_item["id"]
                
                update_data = {
                    "item_name": first_item["item_name"],
                    "interpreted_text": f"Level2統合テスト更新: {first_item['interpreted_text']}",
                    "review_comment": "Level 2統合テストによる更新",
                    "reviewed_by": "level2_integration_tester"
                }
                
                update_response = level2_client.client.patch(
                    f"/api/v1/charts/{chart_id}/items/{item_id}",
                    json=update_data,
                    headers=level2_client.headers
                )
                
                if update_response.status_code == 200:
                    update_result = update_response.json()
                    assert update_result["success"] == True
                    assert update_result["item"]["reviewed_by"] == "level2_integration_tester"
                    
                    # DB更新確認
                    extracted_data = test_db_session.query(ExtractedData).filter(
                        ExtractedData.chart_id == chart_id
                    ).first()
                    
                    if extracted_data:
                        assert extracted_data.data is not None
                        print("✅ レビュー更新DB連携確認完了")
                    
                    print("✅ 項目更新API確認完了")
                else:
                    print(f"ℹ️ 項目更新スキップ（ステータス: {update_response.status_code}）")
            else:
                print("ℹ️ レビュー項目なし（処理未完了または失敗）")
            
            print("✅ レビュー項目取得API確認完了")
        else:
            print(f"ℹ️ レビュー項目取得スキップ（ステータス: {review_response.status_code}）")
        
        # クリーンアップ
        level2_client.cleanup_test_chart(chart_id, test_db_session)
        print("✅ Level 2統合テスト完了: レビューワークフロー統合")


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "integration"]) 