from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.sql import extract
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from app.db.models import Chart, ExtractedData, ProcessStatus, ExtractionTemplate, ExtractionTemplateItem
from app.schemas.template import TemplateCreate, TemplateItemCreate
import logging

# ロガー設定
logger = logging.getLogger("app.services.db_service")
logger.setLevel(logging.DEBUG)


class DBService:
    """データベース操作を統合するサービスクラス"""
    
    def create_chart(
        self, 
        filename: str, 
        content_type: str, 
        file_size: int, 
        uploaded_by: str, 
        db: Session,
        gcs_uri: Optional[str] = None,
        template_id: Optional[UUID] = None
    ) -> Chart:
        """
        新しいカルテレコードを作成する
        
        Args:
            filename: ファイル名
            content_type: コンテンツタイプ
            file_size: ファイルサイズ
            uploaded_by: アップロード者
            db: データベースセッション
            gcs_uri: GCSのURI（任意）
            template_id: テンプレートID（任意）
            
        Returns:
            Chart: 作成されたカルテレコード
        """
        logger.debug(f"DBに保存を開始します: {filename}")
        try:
            chart = Chart(
                original_filename=filename,
                gcs_uri=gcs_uri or f"gs://test-bucket/{filename}",
                content_type=content_type,
                status=ProcessStatus.PENDING,
                needs_review=False,
                overall_confidence_score=None,
                template_id=template_id
            )
            db.add(chart)
            db.commit()
            db.refresh(chart)
            logger.debug(f"DBへの保存が完了しました: {chart.id}")
            return chart
        except Exception as e:
            logger.error(f"DBへの保存中にエラーが発生しました: {e}")
            db.rollback()
            raise

    def get_chart(self, chart_id: UUID, db: Session) -> Optional[Chart]:
        """
        IDでカルテを取得する
        
        Args:
            chart_id: カルテID
            db: データベースセッション
            
        Returns:
            Optional[Chart]: 見つかったカルテまたはNone
        """
        return db.query(Chart).filter(Chart.id == chart_id).first()

    def update_chart_status(
        self, 
        chart_id: UUID, 
        status: ProcessStatus, 
        db: Session,
        error_message: Optional[str] = None
    ) -> Optional[Chart]:
        """
        カルテのステータスを更新する
        
        Args:
            chart_id: カルテID
            status: 新しいステータス
            db: データベースセッション
            error_message: エラーメッセージ（任意）
            
        Returns:
            Optional[Chart]: 更新されたカルテまたはNone
        """
        chart = self.get_chart(chart_id, db)
        if not chart:
            return None
        
        chart.status = status
        if error_message:
            chart.error_message = error_message
        
        db.commit()
        db.refresh(chart)
        return chart

    def create_extracted_data(
        self,
        chart_id: UUID,
        data: Dict[str, Any],
        extracted_at: datetime,
        extraction_method: str,
        db: Session
    ) -> ExtractedData:
        """
        抽出データを作成する
        
        Args:
            chart_id: カルテID
            data: 抽出データ
            extracted_at: 抽出日時
            extraction_method: 抽出方法
            db: データベースセッション
            
        Returns:
            ExtractedData: 作成された抽出データ
        """
        try:
            # 既存データがあれば削除
            existing = db.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()
            if existing:
                db.delete(existing)
                db.flush()
            
            extracted_data = ExtractedData(
                chart_id=chart_id,
                data=data,
                extracted_timestamp=extracted_at
            )
            
            db.add(extracted_data)
            db.commit()
            db.refresh(extracted_data)
            
            return extracted_data
        except Exception as e:
            logger.error(f"抽出データ保存中にエラーが発生しました: {e}")
            db.rollback()
            raise

    def get_chart_with_extracted_data(self, chart_id: UUID, db: Session) -> Optional[Chart]:
        """
        抽出データを含むカルテを取得する
        
        Args:
            chart_id: カルテID
            db: データベースセッション
            
        Returns:
            Optional[Chart]: カルテと抽出データ
        """
        return db.query(Chart).filter(Chart.id == chart_id).first()

    def create_template(self, template_data: TemplateCreate, db: Session) -> ExtractionTemplate:
        """
        テンプレートを作成する
        
        Args:
            template_data: テンプレート作成データ
            db: データベースセッション
            
        Returns:
            ExtractionTemplate: 作成されたテンプレート
        """
        try:
            template = ExtractionTemplate(
                name=template_data.name,
                description=template_data.description,
                type=template_data.type,
                created_by=template_data.created_by,
                is_active=template_data.is_active
            )
            
            db.add(template)
            db.flush()  # IDを取得するためにflush
            
            # テンプレート項目を作成
            for item_data in template_data.items:
                template_item = ExtractionTemplateItem(
                    template_id=template.id,
                    name=item_data.name,
                    enabled=item_data.enabled,
                    display_order=item_data.display_order,
                    description=item_data.description,
                    confidence_threshold=item_data.confidence_threshold
                )
                db.add(template_item)
            
            db.commit()
            db.refresh(template)
            
            return template
        except Exception as e:
            logger.error(f"テンプレート作成中にエラーが発生しました: {e}")
            db.rollback()
            raise

    def get_template(self, template_id: UUID, db: Session) -> Optional[ExtractionTemplate]:
        """
        テンプレートを取得する
        
        Args:
            template_id: テンプレートID
            db: データベースセッション
            
        Returns:
            Optional[ExtractionTemplate]: テンプレート
        """
        return db.query(ExtractionTemplate).filter(ExtractionTemplate.id == template_id).first()

    def get_all_templates(self, db: Session, limit: int = 20, offset: int = 0) -> List[ExtractionTemplate]:
        """
        全テンプレートを取得する
        
        Args:
            db: データベースセッション
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            List[ExtractionTemplate]: テンプレートリスト
        """
        return db.query(ExtractionTemplate).filter(
            ExtractionTemplate.is_active == True
        ).order_by(ExtractionTemplate.created_at.desc()).limit(limit).offset(offset).all()

    def update_template(
        self, 
        template_id: UUID, 
        name: str, 
        description: str, 
        db: Session
    ) -> Optional[ExtractionTemplate]:
        """
        テンプレートを更新する
        
        Args:
            template_id: テンプレートID
            name: 新しい名前
            description: 新しい説明
            db: データベースセッション
            
        Returns:
            Optional[ExtractionTemplate]: 更新されたテンプレート
        """
        template = self.get_template(template_id, db)
        if not template:
            return None
        
        template.name = name
        template.description = description
        template.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(template)
        
        return template

    def delete_template(self, template_id: UUID, db: Session) -> bool:
        """
        テンプレートを削除する
        
        Args:
            template_id: テンプレートID
            db: データベースセッション
            
        Returns:
            bool: 削除成功フラグ
        """
        template = self.get_template(template_id, db)
        if not template:
            return False
        
        template.is_active = False
        db.commit()
        
        return True


