from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.schemas.template import (
    TemplateList, Template, TemplateCreate, TemplateUpdate, TemplateItem, TemplateItemUpdate,
    SimilarityThresholdUpdate, BulkSimilarityThresholdUpdate
)
from app.services import template_service

# ロガーを設定
logger = logging.getLogger(__name__)

router = APIRouter(
    # プレフィックスをメインアプリケーションで設定するためここでは設定しない
    # prefix="/api/templates", 
    tags=["templates"]
)


@router.get("/", response_model=TemplateList)
def get_templates(
    template_type: Optional[str] = Query(None, description="テンプレートタイプ（system, user, all）"),
    limit: int = Query(20, ge=1, le=100, description="取得する最大件数"),
    offset: int = Query(0, ge=0, description="取得開始位置"),
    db: Session = Depends(get_db)
):
    """
    テンプレート一覧を取得する
    """
    return template_service.get_all_templates(db, template_type, limit, offset)


@router.get("/{template_id}", response_model=Template)
def get_template(
    template_id: UUID = Path(..., description="テンプレートID"),
    db: Session = Depends(get_db)
):
    """
    指定IDのテンプレート詳細を取得する
    """
    template = template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/{template_id}/", response_model=Template)
def get_template_with_slash(
    template_id: UUID = Path(..., description="テンプレートID"),
    db: Session = Depends(get_db)
):
    """
    指定IDのテンプレート詳細を取得する（末尾スラッシュ対応）
    """
    return get_template(template_id, db)


@router.post("/", response_model=Template, status_code=201)
def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db)
):
    """
    新しいテンプレートを作成する
    """
    return template_service.create_template(db, template_data)


@router.put("/{template_id}", response_model=Template)
def update_template(
    template_id: UUID,
    update_data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    テンプレートを更新する
    """
    template = template_service.update_template(db, template_id, update_data)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/{template_id}/", response_model=Template)
def update_template_with_slash(
    template_id: UUID,
    update_data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    テンプレートを更新する（末尾スラッシュ対応）
    """
    return update_template(template_id, update_data, db)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレートを削除する
    """
    success = template_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or cannot be deleted")
    return None


@router.delete("/{template_id}/", status_code=204)
def delete_template_with_slash(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレートを削除する（末尾スラッシュ対応）
    """
    return delete_template(template_id, db)


@router.get("/{template_id}/items", response_model=List[TemplateItem])
def get_template_items(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレートの項目リストを取得する
    """
    # テンプレートの存在確認
    template = template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template_service.get_template_items(db, template_id)


@router.put("/items/{item_id}", response_model=TemplateItem)
def update_template_item(
    item_id: UUID,
    update_data: TemplateItemUpdate,
    db: Session = Depends(get_db)
):
    """
    テンプレート項目を更新する
    """
    item = template_service.update_template_item(db, item_id, update_data)
    if not item:
        raise HTTPException(status_code=404, detail="Template item not found")
    return item


@router.put("/items/{item_id}/", response_model=TemplateItem)
def update_template_item_with_slash(
    item_id: UUID,
    update_data: TemplateItemUpdate,
    db: Session = Depends(get_db)
):
    """
    テンプレート項目を更新する（末尾スラッシュ対応）
    """
    return update_template_item(item_id, update_data, db)


@router.delete("/items/{item_id}", status_code=204)
def delete_template_item(
    item_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレート項目を削除する
    """
    success = template_service.delete_template_item(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template item not found or cannot be deleted")
    return None


@router.delete("/items/{item_id}/", status_code=204)
def delete_template_item_with_slash(
    item_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレート項目を削除する（末尾スラッシュ対応）
    """
    return delete_template_item(item_id, db)


@router.put("/{template_id}/similarity-thresholds", response_model=List[TemplateItem])
def update_similarity_thresholds(
    template_id: UUID,
    threshold_updates: BulkSimilarityThresholdUpdate,
    db: Session = Depends(get_db)
):
    """
    テンプレートの類似度閾値を一括更新する
    """
    # テンプレートの存在確認
    template = template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 一括更新実行
    updated_items = template_service.update_similarity_thresholds(
        db, template_id, threshold_updates.updates
    )
    
    if not updated_items:
        raise HTTPException(status_code=400, detail="Failed to update similarity thresholds")
    
    return updated_items


@router.get("/{template_id}/similarity-thresholds")
def get_similarity_thresholds(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレートの類似度閾値設定を取得する
    """
    # テンプレートの存在確認
    template = template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    items = template_service.get_template_items(db, template_id)
    
    # 類似度閾値情報のみを抽出
    threshold_info = []
    for item in items:
        threshold_info.append({
            "item_id": item["id"],
            "item_name": item["name"],
            "text_similarity_threshold": item["text_similarity_threshold"],
            "vector_similarity_threshold": item["vector_similarity_threshold"],
            "confidence_threshold": item["confidence_threshold"]
        })
    
    return {
        "template_id": template_id,
        "template_name": template["name"],
        "thresholds": threshold_info
    }


@router.post("/{template_id}/reset-thresholds", response_model=List[TemplateItem])
def reset_similarity_thresholds(
    template_id: UUID,
    db: Session = Depends(get_db)
):
    """
    テンプレートの類似度閾値をデフォルト値にリセットする
    """
    # テンプレートの存在確認
    template = template_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # デフォルト値でリセット
    reset_items = template_service.reset_similarity_thresholds(db, template_id)
    
    if not reset_items:
        raise HTTPException(status_code=400, detail="Failed to reset similarity thresholds")
    
    return reset_items 