import asyncio
from uuid import UUID
import logging
from typing import Dict, Any, List, Optional
import json
import traceback

from sqlalchemy.orm import Session

from app.db.models import ProcessStatus
from app.services import db_service, gcs_service, gemini_service, similarity_service
from app.core.config import settings

# ロガー設定
logger = logging.getLogger("app.tasks.process_chart")
logger.setLevel(logging.DEBUG)

async def run_extraction_task(chart_id: UUID, gcs_uri: str, db_session: Session) -> None:
    """
    カルテ画像処理とデータ抽出のバックグラウンドタスク
    
    Args:
        chart_id: カルテID
        gcs_uri: GCSのURI
        db_session: データベースセッション
    """
    try:
        # ステータスを 'processing' に更新
        db_service.update_chart_status(db_session, chart_id, ProcessStatus.PROCESSING)
        
        # GCSから画像をダウンロード
        image_data = await gcs_service.download_file_from_gcs(gcs_uri)
        if not image_data:
            error_message = f"Failed to download image from {gcs_uri}"
            db_service.update_chart_status(
                db_session, chart_id, ProcessStatus.FAILED, error_message
            )
            return
        
        # 第一段階: 生テキスト抽出
        try:
            logger.info(f"Starting raw text extraction with Gemini {settings.GEMINI_MODEL_ID}")
            raw_items = await gemini_service.extract_raw_data_from_image(image_data)
            if not raw_items:
                error_message = "Failed to extract raw data from image"
                db_service.update_chart_status(
                    db_session, chart_id, ProcessStatus.FAILED, error_message
                )
                return
                
            logger.info(f"Successfully extracted {len(raw_items)} raw items")
            logger.debug(f"Raw items: {json.dumps(raw_items, ensure_ascii=False)}")
            
            # 抽出データが空（項目がない）場合のチェックを追加
            if len(raw_items) == 0:
                logger.warning("No extraction items found. Using default items.")
                # デフォルトの項目セットを使用
                raw_items = [
                    {"item_name": "主訴", "raw_text": ""},
                    {"item_name": "現病歴", "raw_text": ""},
                    {"item_name": "既往歴", "raw_text": ""},
                    {"item_name": "家族歴", "raw_text": ""},
                    {"item_name": "生活歴", "raw_text": ""},
                    {"item_name": "内服薬", "raw_text": ""},
                    {"item_name": "身体所見", "raw_text": ""}
                ]
        except Exception as e:
            error_message = f"Error during raw text extraction: {str(e)}"
            logger.error(f"{error_message}\n{traceback.format_exc()}")
            db_service.update_chart_status(
                db_session, chart_id, ProcessStatus.FAILED, error_message
            )
            return
        
        # 第二段階: テキスト解釈・正規化
        interpreted_items = []
        interpretation_error = None
        
        try:
            logger.info(f"Starting text interpretation with Gemini {settings.GEMINI_MODEL_ID}")
            interpreted_items = await gemini_service.interpret_extracted_data(raw_items)
            logger.info(f"Successfully interpreted {len(interpreted_items)} items")
            logger.debug(f"Interpreted items: {json.dumps(interpreted_items, ensure_ascii=False)}")
        except Exception as e:
            interpretation_error = str(e)
            logger.error(f"Error during text interpretation: {interpretation_error}\n{traceback.format_exc()}")
            # 解釈に失敗しても、生テキストだけでも保存するため処理は続行
        
        # JSONB用のデータ構造を作成
        jsonb_data, needs_review, overall_confidence = process_extracted_items(
            raw_items, interpreted_items
        )
        
        # 処理結果の状態を判定
        status = ProcessStatus.COMPLETED
        error_message = None
        
        # 解釈フェーズに失敗した場合
        if interpretation_error:
            status = ProcessStatus.PARTIAL_SUCCESS
            error_message = f"Text interpretation failed: {interpretation_error}"
            needs_review = True  # 必ずレビューが必要とマーク
        
        # 部分的な成功（一部の項目が失敗）の場合
        elif any(
            item_data.get("error_occurred", False) 
            for item_data in jsonb_data.values() 
            if isinstance(item_data, dict) and "error_occurred" in item_data
        ):
            status = ProcessStatus.PARTIAL_SUCCESS
            error_message = "Some items failed to process correctly"
        
        # 抽出されたデータをDBに保存
        db_service.create_extracted_data_jsonb(
            db_session, chart_id, jsonb_data, overall_confidence, needs_review
        )
        
        # ステータスを更新
        db_service.update_chart_status(db_session, chart_id, status, error_message)
        
    except Exception as e:
        # エラーハンドリング
        error_message = f"Error processing chart: {str(e)}"
        logger.error(f"{error_message}\n{traceback.format_exc()}")
        db_service.update_chart_status(
            db_session, chart_id, ProcessStatus.FAILED, error_message
        )


