from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from datetime import datetime

from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.db import models
from app.db.session import get_db
from app.schemas import chart as schemas
from app.services import db_service
from app.core.dependencies import get_api_key
import logging

# ロガー設定
logger = logging.getLogger(__name__)

router = APIRouter(
    # プレフィックスはメインアプリケーションで設定するためここでは設定しない
    # prefix="/api/v1/charts",
    tags=["review"],
    dependencies=[Depends(get_api_key)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{chart_id}/review-items", response_model=schemas.ReviewItemsResponse)
def get_review_items(
    chart_id: UUID = Path(..., description="カルテID"),
    get_all_items: bool = True,  # デフォルトで全ての項目を取得
    db: Session = Depends(get_db)
):
    """
    レビューが必要な項目のリストを取得する
    
    Args:
        chart_id: カルテID
        get_all_items: Trueの場合、needs_reviewフラグに関わらず全ての項目を返す
        db: データベースセッション
        
    Returns:
        ReviewItemsResponse: レビュー要項目のリストまたは全ての項目のリスト
    """
    logger.debug(f"リクエスト: get_review_items - chart_id: {chart_id}, get_all_items: {get_all_items}")
    
    # チャートの存在確認
    chart = db_service.get_chart_by_id(db, chart_id)
    if not chart:
        logger.error(f"Chart not found: {chart_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    # 処理完了前ならば空リストを返す
    if chart.status != models.ProcessStatus.COMPLETED and chart.status != models.ProcessStatus.PARTIAL_SUCCESS:
        logger.debug(f"Chart {chart_id} は処理完了していません: {chart.status}")
        return schemas.ReviewItemsResponse(
            chart_id=chart_id,
            review_items=[]
        )
    
    # レビュー要項目を取得
    review_items = db_service.get_review_items(db, chart_id, get_all_items)
    
    logger.debug(f"Chart {chart_id} の項目取得: {len(review_items)}件")
    if len(review_items) > 0:
        logger.debug(f"最初の項目のサンプル: {review_items[0].keys()}")
    
    # レスポンスを作成
    response = schemas.ReviewItemsResponse(
        chart_id=chart_id,
        review_items=[
            schemas.ExtractedItemDetail(
                id=item.get("id", 0),
                item_name=item.get("item_name", ""),
                raw_text=item.get("raw_text"),
                interpreted_text=item.get("interpreted_text"),
                similarity_score=item.get("similarity_score"),
                confidence_score=item.get("confidence_score"),
                needs_review=item.get("needs_review", True),
                review_comment=item.get("review_comment"),
                reviewed_by=item.get("reviewed_by"),
                reviewed_at=item.get("reviewed_at").isoformat() if isinstance(item.get("reviewed_at"), datetime) else item.get("reviewed_at")
            )
            for item in review_items
        ]
    )
    
    logger.debug(f"レスポンス項目数: {len(response.review_items)}")
    return response


@router.patch("/{chart_id}/items/{item_id}", response_model=schemas.ItemUpdateResponse)
def update_item(
    chart_id: UUID = Path(..., description="カルテID"),
    item_id: int = Path(..., description="項目ID"),
    item_update: schemas.ItemUpdateRequest = Body(..., description="更新データ"),
    db: Session = Depends(get_db)
):
    """
    抽出項目の更新・承認を行う（統一データアクセス層使用）
    
    Args:
        chart_id: カルテID
        item_id: 項目ID
        item_update: 更新データ
        db: データベースセッション
        
    Returns:
        schemas.ItemUpdateResponse: 更新した項目の情報
    """
    # デバッグログの追加
    logger.debug(f"PATCH request received - chart_id: {chart_id}, item_id: {item_id}")
    logger.debug(f"Request data: item_name={item_update.item_name}, interpreted_text={item_update.interpreted_text}, reviewed_by={item_update.reviewed_by}")
    
    # チャートの存在確認
    chart = db_service.get_chart_by_id(db, chart_id)
    if not chart:
        logger.error(f"Chart not found: {chart_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    # 抽出データの確認
    extracted_data = db_service.get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        logger.error(f"Extracted data not found for chart: {chart_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Extracted data not found"
        )
    
    # 抽出データのIDをログ出力
    logger.debug(f"Extracted data ID: {extracted_data.id}, comparing with item_id: {item_id}")
    
    # IDの検証は抽出データのIDがitem_idと一致するか確認する
    # フロントエンドから送信されるIDは抽出データのIDと一致する必要がある
    if extracted_data.id != item_id:
        logger.error(f"Item ID {item_id} does not match extracted data ID {extracted_data.id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Item ID does not match extracted data ID"
        )
    
    # 🎯 統一データアクセス層を使用した項目検索
    item_name = item_update.item_name
    logger.debug(f"統一データアクセス層を使用して項目 '{item_name}' を検索")
    
    # 全項目を統一形式で取得
    all_items = db_service.get_all_items_unified(db, chart_id)
    logger.debug(f"統一データアクセス層から取得した項目数: {len(all_items)}")
    
    # 項目名で検索
    target_item = db_service.find_item_by_name(all_items, item_name)
    
    if not target_item:
        available_items = [item.get("item_name") for item in all_items]
        logger.error(f"Item '{item_name}' not found in unified data. Available items: {available_items}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Item '{item_name}' not found"
        )
    
    logger.debug(f"項目 '{item_name}' を統一データアクセス層で発見しました")
    
    # 🎯 統一更新処理（データ構造に依存しない）
    updated = False
    
    # Step 1: review_items配列内での更新を試行
    if "review_items" in extracted_data.data and isinstance(extracted_data.data["review_items"], list):
        review_items = extracted_data.data["review_items"]
        
        for i, item in enumerate(review_items):
            if isinstance(item, dict) and item.get("item_name") == item_name:
                logger.debug(f"review_items[{i}]内の項目 '{item_name}' を更新")
                
                # 項目を更新
                review_item = review_items[i]
                if item_update.interpreted_text is not None:
                    review_item["interpreted_text"] = item_update.interpreted_text
                if item_update.review_comment is not None:
                    review_item["review_comment"] = item_update.review_comment
                
                # レビュー情報を更新
                review_item["reviewed_by"] = item_update.reviewed_by
                review_item["reviewed_at"] = datetime.now().isoformat()
                review_item["needs_review"] = False
                
                # 更新したreview_itemsでデータを上書き
                extracted_data.data["review_items"] = review_items
                updated = True
                logger.debug(f"review_items配列内で項目 '{item_name}' の更新完了")
                break
    
    # Step 2: review_items配列で見つからない場合は従来形式で更新
    if not updated and item_name in extracted_data.data and isinstance(extracted_data.data[item_name], dict):
        logger.debug(f"従来形式で項目 '{item_name}' を更新")
        
        item_data = extracted_data.data[item_name]
        
        # 更新値を適用
        if item_update.interpreted_text is not None:
            item_data["interpreted_text"] = item_update.interpreted_text
        if item_update.review_comment is not None:
            item_data["review_comment"] = item_update.review_comment
            
        # レビュー情報を更新
        item_data["reviewed_by"] = item_update.reviewed_by
        item_data["reviewed_at"] = datetime.now().isoformat()
        item_data["needs_review"] = False
        
        # 従来形式のデータを更新
        extracted_data.data[item_name] = item_data
        
        # review_items配列にも同期（統一性確保）
        if "review_items" not in extracted_data.data:
            extracted_data.data["review_items"] = []
            
        review_items = extracted_data.data["review_items"]
        existing_item_index = None
        
        for i, item in enumerate(review_items):
            if isinstance(item, dict) and item.get("item_name") == item_name:
                existing_item_index = i
                break
                
        # review_item作成
        review_item = dict(item_data)
        review_item["item_name"] = item_name
        
        # 既存のreview_itemがあれば更新、なければ追加
        if existing_item_index is not None:
            review_items[existing_item_index] = review_item
        else:
            review_items.append(review_item)
            
        # 更新したreview_itemsでデータを上書き
        extracted_data.data["review_items"] = review_items
        updated = True
        logger.debug(f"従来形式で項目 '{item_name}' の更新完了")
    
    # Step 3: 更新に失敗した場合はエラー
    if not updated:
        logger.error(f"項目 '{item_name}' の更新に失敗しました")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item '{item_name}'"
        )
    
    # SQLAlchemyに変更を通知（重要：これがないとJSONBの変更が保存されない）
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(extracted_data, "data")
    
    # データベースを更新
    db.commit()
    logger.debug(f"データベースコミット完了")
    
    # コミット後のデータを確認
    post_commit_data = db_service.get_extracted_data_by_chart_id(db, chart_id)
    if post_commit_data and item_name in post_commit_data.data:
        logger.debug(f"コミット後のDB内データ['{item_name}']: {post_commit_data.data[item_name]}")
    
    # 🎯 統一データアクセス層を使用して更新後の項目を取得
    updated_items = db_service.get_all_items_unified(db, chart_id)
    logger.debug(f"統一データアクセス層から取得した更新後項目数: {len(updated_items)}")
    
    updated_item = db_service.find_item_by_name(updated_items, item_name)
    if updated_item:
        logger.debug(f"取得したupdated_item: {updated_item}")
    else:
        logger.error(f"updated_itemが見つかりません: item_name='{item_name}'")
    
    if not updated_item:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated item"
        )
    
    # ChartsテーブルのレビューフラグをDB関数を使用して更新
    db_service.update_chart_review_status_after_item_update(db, chart_id)
    
    # レスポンススキーマに合わせて項目データを直接返す
    # reviewed_atがdatetimeオブジェクトの場合はISO文字列に変換
    reviewed_at = updated_item.get("reviewed_at")
    if isinstance(reviewed_at, datetime):
        reviewed_at = reviewed_at.isoformat()
    
    return schemas.ItemUpdateResponse(
        id=updated_item.get("id", 0),
        item_name=updated_item.get("item_name", ""),
        raw_text=updated_item.get("raw_text"),
        interpreted_text=updated_item.get("interpreted_text"),
        similarity_score=updated_item.get("similarity_score"),
        confidence_score=updated_item.get("confidence_score"),
        needs_review=updated_item.get("needs_review", False),
        review_comment=updated_item.get("review_comment"),
        reviewed_by=updated_item.get("reviewed_by"),
        reviewed_at=reviewed_at
    )


@router.post("/{chart_id}/convert-format", response_model=schemas.GenericResponse)
def convert_data_format(
    chart_id: UUID = Path(..., description="カルテID"),
    db: Session = Depends(get_db)
):
    """
    カスタマイズ抽出データ形式を標準形式に変換する
    
    Args:
        chart_id: カルテID
        db: データベースセッション
        
    Returns:
        schemas.GenericResponse: 処理結果
    """
    logger.info(f"データ形式変換リクエスト - chart_id: {chart_id}")
    
    # カルテの存在確認
    chart = db_service.get_chart_by_id(db, chart_id)
    if not chart:
        logger.error(f"カルテが見つかりません - chart_id: {chart_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Chart with ID {chart_id} not found"
        )
    
    # 抽出データの存在確認
    extracted_data = db_service.get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        logger.error(f"抽出データが見つかりません - chart_id: {chart_id}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Extracted data for chart ID {chart_id} not found"
        )
    
    # データ形式を変換
    success = db_service.convert_to_standard_format(db, chart_id)
    
    if success:
        logger.info(f"データ形式の変換に成功しました - chart_id: {chart_id}")
        return {"success": True, "message": "データ形式を標準形式に変換しました"}
    else:
        logger.error(f"データ形式の変換に失敗しました - chart_id: {chart_id}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert data format"
        ) 