# シングルトンインスタンス
_db_service_instance = None


def get_db_service() -> DBService:
    """
    DBServiceのシングルトンインスタンスを取得する
    
    Returns:
        DBService: DBServiceインスタンス
    """
    global _db_service_instance
    if _db_service_instance is None:
        _db_service_instance = DBService()
    return _db_service_instance


# 既存の関数は保持（後方互換性のため）
def create_chart_record(
    db: Session, chart_id: UUID, original_filename: str, gcs_uri: str, content_type: str, 
    template_id: Optional[UUID] = None
) -> Chart:
    """
    新しいカルテレコードを作成する
    
    Args:
        db: データベースセッション
        chart_id: カルテID (UUID)
        original_filename: 元のファイル名
        gcs_uri: GCSのURI
        content_type: コンテンツタイプ
        template_id: テンプレートID (任意)
        
    Returns:
        Chart: 作成されたカルテレコード
    """
    logger.debug(f"DBに保存を開始します: {chart_id}")
    try:
        chart = Chart(
            id=chart_id,
            original_filename=original_filename,
            gcs_uri=gcs_uri,
            content_type=content_type,
            status=ProcessStatus.PENDING,
            needs_review=False,
            overall_confidence_score=None,
            template_id=template_id
        )
        db.add(chart)
        db.commit()
        db.refresh(chart)
        logger.debug(f"DBへの保存が完了しました: {chart_id}")
        return chart
    except Exception as e:
        logger.error(f"DBへの保存中にエラーが発生しました: {e}")
        db.rollback()
        raise