def process_extracted_items(
    raw_items: List[Dict[str, str]], 
    interpreted_items: List[Dict[str, str]]
) -> tuple[Dict[str, Any], bool, float]:
    """
    抽出された生テキストと解釈後テキストを処理し、JSONB保存用のデータ構造を作成
    
    Args:
        raw_items: 抽出された生テキストのリスト
        interpreted_items: 解釈後テキストのリスト
        
    Returns:
        tuple[Dict[str, Any], bool, float]: 
            - JSONB保存用のデータ辞書
            - レビュー要否フラグ
            - 全体の信頼度スコア
    """
    # raw_itemsをitem_nameをキーとする辞書に変換
    raw_dict = {item["item_name"]: item.get("raw_text") for item in raw_items}
    
    # interpreted_itemsをitem_nameをキーとする辞書に変換
    interpreted_dict = {item["item_name"]: item.get("interpreted_text") for item in interpreted_items}
    
    # 両方のキーのユニオンを取得
    all_keys = set(raw_dict.keys()) | set(interpreted_dict.keys())
    
    # データが空の場合の処理を追加
    if len(all_keys) == 0:
        logger.warning("No extraction keys found. Using default keys.")
        all_keys = {"主訴", "現病歴", "既往歴", "家族歴", "生活歴", "内服薬", "身体所見"}
        
    # データの統合と類似度計算を含むJSONB用のデータ構造
    jsonb_data = {}
    needs_review = False
    review_items = []
    
    for key in all_keys:
        # 生テキストと解釈後テキストを取得
        raw_text = raw_dict.get(key)
        interpreted_text = interpreted_dict.get(key)
        
        # エラー状態を検出
        error_occurred = raw_text is None or interpreted_text is None
        
        # 解釈後テキストがない場合は、生テキストを使用
        if interpreted_text is None and raw_text is not None:
            interpreted_text = raw_text
            error_occurred = True  # 解釈エラーとしてマーク
        
        # 類似度を計算
        similarity_score = similarity_service.calculate_levenshtein_similarity(
            raw_text, interpreted_text
        ) if not error_occurred else 0.0
        
        # 意味的類似度を計算
        confidence_score = similarity_service.calculate_semantic_similarity(
            raw_text, interpreted_text
        ) if not error_occurred else 0.0
        
        # 要確認フラグを判定 - 両方のスコアを「または」条件で評価
        item_needs_review = similarity_service.should_review(
            similarity_score, confidence_score, error_occurred
        )
        
        # 全体の要確認フラグを更新
        if item_needs_review:
            needs_review = True
        
        # 統一された項目データ構造を作成
        item_data = {
            "raw_text": raw_text,
            "interpreted_text": interpreted_text,
            "similarity_score": similarity_score,
            "confidence_score": confidence_score,
            "needs_review": item_needs_review,
            "review_comment": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "error_occurred": error_occurred,
            "threshold": 0.7  # デフォルトの閾値
        }
        
        # jsonb_dataに格納 (従来の形式との互換性のため)
        jsonb_data[key] = item_data
        
        # review_itemsにも追加
        review_item = dict(item_data)
        review_item["item_name"] = key
        review_items.append(review_item)
    
    # 統一されたデータ構造
    unified_data = {
        "review_items": review_items,
        # テンプレート情報（空の場合は後でカスタマイズ抽出時に追加される）
        "template_id": None,
        "template_name": None,
        # 原文データと解釈データ（従来のAPI形式との互換性のため）
        "raw_items": [{"item_name": k, "raw_text": v.get("raw_text")} for k, v in jsonb_data.items()],
        "interpreted_items": [{"item_name": k, "interpreted_text": v.get("interpreted_text")} for k, v in jsonb_data.items()]
    }
    
    # jsonb_dataに統一データ構造のキーを追加
    jsonb_data.update(unified_data)
    
    # 全体の信頼度スコアは平均値を計算
    average_confidence = sum(item.get("confidence_score", 0) for item in review_items) / len(review_items) if review_items else 1.0
    
    return jsonb_data, needs_review, average_confidence


def sync_run_extraction_task(chart_id: UUID, gcs_uri: str, db_session: Session) -> None:
    """
    非同期タスクを同期的に実行するためのラッパー関数
    
    Args:
        chart_id: カルテID
        gcs_uri: GCSのURI
        db_session: データベースセッション
    """
    asyncio.run(run_extraction_task(chart_id, gcs_uri, db_session))
