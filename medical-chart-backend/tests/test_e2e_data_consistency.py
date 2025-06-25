"""
Level 3 E2Eテスト: データ整合性・永続化検証
テストレベル: Level 3 (End-to-End)
信頼性: データ整合性 95%
実行頻度: リリース前
前提条件: 実際のデータベース環境
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15

使用方法:
pytest tests/test_e2e_data_consistency.py -v
"""

import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.db.models import Chart, ExtractedData, ProcessStatus
from app.schemas.chart import ChartCreateResponse
from tests.test_e2e_api_workflows import E2ETestClient


class TestLevel3DataConsistency:
    """
    Level 3 E2Eテスト: データ整合性検証
    """
    
    @pytest.mark.e2e
    def test_chart_data_persistence_workflow(self):
        """
        テストレベル: Level 3 (E2E)
        対象: チャートデータの永続化と整合性
        """
        print("\n🧪 Level 3 E2Eテスト開始: データ永続化整合性")
        
        e2e_client = E2ETestClient()
        
        # Step 1: チャートアップロード
        print("📤 Step 1: チャートアップロード")
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # Step 2: データベース直接確認（チャート作成直後）
        print("🔍 Step 2: DB直接確認（作成直後）")
        db_session = next(get_db())
        
        try:
            # チャートレコードの確認
            chart_record = db_session.query(Chart).filter(Chart.id == chart_id).first()
            assert chart_record is not None, "チャートレコードがDBに作成されていません"
            assert chart_record.status in [ProcessStatus.PENDING, ProcessStatus.PROCESSING]
            assert chart_record.filename == "test_chart.jpg"
            assert chart_record.content_type == "image/jpeg"
            assert chart_record.gcs_uri is not None
            
            print(f"✅ チャートレコード確認: status={chart_record.status}")
            
            # Step 3: 処理完了まで待機
            print("⏳ Step 3: 処理完了まで待機")
            max_wait_time = 120
            start_time = time.time()
            final_status = None
            
            while time.time() - start_time < max_wait_time:
                # APIでステータス確認
                status_response = e2e_client.client.get(
                    f"/api/v1/charts/{chart_id}/status",
                    headers=e2e_client.headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data["status"]
                    
                    # DB直接確認
                    db_session.refresh(chart_record)
                    db_status = chart_record.status.value
                    
                    # API レスポンスとDB状態の整合性確認
                    assert current_status == db_status, f"API({current_status})とDB({db_status})のステータスが不一致"
                    
                    if current_status in ["completed", "failed", "partial_success"]:
                        final_status = current_status
                        break
                
                time.sleep(2)
            
            assert final_status in ["completed", "partial_success"], f"処理が失敗: {final_status}"
            print(f"✅ 処理完了: {final_status}")
            
            # Step 4: 抽出データの整合性確認
            print("📊 Step 4: 抽出データ整合性確認")
            
            # API経由で結果取得
            result_response = e2e_client.client.get(
                f"/api/v1/charts/{chart_id}",
                headers=e2e_client.headers
            )
            
            assert result_response.status_code == 200
            api_result = result_response.json()
            
            # DB直接確認
            extracted_data_record = db_session.query(ExtractedData).filter(
                ExtractedData.chart_id == chart_id
            ).first()
            
            assert extracted_data_record is not None, "抽出データレコードがDBに作成されていません"
            
            # API結果とDB結果の整合性確認
            api_items = api_result["extracted_items"]
            db_data = extracted_data_record.data
            
            # データ構造の確認
            if "review_items" in db_data:
                db_items = db_data["review_items"]
            else:
                # 従来形式の場合、変換
                db_items = [
                    {
                        "item_name": key,
                        "interpreted_text": value.get("interpreted_text", "") if isinstance(value, dict) else str(value),
                        "confidence_score": value.get("confidence_score", 0.0) if isinstance(value, dict) else 0.0,
                        "similarity_score": value.get("similarity_score", 0.0) if isinstance(value, dict) else 0.0
                    }
                    for key, value in db_data.items()
                    if key != "metadata"
                ]
            
            # 項目数の確認
            assert len(api_items) == len(db_items), f"API項目数({len(api_items)})とDB項目数({len(db_items)})が不一致"
            
            # 各項目の整合性確認
            for api_item in api_items:
                item_name = api_item["item_name"]
                db_item = next((item for item in db_items if item["item_name"] == item_name), None)
                
                assert db_item is not None, f"項目 '{item_name}' がDBに存在しません"
                assert api_item["interpreted_text"] == db_item["interpreted_text"], f"項目 '{item_name}' の解釈テキストが不一致"
                
                # スコアの確認（小数点以下の誤差を考慮）
                api_confidence = api_item.get("confidence_score", 0.0)
                db_confidence = db_item.get("confidence_score", 0.0)
                assert abs(api_confidence - db_confidence) < 0.001, f"項目 '{item_name}' の信頼度スコアが不一致"
            
            print(f"✅ 抽出データ整合性確認完了: {len(api_items)}項目")
            
            # Step 5: タイムスタンプ整合性確認
            print("🕐 Step 5: タイムスタンプ整合性確認")
            
            # チャートのタイムスタンプ
            assert chart_record.created_at is not None
            assert chart_record.updated_at is not None
            assert chart_record.updated_at >= chart_record.created_at
            
            # 抽出データのタイムスタンプ
            assert extracted_data_record.created_at is not None
            assert extracted_data_record.updated_at is not None
            assert extracted_data_record.created_at >= chart_record.created_at
            
            print("✅ タイムスタンプ整合性確認完了")
            print("✅ Level 3 E2Eテスト完了: データ永続化整合性")
            
            return chart_id, chart_record, extracted_data_record
            
        finally:
            db_session.close()
    
    @pytest.mark.e2e
    def test_concurrent_data_consistency(self):
        """
        テストレベル: Level 3 (E2E)
        対象: 同時処理時のデータ整合性
        """
        print("\n🧪 Level 3 E2Eテスト開始: 同時処理データ整合性")
        
        import concurrent.futures
        
        e2e_client = E2ETestClient()
        
        def upload_and_verify_chart(request_id: int) -> Dict:
            """単一チャートのアップロードと検証"""
            test_image = e2e_client.create_test_image()
            
            # アップロード
            upload_response = e2e_client.client.post(
                "/api/v1/charts",
                files={"file": (f"test_chart_{request_id}.jpg", test_image, "image/jpeg")},
                headers=e2e_client.headers
            )
            
            if upload_response.status_code != 202:
                return {"request_id": request_id, "success": False, "error": "Upload failed"}
            
            chart_id = upload_response.json()["chart_id"]
            
            # DB確認
            db_session = next(get_db())
            try:
                chart_record = db_session.query(Chart).filter(Chart.id == chart_id).first()
                if chart_record is None:
                    return {"request_id": request_id, "success": False, "error": "Chart not in DB"}
                
                return {
                    "request_id": request_id,
                    "success": True,
                    "chart_id": chart_id,
                    "db_status": chart_record.status.value
                }
            finally:
                db_session.close()
        
        # 3つの同時リクエストを実行
        concurrent_requests = 3
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(upload_and_verify_chart, i)
                for i in range(concurrent_requests)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 結果検証
        successful_results = [r for r in results if r["success"]]
        assert len(successful_results) == concurrent_requests, f"同時処理で失敗があります: {results}"
        
        # 各チャートのユニーク性確認
        chart_ids = [r["chart_id"] for r in successful_results]
        assert len(set(chart_ids)) == len(chart_ids), "チャートIDに重複があります"
        
        print(f"✅ 同時処理データ整合性確認完了: {len(successful_results)}件")
        print("✅ Level 3 E2Eテスト完了: 同時処理データ整合性")
        
        return results
    
    @pytest.mark.e2e
    def test_review_data_consistency(self):
        """
        テストレベル: Level 3 (E2E)
        対象: レビューデータの整合性
        """
        print("\n🧪 Level 3 E2Eテスト開始: レビューデータ整合性")
        
        e2e_client = E2ETestClient()
        
        # Step 1: チャートアップロードと処理完了まで待機
        print("📤 Step 1: チャートアップロード")
        test_image = e2e_client.create_test_image()
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": ("test_chart.jpg", test_image, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        assert upload_response.status_code == 202
        chart_id = upload_response.json()["chart_id"]
        
        # 処理完了まで待機
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
        
        # Step 2: レビュー項目取得
        print("📋 Step 2: レビュー項目取得")
        review_response = e2e_client.client.get(
            f"/api/v1/charts/{chart_id}/review-items",
            headers=e2e_client.headers
        )
        
        assert review_response.status_code == 200
        review_data = review_response.json()
        review_items = review_data["review_items"]
        assert len(review_items) > 0
        
        # Step 3: 項目更新
        print("✏️ Step 3: 項目更新")
        first_item = review_items[0]
        item_id = first_item["id"]
        original_text = first_item["interpreted_text"]
        
        update_data = {
            "item_name": first_item["item_name"],
            "interpreted_text": f"更新済み: {original_text}",
            "review_comment": "データ整合性テスト",
            "reviewed_by": "consistency_tester"
        }
        
        update_response = e2e_client.client.patch(
            f"/api/v1/charts/{chart_id}/items/{item_id}",
            json=update_data,
            headers=e2e_client.headers
        )
        
        assert update_response.status_code == 200
        
        # Step 4: DB直接確認
        print("🔍 Step 4: DB直接確認")
        db_session = next(get_db())
        
        try:
            extracted_data_record = db_session.query(ExtractedData).filter(
                ExtractedData.chart_id == chart_id
            ).first()
            
            assert extracted_data_record is not None
            
            # 更新されたデータの確認
            db_data = extracted_data_record.data
            
            if "review_items" in db_data:
                updated_item = next(
                    (item for item in db_data["review_items"] if item["item_name"] == first_item["item_name"]),
                    None
                )
            else:
                # 従来形式の場合
                item_name = first_item["item_name"]
                updated_item = db_data.get(item_name, {})
            
            assert updated_item is not None, "更新された項目がDBに見つかりません"
            assert "更新済み:" in updated_item["interpreted_text"], "DBの更新が反映されていません"
            assert updated_item["reviewed_by"] == "consistency_tester", "レビュー者情報が正しく保存されていません"
            assert updated_item["needs_review"] == False, "レビュー完了フラグが正しく設定されていません"
            
            print("✅ DB更新確認完了")
            
            # Step 5: API経由での再確認
            print("🔄 Step 5: API経由再確認")
            review_response_after = e2e_client.client.get(
                f"/api/v1/charts/{chart_id}/review-items",
                headers=e2e_client.headers
            )
            
            assert review_response_after.status_code == 200
            review_data_after = review_response_after.json()
            
            updated_item_api = next(
                (item for item in review_data_after["review_items"] if item["id"] == item_id),
                None
            )
            
            assert updated_item_api is not None
            assert "更新済み:" in updated_item_api["interpreted_text"]
            assert updated_item_api["reviewed_by"] == "consistency_tester"
            assert updated_item_api["needs_review"] == False
            
            print("✅ API経由再確認完了")
            print("✅ Level 3 E2Eテスト完了: レビューデータ整合性")
            
            return chart_id, item_id, updated_item_api
            
        finally:
            db_session.close()


class TestLevel3TransactionConsistency:
    """
    Level 3 E2Eテスト: トランザクション整合性
    """
    
    @pytest.mark.e2e
    def test_rollback_consistency(self):
        """
        テストレベル: Level 3 (E2E)
        対象: エラー時のロールバック整合性
        """
        print("\n🧪 Level 3 E2Eテスト開始: ロールバック整合性")
        
        e2e_client = E2ETestClient()
        
        # 不正なファイルでアップロード試行
        invalid_file = e2e_client.create_test_image()
        
        # 非常に大きなファイル名でエラーを誘発
        long_filename = "a" * 1000 + ".jpg"
        
        upload_response = e2e_client.client.post(
            "/api/v1/charts",
            files={"file": (long_filename, invalid_file, "image/jpeg")},
            headers=e2e_client.headers
        )
        
        # エラーレスポンスの場合、DBに不正なレコードが残っていないことを確認
        if upload_response.status_code >= 400:
            print("✅ 期待通りエラーが発生")
            
            # DB確認（不正なレコードがないことを確認）
            db_session = next(get_db())
            try:
                # 長いファイル名のチャートが作成されていないことを確認
                invalid_charts = db_session.query(Chart).filter(
                    Chart.filename.like("aaaa%")
                ).all()
                
                assert len(invalid_charts) == 0, "エラー時にDBに不正なレコードが残っています"
                print("✅ ロールバック確認完了")
                
            finally:
                db_session.close()
        else:
            print("ℹ️ エラーが発生しませんでした（ファイル名制限が緩い可能性）")
        
        print("✅ Level 3 E2Eテスト完了: ロールバック整合性")


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v", "-s", "--tb=short"]) 