def get_chart_by_id(db: Session, chart_id: UUID) -> Optional[Chart]:
    """
    IDでカルテを取得する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        Optional[Chart]: 見つかったカルテまたはNone
    """
    return db.query(Chart).filter(Chart.id == chart_id).first()


def update_chart_status(
    db: Session, chart_id: UUID, status: ProcessStatus, error_message: Optional[str] = None
) -> Optional[Chart]:
    """
    カルテのステータスを更新する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        status: 新しいステータス
        error_message: エラーメッセージ（任意）
        
    Returns:
        Optional[Chart]: 更新されたカルテまたはNone
    """
    chart = get_chart_by_id(db, chart_id)
    if not chart:
        return None
    
    chart.status = status
    if error_message:
        chart.error_message = error_message
    
    db.commit()
    db.refresh(chart)
    return chart


def update_chart_review_status(
    db: Session, 
    chart_id: UUID, 
    needs_review: bool, 
    overall_confidence_score: Optional[float] = None,
    reviewed_by: Optional[str] = None
) -> Optional[Chart]:
    """
    カルテのレビュー状態を更新する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        needs_review: レビューが必要かどうか
        overall_confidence_score: 全体の信頼度スコア
        reviewed_by: レビュー担当者（レビュー完了時）
        
    Returns:
        Optional[Chart]: 更新されたカルテまたはNone
    """
    chart = get_chart_by_id(db, chart_id)
    if not chart:
        return None
    
    chart.needs_review = needs_review
    
    if overall_confidence_score is not None:
        chart.overall_confidence_score = overall_confidence_score
    
    if reviewed_by and not needs_review:
        chart.reviewed_by = reviewed_by
        chart.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(chart)
    return chart


def create_extracted_data_jsonb(
    db: Session, 
    chart_id: UUID, 
    data: Dict[str, Any],
    overall_confidence_score: Optional[float] = None,
    needs_review: bool = False
) -> Optional[ExtractedData]:
    """
    抽出データをJSONB型でデータベースに保存する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        data: JSONB型で保存するデータ辞書
        overall_confidence_score: 全体の信頼度スコア
        needs_review: レビュー要否フラグ
        
    Returns:
        Optional[ExtractedData]: 作成された抽出データまたはNone
    """
    try:
        # 既存データがあれば削除（1カルテにつき1つのExtractedDataレコード）
        existing = db.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()
        if existing:
            db.delete(existing)
            db.flush()
        
        # 新しいExtractedDataを作成
        extracted_data = ExtractedData(
            chart_id=chart_id,
            data=data,
            extracted_timestamp=datetime.now()
        )
        
        db.add(extracted_data)
        db.commit()
        db.refresh(extracted_data)
        
        # カルテのレビュー情報を更新
        update_chart_review_status(
            db, chart_id, needs_review, overall_confidence_score
        )
        
        return extracted_data
    except Exception as e:
        logger.error(f"抽出データ保存中にエラーが発生しました: {e}")
        db.rollback()
        raise


def get_extracted_data_by_chart_id(db: Session, chart_id: UUID) -> Optional[ExtractedData]:
    """
    カルテIDに関連する抽出データを取得する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        Optional[ExtractedData]: 抽出データまたはNone
    """
    return db.query(ExtractedData).filter(ExtractedData.chart_id == chart_id).first()


