from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import ExtractionTemplate, ExtractionTemplateItem, Chart
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateItemCreate, TemplateItemUpdate, SimilarityThresholdUpdate
import logging

logger = logging.getLogger("app.services.template_service")
logger.setLevel(logging.DEBUG)


class TemplateService:
    """テンプレート管理を統合するサービスクラス"""
    
    def __init__(self):
        pass
    
    def get_all_templates(self, db: Session, template_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        テンプレート一覧を取得する
        
        Args:
            db: データベースセッション
            template_type: フィルタリングするテンプレートタイプ
            limit: 返却する最大結果数
            offset: ページネーション用オフセット
            
        Returns:
            テンプレート一覧を含む辞書
        """
        return get_all_templates(db, template_type, limit, offset)
    
    def get_template_by_id(self, db: Session, template_id: UUID) -> Optional[Dict[str, Any]]:
        """
        指定IDのテンプレートを取得する
        
        Args:
            db: データベースセッション
            template_id: テンプレートID
            
        Returns:
            テンプレート詳細を含む辞書
        """
        return get_template_by_id(db, template_id)
    
    def create_template(self, db: Session, template_data: TemplateCreate) -> Dict[str, Any]:
        """
        新しいテンプレートを作成する
        
        Args:
            db: データベースセッション
            template_data: テンプレート作成データ
            
        Returns:
            作成されたテンプレート
        """
        return create_template(db, template_data)
    
    def update_template(self, db: Session, template_id: UUID, update_data: TemplateUpdate) -> Optional[Dict[str, Any]]:
        """
        テンプレートを更新する
        
        Args:
            db: データベースセッション
            template_id: 更新するテンプレートID
            update_data: 更新データ
            
        Returns:
            更新されたテンプレート、存在しない場合はNone
        """
        return update_template(db, template_id, update_data)
    
    def delete_template(self, db: Session, template_id: UUID) -> bool:
        """
        テンプレートを削除する
        
        Args:
            db: データベースセッション
            template_id: 削除するテンプレートID
            
        Returns:
            削除成功フラグ
        """
        return delete_template(db, template_id)
    
    def get_template_items(self, db: Session, template_id: UUID) -> List[Dict[str, Any]]:
        """
        テンプレート項目一覧を取得する
        
        Args:
            db: データベースセッション
            template_id: テンプレートID
            
        Returns:
            テンプレート項目一覧
        """
        return get_template_items(db, template_id)

    def update_similarity_thresholds(self, db: Session, template_id: UUID, threshold_updates: List[SimilarityThresholdUpdate]) -> List[Dict[str, Any]]:
        """
        テンプレートの類似度閾値を一括更新する
        
        Args:
            db: データベースセッション
            template_id: テンプレートID
            threshold_updates: 更新する閾値データのリスト
            
        Returns:
            更新された項目のリスト
        """
        # テンプレートの存在確認
        template = db.query(ExtractionTemplate).filter(
            ExtractionTemplate.id == template_id,
            ExtractionTemplate.is_active == True
        ).first()
        
        if not template:
            logger.error(f"Template not found: {template_id}")
            return []
        
        updated_items = []
        
        try:
            for update in threshold_updates:
                item_id = update.item_id
                text_threshold = update.text_similarity_threshold
                vector_threshold = update.vector_similarity_threshold
                
                # 項目の存在確認
                item = db.query(ExtractionTemplateItem).filter(
                    ExtractionTemplateItem.id == item_id,
                    ExtractionTemplateItem.template_id == template_id
                ).first()
                
                if not item:
                    logger.warning(f"Template item not found: {item_id}")
                    continue
                
                # 閾値の更新
                if text_threshold is not None:
                    item.text_similarity_threshold = text_threshold
                if vector_threshold is not None:
                    item.vector_similarity_threshold = vector_threshold
                
                item.updated_at = datetime.now()
                
                updated_items.append({
                    "id": item.id,
                    "template_id": item.template_id,
                    "name": item.name,
                    "enabled": item.enabled,
                    "display_order": item.display_order,
                    "description": item.description,
                    "confidence_threshold": item.confidence_threshold,
                    "text_similarity_threshold": item.text_similarity_threshold,
                    "vector_similarity_threshold": item.vector_similarity_threshold,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at
                })
            
            db.commit()
            logger.info(f"Updated similarity thresholds for {len(updated_items)} items in template {template_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update similarity thresholds: {str(e)}")
            return []
        
        return updated_items

    def reset_similarity_thresholds(self, db: Session, template_id: UUID) -> List[Dict[str, Any]]:
        """
        テンプレートの類似度閾値をデフォルト値にリセットする
        
        Args:
            db: データベースセッション
            template_id: テンプレートID
            
        Returns:
            リセットされた項目のリスト
        """
        return reset_similarity_thresholds(db, template_id)


# シングルトンインスタンス
_template_service_instance = None


def get_template_service() -> TemplateService:
    """
    TemplateServiceのシングルトンインスタンスを取得する
    
    Returns:
        TemplateService: TemplateServiceインスタンス
    """
    global _template_service_instance
    if _template_service_instance is None:
        _template_service_instance = TemplateService()
    return _template_service_instance


def get_all_templates(
    db: Session, template_type: Optional[str] = None, limit: int = 20, offset: int = 0
) -> Dict[str, Any]:
    """
    テンプレート一覧を取得する
    
    Args:
        db: データベースセッション
        template_type: フィルタリングするテンプレートタイプ ("system", "user", "all")
        limit: 返却する最大結果数
        offset: ページネーション用オフセット
        
    Returns:
        テンプレート一覧を含む辞書
    """
    query = db.query(ExtractionTemplate).filter(ExtractionTemplate.is_active == True)
    
    if template_type and template_type != "all":
        query = query.filter(ExtractionTemplate.type == template_type)
    
    total = query.count()
    templates = query.order_by(ExtractionTemplate.created_at.desc()).limit(limit).offset(offset).all()
    
    result = []
    for template in templates:
        item_count = db.query(func.count(ExtractionTemplateItem.id)).filter(
            ExtractionTemplateItem.template_id == template.id,
            ExtractionTemplateItem.enabled == True
        ).scalar()
        
        template_dict = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "type": template.type,
            "created_at": template.created_at,
            "created_by": template.created_by,
            "is_active": template.is_active,
            "item_count": item_count
        }
        result.append(template_dict)
    
    return {
        "total": total,
        "templates": result
    }


def get_template_by_id(db: Session, template_id: UUID) -> Optional[Dict[str, Any]]:
    """
    指定IDのテンプレートを取得する
    
    Args:
        db: データベースセッション
        template_id: テンプレートID
        
    Returns:
        テンプレート詳細を含む辞書
    """
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id,
        ExtractionTemplate.is_active == True
    ).first()
    
    if not template:
        return None
    
    items = db.query(ExtractionTemplateItem).filter(
        ExtractionTemplateItem.template_id == template_id
    ).order_by(ExtractionTemplateItem.display_order).all()
    
    template_dict = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "type": template.type,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "created_by": template.created_by,
        "is_active": template.is_active,
        "items": [{
            "id": item.id,
            "template_id": item.template_id,
            "name": item.name,
            "enabled": item.enabled,
            "display_order": item.display_order,
            "description": item.description,
            "confidence_threshold": item.confidence_threshold,
            "text_similarity_threshold": item.text_similarity_threshold,
            "vector_similarity_threshold": item.vector_similarity_threshold,
            "created_at": item.created_at,
            "updated_at": item.updated_at
        } for item in items]
    }
    
    return template_dict


def create_template(db: Session, template_data: TemplateCreate) -> Dict[str, Any]:
    """
    新しいテンプレートを作成する
    
    Args:
        db: データベースセッション
        template_data: テンプレート作成データ
        
    Returns:
        作成されたテンプレート
    """
    template = ExtractionTemplate(
        name=template_data.name,
        description=template_data.description,
        type=template_data.type,
        created_by=template_data.created_by,
        is_active=template_data.is_active
    )
    
    db.add(template)
    db.flush()
    
    items = []
    for i, item_data in enumerate(template_data.items):
        item = ExtractionTemplateItem(
            template_id=template.id,
            name=item_data.name,
            enabled=item_data.enabled,
            display_order=item_data.display_order or (i + 1),
            description=item_data.description,
            confidence_threshold=item_data.confidence_threshold,
            text_similarity_threshold=item_data.text_similarity_threshold,
            vector_similarity_threshold=item_data.vector_similarity_threshold
        )
        db.add(item)
        items.append(item)
    
    db.commit()
    db.refresh(template)
    
    return get_template_by_id(db, template.id)


def update_template(
    db: Session, template_id: UUID, update_data: TemplateUpdate
) -> Optional[Dict[str, Any]]:
    """
    テンプレートを更新する
    
    Args:
        db: データベースセッション
        template_id: 更新するテンプレートID
        update_data: 更新データ
        
    Returns:
        更新されたテンプレート、存在しない場合はNone
    """
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()
    
    if not template:
        return None
    
    # システムテンプレートはタイプを変更できない
    if template.type == "system" and update_data.type == "user":
        logger.warning(f"Cannot change system template type to user: {template_id}")
        update_data.type = "system"
    
    # 基本情報の更新
    if update_data.name is not None:
        template.name = update_data.name
    if update_data.description is not None:
        template.description = update_data.description
    if update_data.is_active is not None:
        template.is_active = update_data.is_active
    
    template.updated_at = datetime.now()
    
    # 項目リストが指定されていれば、更新
    if update_data.items is not None:
        # 既存項目のIDマッピングを作成
        existing_items = {str(item.id): item for item in db.query(ExtractionTemplateItem).filter(
            ExtractionTemplateItem.template_id == template_id
        ).all()}
        
        # 新しい項目リストを処理
        for i, item_data in enumerate(update_data.items):
            item_id = getattr(item_data, 'id', None)
            
            if item_id and str(item_id) in existing_items:
                # 既存項目の更新
                item = existing_items[str(item_id)]
                item.name = item_data.name
                item.enabled = item.enabled
                item.display_order = item_data.display_order or (i + 1)
                item.description = item_data.description
                item.confidence_threshold = item_data.confidence_threshold
                # 閾値フィールドは保護（専用APIでのみ更新可能）
                # item.text_similarity_threshold = item_data.text_similarity_threshold
                # item.vector_similarity_threshold = item_data.vector_similarity_threshold
                item.updated_at = datetime.now()
                
                # 処理済みの項目をマッピングから削除
                del existing_items[str(item_id)]
            else:
                # 新規項目の追加
                item = ExtractionTemplateItem(
                    template_id=template.id,
                    name=item_data.name,
                    enabled=item_data.enabled,
                    display_order=item_data.display_order or (i + 1),
                    description=item_data.description,
                    confidence_threshold=item_data.confidence_threshold,
                    text_similarity_threshold=item_data.text_similarity_threshold,
                    vector_similarity_threshold=item_data.vector_similarity_threshold
                )
                db.add(item)
        
        # 残った項目（更新対象に含まれなかった項目）を削除
        for item_id, item in existing_items.items():
            db.delete(item)
    
    db.commit()
    db.refresh(template)
    
    return get_template_by_id(db, template.id)


def delete_template(db: Session, template_id: UUID) -> bool:
    """
    テンプレートを削除する（論理削除）
    
    Args:
        db: データベースセッション
        template_id: 削除するテンプレートID
        
    Returns:
        削除の成否
    """
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id
    ).first()
    
    if not template:
        return False
    
    # システムテンプレートは削除できない
    if template.type == "system":
        logger.warning(f"Cannot delete system template: {template_id}")
        return False
    
    # 使用中のテンプレートかチェック
    used_chart_count = db.query(func.count(Chart.id)).filter(
        Chart.template_id == template_id
    ).scalar()
    
    if used_chart_count > 0:
        # 使用中のテンプレートは論理削除のみ
        template.is_active = False
        template.updated_at = datetime.now()
        db.commit()
        return True
    else:
        # 使用されていなければ物理削除
        db.delete(template)
        db.commit()
        return True


def update_template_item(
    db: Session, item_id: UUID, update_data: TemplateItemUpdate
) -> Optional[Dict[str, Any]]:
    """
    テンプレート項目を更新する
    
    Args:
        db: データベースセッション
        item_id: 更新する項目ID
        update_data: 更新データ
        
    Returns:
        更新された項目、存在しない場合はNone
    """
    item = db.query(ExtractionTemplateItem).filter(
        ExtractionTemplateItem.id == item_id
    ).first()
    
    if not item:
        return None
    
    # テンプレートの種類をチェック
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == item.template_id
    ).first()
    
    if template.type == "system":
        # システムテンプレートの項目は名前と説明を変更できない
        if update_data.name is not None or update_data.description is not None:
            logger.warning(f"Cannot change name or description of system template item: {item_id}")
            update_data.name = None
            update_data.description = None
    
    # 項目の更新
    if update_data.name is not None:
        item.name = update_data.name
    if update_data.enabled is not None:
        item.enabled = update_data.enabled
    if update_data.display_order is not None:
        item.display_order = update_data.display_order
    if update_data.description is not None:
        item.description = update_data.description
    if update_data.confidence_threshold is not None:
        item.confidence_threshold = update_data.confidence_threshold
    if update_data.text_similarity_threshold is not None:
        item.text_similarity_threshold = update_data.text_similarity_threshold
    if update_data.vector_similarity_threshold is not None:
        item.vector_similarity_threshold = update_data.vector_similarity_threshold
    
    item.updated_at = datetime.now()
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "template_id": item.template_id,
        "name": item.name,
        "enabled": item.enabled,
        "display_order": item.display_order,
        "description": item.description,
        "confidence_threshold": item.confidence_threshold,
        "text_similarity_threshold": item.text_similarity_threshold,
        "vector_similarity_threshold": item.vector_similarity_threshold,
        "created_at": item.created_at,
        "updated_at": item.updated_at
    }


def get_template_items(db: Session, template_id: UUID) -> List[Dict[str, Any]]:
    """
    テンプレートの項目リストを取得する
    
    Args:
        db: データベースセッション
        template_id: テンプレートID
        
    Returns:
        項目リスト
    """
    items = db.query(ExtractionTemplateItem).filter(
        ExtractionTemplateItem.template_id == template_id
    ).order_by(ExtractionTemplateItem.display_order).all()
    
    return [{
        "id": item.id,
        "template_id": item.template_id,
        "name": item.name,
        "enabled": item.enabled,
        "display_order": item.display_order,
        "description": item.description,
        "confidence_threshold": item.confidence_threshold,
        "text_similarity_threshold": item.text_similarity_threshold,
        "vector_similarity_threshold": item.vector_similarity_threshold,
        "created_at": item.created_at,
        "updated_at": item.updated_at
    } for item in items]


def delete_template_item(db: Session, item_id: UUID) -> bool:
    """
    テンプレート項目を削除する
    
    Args:
        db: データベースセッション
        item_id: 削除する項目ID
        
    Returns:
        削除の成否
    """
    item = db.query(ExtractionTemplateItem).filter(
        ExtractionTemplateItem.id == item_id
    ).first()
    
    if not item:
        return False
    
    # テンプレートのタイプを確認
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == item.template_id
    ).first()
    
    if template.type == "system":
        # システムテンプレートの項目は削除不可
        logger.warning(f"Cannot delete item from system template: {item_id}")
        return False
        
    # 削除後に残る項目数を確認（最低1項目は残す）
    remaining_count = db.query(func.count(ExtractionTemplateItem.id)).filter(
        ExtractionTemplateItem.template_id == item.template_id,
        ExtractionTemplateItem.id != item_id
    ).scalar()
    
    if remaining_count == 0:
        logger.warning(f"Cannot delete the last item from template: {item.template_id}")
        return False
    
    # 項目の削除
    db.delete(item)
    
    # 残りの項目の表示順序を再設定
    remaining_items = db.query(ExtractionTemplateItem).filter(
        ExtractionTemplateItem.template_id == item.template_id
    ).order_by(ExtractionTemplateItem.display_order).all()
    
    for i, remaining_item in enumerate(remaining_items):
        remaining_item.display_order = i + 1
    
    db.commit()
    return True


def reset_similarity_thresholds(db: Session, template_id: UUID) -> List[Dict[str, Any]]:
    """
    テンプレートの類似度閾値をデフォルト値にリセットする
    
    Args:
        db: データベースセッション
        template_id: テンプレートID
        
    Returns:
        リセットされた項目のリスト
    """
    # テンプレートの存在確認
    template = db.query(ExtractionTemplate).filter(
        ExtractionTemplate.id == template_id,
        ExtractionTemplate.is_active == True
    ).first()
    
    if not template:
        logger.error(f"Template not found: {template_id}")
        return []
    
    # デフォルト値の定義
    DEFAULT_TEXT_SIMILARITY_THRESHOLD = 0.8
    DEFAULT_VECTOR_SIMILARITY_THRESHOLD = 0.7
    
    try:
        # テンプレートの全項目を取得
        items = db.query(ExtractionTemplateItem).filter(
            ExtractionTemplateItem.template_id == template_id
        ).all()
        
        reset_items = []
        
        for item in items:
            # デフォルト値にリセット
            item.text_similarity_threshold = DEFAULT_TEXT_SIMILARITY_THRESHOLD
            item.vector_similarity_threshold = DEFAULT_VECTOR_SIMILARITY_THRESHOLD
            item.updated_at = datetime.now()
            
            reset_items.append({
                "id": item.id,
                "template_id": item.template_id,
                "name": item.name,
                "enabled": item.enabled,
                "display_order": item.display_order,
                "description": item.description,
                "confidence_threshold": item.confidence_threshold,
                "text_similarity_threshold": item.text_similarity_threshold,
                "vector_similarity_threshold": item.vector_similarity_threshold,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            })
        
        db.commit()
        logger.info(f"Reset similarity thresholds for {len(reset_items)} items in template {template_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset similarity thresholds: {str(e)}")
        return []
    
    return reset_items


def update_similarity_thresholds(
    db: Session, template_id: UUID, threshold_updates: List[SimilarityThresholdUpdate]
) -> List[Dict[str, Any]]:
    """
    テンプレートの類似度閾値を一括更新する
    
    Args:
        db: データベースセッション
        template_id: テンプレートID
        threshold_updates: 更新する閾値データのリスト
        
    Returns:
        更新された項目のリスト
    """
    service = get_template_service()
    return service.update_similarity_thresholds(db, template_id, threshold_updates) 