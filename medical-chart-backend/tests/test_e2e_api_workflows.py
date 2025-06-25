"""
Level 3 E2Eテスト: API経由の完全ワークフロー
テストレベル: Level 3 (End-to-End)
信頼性: 全体ワークフロー 90%
実行頻度: リリース前
前提条件: ステージング環境またはテスト環境
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15

使用方法:
pytest tests/test_e2e_api_workflows.py -v
"""

import asyncio
import io
import json
import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.schemas.chart import ChartCreateResponse, ChartStatusResponse, ChartResultResponse
from app.schemas.template import TemplateCreate, TemplateItemCreate


class E2ETestClient:
    """E2Eテスト用のHTTPクライアント"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.client = TestClient(app)
        self.base_url = base_url or "http://localhost:8000"
        self.api_key = api_key or "test-api-key"
        self.headers = {"X-API-KEY": self.api_key}
    
    def create_test_image(self, width: int = 800, height: int = 600) -> io.BytesIO:
        """テスト用画像を生成"""
        image = Image.new('RGB', (width, height), color='white')
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='JPEG')
        image_buffer.seek(0)
        return image_buffer


@pytest.fixture
def e2e_client():
    """E2Eテスト用クライアントのフィクスチャ"""
    return E2ETestClient()


@pytest.fixture
def test_template_data():
    """テスト用テンプレートデータ"""
    return TemplateCreate(
        name="E2Eテスト用テンプレート",
        description="E2Eテストで使用するテンプレート",
        type="user",
        created_by="e2e_test_user",
        is_active=True,
        items=[
            TemplateItemCreate(
                name="主訴",
                enabled=True,
                display_order=1,
                description="患者の主な訴え",
                confidence_threshold=0.8
            ),
            TemplateItemCreate(
                name="現病歴",
                enabled=True,
                display_order=2,
                description="現在の病気の経過",
                confidence_threshold=0.7
            ),
            TemplateItemCreate(
                name="既往歴",
                enabled=True,
                display_order=3,
                description="過去の病気の履歴",
                confidence_threshold=0.6
            )
        ]
    )


class TestLevel3ChartWorkflow:
    """
    Level 3 E2Eテスト: チャート処理の完全ワークフロー
    """
    
    @pytest.mark.e2e
    def test_complete_chart_upload_workflow(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: チャートアップロード〜結果取得の完全ワークフロー
        信頼性: 全体ワークフロー 90%
        """
        print("\n🧪 Level 3 E2Eテスト開始: チャート完全ワークフロー")
        
        # Step 1: チャートアップロード
        print("📤 Step 1: チャートアップロード")
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        assert upload_response.status_code == 202
        upload_data = upload_response.json()
        chart_id = upload_data["chart_id"]
        
        print(f"✅ アップロード成功: chart_id={chart_id}")
        assert "chart_id" in upload_data
        assert upload_data["status"] in ["processing", "pending"]
        
        # Step 2: ステータス確認（処理完了まで待機）
        print("⏳ Step 2: 処理完了まで待機")
        max_wait_time = 120  # 最大2分待機
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait_time:
            status_response = e2e_client.client.get(
                f"/api/v1/charts/{chart_id}/status",
                headers=e2e_client.headers
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            current_status = status_data["status"]
            
            print(f"📊 現在のステータス: {current_status}")
            
            if current_status in ["completed", "failed", "partial_success"]:
                final_status = current_status
                break
            
            time.sleep(2)  # 2秒待機
        
        # 処理完了の確認
        assert final_status is not None, "処理がタイムアウトしました"
        assert final_status in ["completed", "partial_success"], f"処理が失敗しました: {final_status}"
        
        print(f"✅ 処理完了: {final_status}")
        
        # Step 3: 結果取得
        print("📥 Step 3: 結果取得")
        result_response = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}",
            headers=e2e_client.headers
        )
        
        assert result_response.status_code == 200
        result_data = result_response.json()
        
        print(f"📊 結果データ構造: {list(result_data.keys())}")
        
        # 結果データの検証
        assert "chart_id" in result_data
        assert "status" in result_data
        assert "extracted_items" in result_data
        assert result_data["status"] == final_status
        
        # 抽出項目の検証
        extracted_items = result_data["extracted_items"]
        assert isinstance(extracted_items, list)
        assert len(extracted_items) > 0
        
        # 各項目の構造検証
        for item in extracted_items:
            assert "item_name" in item
            assert "interpreted_text" in item
            assert "confidence_score" in item
            assert "similarity_score" in item
            
        print(f"✅ 抽出項目数: {len(extracted_items)}")
        print("✅ Level 3 E2Eテスト完了: チャート完全ワークフロー")
        
        return chart_id, result_data
    
    @pytest.mark.e2e
    def test_chart_upload_with_template_workflow(self, e2e_client: E2ETestClient, test_template_data):
        """
        テストレベル: Level 3 (E2E)
        対象: テンプレート指定チャートアップロードワークフロー
        """
        print("\n🧪 Level 3 E2Eテスト開始: テンプレート指定ワークフロー")
        
        # Step 1: テンプレート作成
        print("📝 Step 1: テンプレート作成")
        template_response = e2e_client.client.post(
            "/api/v1/templates",
            json=test_template_data.dict(),
            headers=e2e_client.headers
        )
        
        assert template_response.status_code == 201
        template_data = template_response.json()
        template_id = template_data["id"]
        
        print(f"✅ テンプレート作成成功: template_id={template_id}")
        
        # Step 2: テンプレート指定でチャートアップロード
        print("📤 Step 2: テンプレート指定チャートアップロード")
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            f"/api/v1/charts/upload?template_id={template_id}",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        assert upload_response.status_code in [200, 201, 202]
        upload_data = upload_response.json()
        chart_id = upload_data["chart_id"]
        
        print(f"✅ テンプレート指定アップロード成功: chart_id={chart_id}")
        
        # Step 3: 処理完了まで待機
        print("⏳ Step 3: 処理完了まで待機")
        max_wait_time = 120
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait_time:
            status_response = e2e_client.client.get(
                f"/api/v1/charts/{chart_id}/status",
                headers=e2e_client.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_status = status_data["status"]
                
                if current_status in ["completed", "failed", "partial_success"]:
                    final_status = current_status
                    break
            
            time.sleep(2)
        
        assert final_status in ["completed", "partial_success"], f"処理が失敗: {final_status}"
        
        # Step 4: 結果確認（テンプレート項目との整合性）
        print("📥 Step 4: テンプレート整合性確認")
        result_response = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}",
            headers=e2e_client.headers
        )
        
        assert result_response.status_code == 200
        result_data = result_response.json()
        
        # テンプレート項目との整合性確認
        extracted_items = result_data["extracted_items"]
        template_item_names = [item.name for item in test_template_data.items]
        extracted_item_names = [item["item_name"] for item in extracted_items]
        
        # テンプレートで指定した項目が含まれているか確認
        for template_item_name in template_item_names:
            assert template_item_name in extracted_item_names, f"テンプレート項目 '{template_item_name}' が結果に含まれていません"
        
        print(f"✅ テンプレート項目整合性確認完了")
        print("✅ Level 3 E2Eテスト完了: テンプレート指定ワークフロー")
        
        # Step 5: クリーンアップ（テンプレート削除）
        delete_response = e2e_client.client.delete(
            f"/api/v1/templates/{template_id}",
            headers=e2e_client.headers
        )
        assert delete_response.status_code == 204
        
        return chart_id, template_id, result_data