def update_item_review_status(
    db: Session,
    chart_id: UUID,
    item_name: str,
    interpreted_text: Optional[str] = None,
    review_comment: Optional[str] = None,
    reviewed_by: Optional[str] = None
) -> Tuple[Optional[ExtractedData], bool]:
    """
    抽出項目のレビュー状態を更新する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        item_name: 項目名
        interpreted_text: 更新する解釈後テキスト（任意）
        review_comment: レビューコメント（任意）
        reviewed_by: レビュー実施者（任意、指定なしの場合は「システム」）
        
    Returns:
        Tuple[Optional[ExtractedData], bool]: 更新された抽出データとチャート全体のレビュー必要性
    """
    # 抽出データを取得
    extracted_data = get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        logger.error(f"抽出データが見つかりません - chart_id: {chart_id}")
        return None, False
    
    # データ構造を確認（カスタマイズ抽出かどうか）
    is_custom_extraction = "review_items" in extracted_data.data and isinstance(extracted_data.data["review_items"], list)
    logger.debug(f"データ構造: {'カスタマイズ抽出' if is_custom_extraction else 'デフォルト抽出'}")
    
    # データ構造に基づいて処理を分岐
    if is_custom_extraction:
        # カスタマイズ抽出の場合の処理
        review_items = extracted_data.data["review_items"]
        
        # 項目名が一致するアイテムを検索
        item_index = None
        for i, item in enumerate(review_items):
            if isinstance(item, dict) and item.get("item_name") == item_name:
                item_index = i
                break
        
        if item_index is None:
            logger.error(f"項目が見つかりません - chart_id: {chart_id}, item_name: {item_name}")
            return None, False
        
        # 項目データを取得
        item_data = review_items[item_index]
        logger.debug(f"更新前の項目データ: {item_data}")
        
        # データの深いコピーを作成
        updated_data_copy = dict(extracted_data.data)
        updated_item_copy = dict(item_data)
        
        # interpreted_textが提供された場合、更新
        if interpreted_text is not None:
            logger.debug(f"解釈テキストを更新: '{updated_item_copy.get('interpreted_text')}' -> '{interpreted_text}'")
            updated_item_copy["interpreted_text"] = interpreted_text
        else:
            logger.debug(f"解釈テキストは提供されていません。現在の値: '{updated_item_copy.get('interpreted_text')}'")
        
        # review_commentが提供された場合、更新
        if review_comment is not None:
            logger.debug(f"レビューコメントを更新: '{updated_item_copy.get('review_comment')}' -> '{review_comment}'")
            updated_item_copy["review_comment"] = review_comment
        
        # レビュー情報を更新
        updated_item_copy["needs_review"] = False
        updated_item_copy["reviewed_by"] = reviewed_by or "システム"
        updated_item_copy["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        
        # review_items配列を更新
        updated_data_copy["review_items"][item_index] = updated_item_copy
        
        logger.debug(f"更新後の項目データ: {updated_item_copy}")
        
        # 全体のレビュー要否確認
        still_needs_review = any(
            isinstance(item, dict) and item.get("needs_review", False)
            for item in updated_data_copy["review_items"]
        )
    else:
        # デフォルト抽出の場合の処理
        if item_name not in extracted_data.data:
            logger.error(f"抽出データまたは項目が見つかりません - chart_id: {chart_id}, item_name: {item_name}")
            return None, False
        
        # データを更新
        item_data = extracted_data.data[item_name]
        logger.debug(f"更新前の項目データ: {item_data}")
        
        # データの深いコピーを作成
        updated_data_copy = dict(extracted_data.data)
        updated_item_copy = dict(item_data)
        
        # interpreted_textが提供された場合、更新
        if interpreted_text is not None:
            logger.debug(f"解釈テキストを更新: '{updated_item_copy.get('interpreted_text')}' -> '{interpreted_text}'")
            updated_item_copy["interpreted_text"] = interpreted_text
        else:
            logger.debug(f"解釈テキストは提供されていません。現在の値: '{updated_item_copy.get('interpreted_text')}'")
        
        # review_commentが提供された場合、更新
        if review_comment is not None:
            logger.debug(f"レビューコメントを更新: '{updated_item_copy.get('review_comment')}' -> '{review_comment}'")
            updated_item_copy["review_comment"] = review_comment
        
        # レビュー情報を更新
        updated_item_copy["needs_review"] = False
        updated_item_copy["reviewed_by"] = reviewed_by or "システム"
        updated_item_copy["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        
        # 更新したデータで抽出データを更新
        updated_data_copy[item_name] = updated_item_copy
        
        logger.debug(f"更新後の項目データ: {updated_item_copy}")
        
        # 全体のレビュー要否確認
        still_needs_review = any(
            isinstance(v, dict) and v.get("needs_review", False)
            for v in updated_data_copy.values()
        )
    
    # 抽出データを更新
    extracted_data.data = updated_data_copy
    
    # SQLAlchemyに変更を通知
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(extracted_data, "data")
    
    # データベースに保存
    db.flush()
    db.commit()
    db.refresh(extracted_data)
    
    # 更新後のデータを再度確認
    if is_custom_extraction:
        # カスタマイズ抽出の場合の確認
        after_update_data = get_extracted_data_by_chart_id(db, chart_id)
        if after_update_data and "review_items" in after_update_data.data:
            review_items = after_update_data.data["review_items"]
            item_found = False
            for i, item in enumerate(review_items):
                if isinstance(item, dict) and item.get("item_name") == item_name:
                    after_item_data = item
                    item_found = True
                    logger.debug(f"データベース保存後の項目データ: {after_item_data}")
                    if after_item_data.get("interpreted_text") != interpreted_text and interpreted_text is not None:
                        logger.error(f"更新に失敗: DBに保存された解釈テキスト '{after_item_data.get('interpreted_text')}' が期待値 '{interpreted_text}' と一致しません")
                    break
            
            if not item_found:
                logger.error(f"保存後のデータで項目が見つかりません: {item_name}")
    else:
        # デフォルト抽出の場合の確認
        after_update_data = get_extracted_data_by_chart_id(db, chart_id)
        if after_update_data and item_name in after_update_data.data:
            after_item_data = after_update_data.data[item_name]
            logger.debug(f"データベース保存後の項目データ: {after_item_data}")
            if after_item_data.get("interpreted_text") != interpreted_text and interpreted_text is not None:
                logger.error(f"更新に失敗: DBに保存された解釈テキスト '{after_item_data.get('interpreted_text')}' が期待値 '{interpreted_text}' と一致しません")
    
    logger.debug(f"データベースに保存完了: {item_name}")
    
    # チャートのレビュー情報も更新
    update_chart_review_status(
        db, chart_id, still_needs_review, 
        reviewed_by=reviewed_by if not still_needs_review else None
    )
    
    return extracted_data, still_needs_review


def get_review_items(db: Session, chart_id: UUID, get_all_items: bool = False) -> List[Dict[str, Any]]:
    """
    レビューが必要な項目を取得する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        get_all_items: Trueの場合、needs_reviewフラグに関わらず全ての項目を返す
        
    Returns:
        List[Dict[str, Any]]: レビューが必要な項目または全ての項目のリスト
    """
    extracted_data = get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        return []
    
    review_items = []
    
    # review_items配列から項目を取得（承認済み項目が主に含まれる）
    review_items_from_array = []
    if "review_items" in extracted_data.data and isinstance(extracted_data.data["review_items"], list):
        logger.debug("review_items配列を検出しました")
        
        for item in extracted_data.data["review_items"]:
            if isinstance(item, dict) and (get_all_items or item.get("needs_review", False)):
                # 項目データをコピーして識別子を追加
                item_copy = dict(item)
                item_copy["id"] = extracted_data.id
                # item_nameが存在することを確認
                if "item_name" not in item_copy and "item_name" in item:
                    item_copy["item_name"] = item["item_name"]
                review_items_from_array.append(item_copy)
    
    # review_items配列にある項目名を記録（重複を避けるため）
    items_in_array = {item.get("item_name") for item in review_items_from_array if item.get("item_name")}
    logger.debug(f"review_items配列にある項目: {items_in_array}")
    
    # 従来形式から項目を取得（review_items配列にない項目を補完）
    # 従来の形式の場合、オブジェクト内の各キーを項目として処理
    logger.debug("従来のデータ形式を検出しました")

    # ベースデータおよびテンプレート情報を取得
    raw_items = extracted_data.data.get("raw_items", [])
    interpreted_items = extracted_data.data.get("interpreted_items", [])
    template_id = extracted_data.data.get("template_id")
    template_name = extracted_data.data.get("template_name")

    # キーのリストを取得（raw_itemsとinterpreted_itemsから重複なく取得）
    item_names = set()
    for item in raw_items:
        if isinstance(item, dict) and "item_name" in item:
            item_names.add(item["item_name"])
    for item in interpreted_items:
        if isinstance(item, dict) and "item_name" in item:
            item_names.add(item["item_name"])

    # raw_itemsとinterpreted_itemsの項目名をキーにしたマッピングを作成
    raw_dict = {item["item_name"]: item.get("raw_text") for item in raw_items if isinstance(item, dict) and "item_name" in item}
    interpreted_dict = {item["item_name"]: item.get("interpreted_text") for item in interpreted_items if isinstance(item, dict) and "item_name" in item}

    # 従来形式のデータからreview_items形式に変換（review_items配列にない項目のみ）
    for key, value in extracted_data.data.items():
        # テンプレート情報やraw_items, interpreted_itemsなどの特殊キーはスキップ
        if key in ["raw_items", "interpreted_items", "template_id", "template_name", "review_items"]:
            continue
        
        # review_items配列に既に存在する項目はスキップ
        if key in items_in_array:
            logger.debug(f"項目 '{key}' はreview_items配列に存在するためスキップ")
            continue
        
        # valueが辞書型の場合のみ処理
        if isinstance(value, dict):
            needs_review = value.get("needs_review", False)
            if get_all_items or needs_review:
                logger.debug(f"従来形式項目を変換: key='{key}', value={value}")
                
                # 従来形式の項目をreview_items形式に変換
                item_copy = dict(value)
                item_copy["id"] = extracted_data.id
                item_copy["item_name"] = key
                
                # 従来のデータに不足している可能性のあるフィールドを追加
                if "threshold" not in item_copy:
                    item_copy["threshold"] = 0.7
                if "review_comment" not in item_copy:
                    item_copy["review_comment"] = None
                if "reviewed_by" not in item_copy:
                    item_copy["reviewed_by"] = None
                if "reviewed_at" not in item_copy:
                    item_copy["reviewed_at"] = None
                if "error_occurred" not in item_copy:
                    item_copy["error_occurred"] = False
                
                logger.debug(f"変換後のitem_copy: {item_copy}")
                review_items.append(item_copy)

    # 従来形式で項目が見つからない場合、raw_itemsとinterpreted_itemsから項目を復元
    if not review_items and get_all_items:
        logger.debug("従来形式で項目が見つからないため、raw_itemsとinterpreted_itemsから復元を試行")
        for item_name in item_names:
            # review_items配列に既に存在する項目はスキップ
            if item_name in items_in_array:
                continue
            
            raw_text = raw_dict.get(item_name)
            interpreted_text = interpreted_dict.get(item_name)
            
            # 基本的な項目データを作成
            item_copy = {
                "id": extracted_data.id,
                "item_name": item_name,
                "raw_text": raw_text,
                "interpreted_text": interpreted_text,
                "similarity_score": 1.0,
                "confidence_score": 0.8,
                "needs_review": False,
                "review_comment": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "error_occurred": False,
                "threshold": 0.7
            }
            review_items.append(item_copy)

    # review_items配列の項目と従来形式の項目を統合
    review_items.extend(review_items_from_array)

    logger.debug(f"統合結果: review_items配列から{len(review_items_from_array)}件, 従来形式から{len(review_items) - len(review_items_from_array)}件")
    logger.debug(f"取得した項目数: {len(review_items)}, get_all_items: {get_all_items}")
    return review_items


def convert_to_standard_format(db: Session, chart_id: UUID) -> bool:
    """
    カスタマイズ抽出データ形式（review_items配列）を標準形式（項目名をキーとする辞書）に変換する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        bool: 変換が成功したかどうか
    """
    extracted_data = get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        logger.error(f"抽出データが見つかりません - chart_id: {chart_id}")
        return False
    
    # カスタマイズ抽出形式かチェック
    if "review_items" not in extracted_data.data or not isinstance(extracted_data.data["review_items"], list):
        logger.debug(f"すでに標準形式のため変換不要 - chart_id: {chart_id}")
        return True
    
    logger.info(f"データ形式を標準形式に変換します - chart_id: {chart_id}")
    
    review_items = extracted_data.data["review_items"]
    standard_format = {}
    
    # review_items配列から標準形式の辞書を作成
    for item in review_items:
        if isinstance(item, dict) and "item_name" in item:
            item_name = item["item_name"]
            # item_nameキーを除いたアイテムデータをコピー
            item_data = {k: v for k, v in item.items() if k != "item_name"}
            standard_format[item_name] = item_data
    
    # メタデータを保持
    for key, value in extracted_data.data.items():
        if key != "review_items" and not key in standard_format:
            standard_format[key] = value
    
    # 更新データを保存
    extracted_data.data = standard_format
    
    # SQLAlchemyに変更を通知
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(extracted_data, "data")
    
    # データベースに保存
    db.flush()
    db.commit()
    db.refresh(extracted_data)
    
    logger.info(f"データ形式の変換が完了しました - chart_id: {chart_id}")
    return True


def update_chart_review_status_after_item_update(db: Session, chart_id: UUID) -> Optional[Chart]:
    """
    項目更新後にカルテのレビュー状態を更新する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        Optional[Chart]: 更新されたカルテ情報またはNone
    """
    logger.debug(f"項目更新後にカルテレビュー状態を更新 - chart_id: {chart_id}")
    
    # すべての項目を取得（レビュー済み含む）
    review_items = get_review_items(db, chart_id, get_all_items=True)
    
    # レビュー要の項目がまだ残っているかチェック
    needs_review = any(item.get("needs_review", False) for item in review_items)
    
    # 全てのレビューが完了した場合のレビュー担当者（最後に更新した人）
    reviewed_by = None
    if not needs_review and review_items:
        # 最後に更新されたレビュー項目から担当者を取得
        latest_item = max(
            [item for item in review_items if item.get("reviewed_at")],
            key=lambda x: x.get("reviewed_at", ""),
            default=None
        )
        if latest_item:
            reviewed_by = latest_item.get("reviewed_by")
    
    # カルテの状態を更新
    return update_chart_review_status(
        db, chart_id, needs_review, reviewed_by=reviewed_by
    )


def get_all_items_unified(db: Session, chart_id: UUID) -> List[Dict[str, Any]]:
    """
    全項目を統一形式で取得する単一の信頼できるデータソース
    review_items配列と従来形式の両方を統合処理
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        List[Dict[str, Any]]: 統一形式の全項目リスト
    """
    extracted_data = get_extracted_data_by_chart_id(db, chart_id)
    if not extracted_data:
        return []
    
    unified_items = []
    
    # Step 1: review_items配列から項目を取得
    if "review_items" in extracted_data.data and isinstance(extracted_data.data["review_items"], list):
        logger.debug("review_items配列から項目を統合処理")
        
        for item in extracted_data.data["review_items"]:
            if isinstance(item, dict) and item.get("item_name"):
                # 統一形式に変換
                unified_item = {
                    "id": extracted_data.id,
                    "item_name": item["item_name"],
                    "raw_text": item.get("raw_text"),
                    "interpreted_text": item.get("interpreted_text"),
                    "similarity_score": item.get("similarity_score"),
                    "confidence_score": item.get("confidence_score"),
                    "needs_review": item.get("needs_review", False),
                    "review_comment": item.get("review_comment"),
                    "reviewed_by": item.get("reviewed_by"),
                    "reviewed_at": item.get("reviewed_at"),
                    "threshold": item.get("threshold", 0.7),
                    "error_occurred": item.get("error_occurred", False)
                }
                unified_items.append(unified_item)
    
    # Step 2: 従来形式から項目を取得（重複除外）
    existing_names = {item["item_name"] for item in unified_items}
    logger.debug(f"review_items配列にある項目: {existing_names}")
    
    # 従来形式の項目を処理
    for key, value in extracted_data.data.items():
        # 特殊キーはスキップ
        if key in ["raw_items", "interpreted_items", "template_id", "template_name", "review_items"]:
            continue
        
        # 既に統合済みの項目はスキップ
        if key in existing_names:
            continue
        
        # valueが辞書型の場合のみ処理
        if isinstance(value, dict):
            logger.debug(f"従来形式項目を統合: {key}")
            
            # 統一形式に変換
            unified_item = {
                "id": extracted_data.id,
                "item_name": key,
                "raw_text": value.get("raw_text"),
                "interpreted_text": value.get("interpreted_text"),
                "similarity_score": value.get("similarity_score"),
                "confidence_score": value.get("confidence_score"),
                "needs_review": value.get("needs_review", False),
                "review_comment": value.get("review_comment"),
                "reviewed_by": value.get("reviewed_by"),
                "reviewed_at": value.get("reviewed_at"),
                "threshold": value.get("threshold", 0.7),
                "error_occurred": value.get("error_occurred", False)
            }
            unified_items.append(unified_item)
    
    logger.debug(f"統一データアクセス層: 合計{len(unified_items)}件の項目を統合")
    return unified_items


def find_item_by_name(items: List[Dict[str, Any]], item_name: str) -> Optional[Dict[str, Any]]:
    """
    項目名で項目を検索する
    
    Args:
        items: 項目リスト
        item_name: 検索する項目名
        
    Returns:
        Optional[Dict[str, Any]]: 見つかった項目、存在しない場合はNone
    """
    return next((item for item in items if item.get("item_name") == item_name), None)