class TestLevel3ReviewWorkflow:
    """
    Level 3 E2Eテスト: レビューワークフロー
    """
    
    @pytest.mark.e2e
    def test_complete_review_workflow(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: レビュー機能の完全ワークフロー
        """
        print("\n🧪 Level 3 E2Eテスト開始: レビュー完全ワークフロー")
        
        # Step 1: チャートアップロード（前提条件）
        print("📤 Step 1: チャートアップロード")
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # Step 2: 処理完了まで待機
        print("⏳ Step 2: 処理完了まで待機")
        max_wait_time = 120
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = e2e_client.client.get(
                f"/api/v1/charts/{chart_id}/status",
                headers=e2e_client.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "partial_success"]:
                    break
            
            time.sleep(2)
        
        # Step 3: レビュー項目取得
        print("📋 Step 3: レビュー項目取得")
        review_response = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}/review-items",
            headers=e2e_client.headers
        )
        
        assert review_response.status_code == 200
        review_data = review_response.json()
        
        assert "chart_id" in review_data
        assert "review_items" in review_data
        review_items = review_data["review_items"]
        assert len(review_items) > 0
        
        print(f"📊 レビュー項目数: {len(review_items)}")
        
        # Step 4: 項目更新（レビュー実行）
        print("✏️ Step 4: 項目レビュー実行")
        first_item = review_items[0]
        item_id = first_item["id"]
        
        update_data = {
            "item_name": first_item["item_name"],
            "interpreted_text": f"レビュー済み: {first_item['interpreted_text']}",
            "review_comment": "E2Eテストによるレビュー",
            "reviewed_by": "e2e_test_reviewer"
        }
        
        update_response = e2e_client.client.patch(
            f"/api/v1/charts/{chart_id}/items/{item_id}",
            json=update_data,
            headers=e2e_client.headers
        )
        
        assert update_response.status_code == 200
        update_result = update_response.json()
        
        # 更新結果の検証
        assert update_result["success"] == True
        assert update_result["item"]["reviewed_by"] == "e2e_test_reviewer"
        assert update_result["item"]["needs_review"] == False
        
        print("✅ 項目レビュー完了")
        
        # Step 5: 更新後のレビュー項目再取得（確認）
        print("🔍 Step 5: レビュー結果確認")
        review_response_after = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}/review-items",
            headers=e2e_client.headers
        )
        
        assert review_response_after.status_code == 200
        review_data_after = review_response_after.json()
        
        # 更新された項目を確認
        updated_item = next(
            (item for item in review_data_after["review_items"] if item["id"] == item_id),
            None
        )
        
        assert updated_item is not None
        assert updated_item["reviewed_by"] == "e2e_test_reviewer"
        assert updated_item["needs_review"] == False
        assert "レビュー済み:" in updated_item["interpreted_text"]
        
        print("✅ Level 3 E2Eテスト完了: レビュー完全ワークフロー")
        
        return chart_id, item_id, update_result


class TestLevel3ErrorHandling:
    """
    Level 3 E2Eテスト: エラーハンドリング
    """
    
    @pytest.mark.e2e
    def test_invalid_file_upload_error_handling(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: 不正ファイルアップロード時のエラーハンドリング
        """
        print("\n🧪 Level 3 E2Eテスト開始: 不正ファイルエラーハンドリング")
        
        # 不正なファイル形式（テキストファイル）
        invalid_file = io.StringIO("This is not an image file")
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test.txt", invalid_file, "text/plain")},
            headers=e2e_client.headers
        )
        
        # エラーレスポンスの検証
        assert upload_response.status_code == 400
        error_data = upload_response.json()
        assert "detail" in error_data
        assert "File type not allowed" in error_data["detail"]
        
        print("✅ 不正ファイル形式エラーハンドリング確認")
        
        # ファイルサイズ超過テスト（大きなファイル）
        large_image = e2e_client.create_test_image(width=5000, height=5000)
        
        upload_response_large = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("large_test.jpg", large_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        # ファイルサイズによってはエラーになる可能性
        if upload_response_large.status_code == 400:
            error_data = upload_response_large.json()
            assert "File size exceeds limit" in error_data["detail"]
            print("✅ ファイルサイズ超過エラーハンドリング確認")
        else:
            print("ℹ️ ファイルサイズは制限内でした")
        
        print("✅ Level 3 E2Eテスト完了: エラーハンドリング")
    
    @pytest.mark.e2e
    def test_authentication_error_handling(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: 認証エラーハンドリング
        """
        print("\n🧪 Level 3 E2Eテスト開始: 認証エラーハンドリング")
        
        # 無効なAPIキー
        invalid_headers = {"X-API-KEY": "invalid-api-key"}
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=invalid_headers
        )
        
        # 認証エラーの検証
        assert upload_response.status_code in [401, 403]
        
        print("✅ 無効APIキーエラーハンドリング確認")
        
        # APIキーなし
        upload_response_no_key = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")}
        )
        
        assert upload_response_no_key.status_code in [401, 403]
        
        print("✅ APIキーなしエラーハンドリング確認")
        print("✅ Level 3 E2Eテスト完了: 認証エラーハンドリング")


class TestLevel3PerformanceAndSecurity:
    """
    Level 3 E2Eテスト: パフォーマンスとセキュリティ
    """
    
    @pytest.mark.e2e
    def test_api_response_time_performance(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: APIレスポンス時間のパフォーマンス検証
        """
        print("\n🧪 Level 3 E2Eテスト開始: パフォーマンス検証")
        
        # アップロードレスポンス時間測定
        test_image = e2e_client.create_test_image()
        
        start_time = time.time()
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        upload_time = time.time() - start_time
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # アップロードレスポンス時間の検証（5秒以内）
        assert upload_time < 5.0, f"アップロードレスポンス時間が遅すぎます: {upload_time:.2f}秒"
        print(f"✅ アップロードレスポンス時間: {upload_time:.2f}秒")
        
        # ステータス確認レスポンス時間測定
        start_time = time.time()
        status_response = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}/status",
            headers=e2e_client.headers
        )
        status_time = time.time() - start_time
        
        assert status_response.status_code == 200
        assert status_time < 2.0, f"ステータス確認レスポンス時間が遅すぎます: {status_time:.2f}秒"
        print(f"✅ ステータス確認レスポンス時間: {status_time:.2f}秒")
        
        print("✅ Level 3 E2Eテスト完了: パフォーマンス検証")
    
    @pytest.mark.e2e
    def test_concurrent_requests_handling(self, e2e_client: E2ETestClient):
        """
        テストレベル: Level 3 (E2E)
        対象: 同時リクエスト処理能力
        """
        print("\n🧪 Level 3 E2Eテスト開始: 同時リクエスト処理")
        
        import concurrent.futures
        import threading
        
        def upload_chart(client_instance, request_id):
            """単一のチャートアップロード"""
            test_image = client_instance.create_test_image()
            
            response = client_instance.client.post(
                "/api/v1/charts",
                files={"file": (f"test_chart_{request_id}.jpg", test_image, "image/jpeg")},
                headers=client_instance.headers
            )
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time": time.time(),
                "chart_id": response.json().get("chart_id") if response.status_code == 202 else None
            }
        
        # 5つの同時リクエストを実行
        concurrent_requests = 5
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(upload_chart, e2e_client, i)
                for i in range(concurrent_requests)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # 結果検証
        successful_requests = [r for r in results if r["status_code"] == 202]
        assert len(successful_requests) >= concurrent_requests * 0.8, "同時リクエストの成功率が低すぎます"
        
        print(f"✅ 同時リクエスト処理: {len(successful_requests)}/{concurrent_requests} 成功")
        print(f"✅ 総処理時間: {total_time:.2f}秒")
        print("✅ Level 3 E2Eテスト完了: 同時リクエスト処理")
        
        return results


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v", "-s", "--tb=short"]) 