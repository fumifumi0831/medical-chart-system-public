from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import logging
from sqlalchemy.orm import Session

from app.db.models import Chart, ExtractionTemplate, ExtractionTemplateItem, ProcessStatus
from app.services import db_service, gemini_service, template_service, gcs_service, similarity_service

# ロガー設定
logger = logging.getLogger("app.services.chart_service")
logger.setLevel(logging.DEBUG)


class ChartService:
    """カルテ処理を統合するサービスクラス"""
    
    def __init__(self):
        pass
    
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
        # 実際のモデル構造に合わせてChart作成
        chart = Chart(
            original_filename=filename,
            gcs_uri=gcs_uri or f"gs://temp-bucket/{filename}",  # 一時的なURI
            content_type=content_type,
            status="PENDING",
            template_id=template_id
        )
        
        db.add(chart)
        db.commit()
        db.refresh(chart)
        
        return chart
    
    async def process_chart_with_template(self, db: Session, chart_id: UUID, template_id: UUID) -> Chart:
        """
        指定されたテンプレートを使用してカルテを処理する
        
        Args:
            db: データベースセッション
            chart_id: カルテID
            template_id: テンプレートID
            
        Returns:
            Chart: 更新されたカルテレコード
        """
        return await process_chart_with_template(db, chart_id, template_id)
    
    async def reprocess_chart(self, db: Session, chart_id: UUID) -> Chart:
        """
        カルテを再処理する（既に関連付けられたテンプレートを使用）
        
        Args:
            db: データベースセッション
            chart_id: カルテID
            
        Returns:
            Chart: 更新されたカルテレコード
        """
        return await reprocess_chart(db, chart_id)
    
    def get_chart_status(self, db: Session, chart_id: UUID) -> Optional[str]:
        """
        カルテの処理状態を取得する
        
        Args:
            db: データベースセッション
            chart_id: カルテID
            
        Returns:
            str: 処理状態（pending, processing, completed, failed）
        """
        chart = db.query(Chart).filter(Chart.id == chart_id).first()
        if chart:
            return chart.status
        return None
    
    def get_chart_details(self, db: Session, chart_id: UUID) -> Optional[Chart]:
        """
        カルテの詳細情報を取得する
        
        Args:
            db: データベースセッション
            chart_id: カルテID
            
        Returns:
            Chart: カルテの詳細情報
        """
        return db.query(Chart).filter(Chart.id == chart_id).first()


# シングルトンインスタンス
_chart_service_instance = None


def get_chart_service() -> ChartService:
    """
    ChartServiceのシングルトンインスタンスを取得する
    
    Returns:
        ChartService: ChartServiceインスタンス
    """
    global _chart_service_instance
    if _chart_service_instance is None:
        _chart_service_instance = ChartService()
    return _chart_service_instance


async def process_chart_with_template(
    db: Session, chart_id: UUID, template_id: UUID
) -> Chart:
    """
    指定されたテンプレートを使用してカルテを処理する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        template_id: テンプレートID
        
    Returns:
        Chart: 更新されたカルテレコード
    """
    # テンプレートサービスを使用してテンプレート情報を取得
    template = template_service.get_template_by_id(db, template_id)
    
    if not template:
        raise ValueError(f"Template not found: {template_id}")
    
    # テンプレート項目を取得（template_serviceが返す辞書から取得）
    template_items = template.get('items', [])
    
    if not template_items:
        raise ValueError(f"No enabled items in template: {template_id}")
    
    # 有効な項目のみをフィルタリング
    template_items = [item for item in template_items if item.get('enabled', True)]
    
    if not template_items:
        raise ValueError(f"No enabled items in template: {template_id}")
    
    # カルテレコードの更新と存在確認
    chart = db.query(Chart).filter(Chart.id == chart_id).first()
    if not chart:
        raise ValueError(f"Chart not found: {chart_id}")
    
    # 処理中に状態を更新
    chart.template_id = template_id
    chart.status = ProcessStatus.PROCESSING
    db.commit()
    db.refresh(chart)
    
    try:
        # 抽出項目名のリスト作成
        item_names = [item['name'] for item in template_items]
        logger.info(f"Processing chart {chart_id} with template {template_id}, items: {item_names}")
        
        # カルテ画像をGCSから取得
        image_data = await gcs_service.download_file_from_gcs(chart.gcs_uri)
        
        # AIによる抽出と解釈処理
        raw_items, interpreted_items = await gemini_service.extract_and_interpret_data(
            image_data=image_data,
            custom_items=item_names
        )
        
        # 信頼度閾値によるレビュー要否判定
        needs_review = False
        total_confidence = 0.0
        review_items = []
        
        for i, raw_item in enumerate(raw_items):
            item_name = raw_item["item_name"]
            
            # テンプレート項目の閾値を取得
            template_item = next((item for item in template_items if item['name'] == item_name), None)
            
            # 2つの閾値を取得（デフォルト値付き）
            text_similarity_threshold = template_item.get('text_similarity_threshold', 0.85) if template_item else 0.85
            vector_similarity_threshold = template_item.get('vector_similarity_threshold', 0.90) if template_item else 0.90
            # 下位互換性のため既存フィールドも確認
            if template_item and not template_item.get('text_similarity_threshold'):
                text_similarity_threshold = template_item.get('confidence_threshold', 0.85)
            if template_item and not template_item.get('vector_similarity_threshold'):
                vector_similarity_threshold = template_item.get('confidence_threshold', 0.90)
            
            # 生テキストと解釈後テキストから2つの類似度スコアを計算
            raw_text = raw_item["raw_text"]
            interpreted_text = interpreted_items[i]["interpreted_text"]
            
            # 類似度スコアの計算
            error_occurred = raw_text is None or interpreted_text is None
            
            # テキスト類似度（レーベンシュタイン距離ベース）
            text_similarity_score = similarity_service.calculate_levenshtein_similarity(
                raw_text, interpreted_text
            ) if not error_occurred else 0.0
            
            # ベクトル類似度（セマンティック類似度）
            vector_similarity_score = similarity_service.calculate_semantic_similarity(
                raw_text, interpreted_text
            ) if not error_occurred else 0.0
            
            # レビュー要否判定：どちらかの閾値を下回る場合はレビュー対象
            item_needs_review = (
                text_similarity_score < text_similarity_threshold or 
                vector_similarity_score < vector_similarity_threshold
            )
            
            if item_needs_review:
                needs_review = True
            
            # 全体の信頼度は2つのスコアの平均を使用
            combined_confidence = (text_similarity_score + vector_similarity_score) / 2.0
            total_confidence += combined_confidence
            
            # レビュー情報の構築
            review_items.append({
                "item_name": item_name,
                "raw_text": raw_item["raw_text"],
                "interpreted_text": interpreted_items[i]["interpreted_text"],
                "text_similarity_score": text_similarity_score,
                "vector_similarity_score": vector_similarity_score,
                "text_similarity_threshold": text_similarity_threshold,
                "vector_similarity_threshold": vector_similarity_threshold,
                # 下位互換性のため既存フィールドも維持
                "confidence_score": vector_similarity_score,
                "similarity_score": text_similarity_score,
                "threshold": vector_similarity_threshold,
                "needs_review": item_needs_review,
                "review_comment": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "error_occurred": error_occurred
            })
            
            logger.debug(f"項目 '{item_name}' - テキスト類似度: {text_similarity_score:.2f} (閾値: {text_similarity_threshold}), ベクトル類似度: {vector_similarity_score:.2f} (閾値: {vector_similarity_threshold}), 要レビュー: {item_needs_review}")
        
        # 平均信頼度スコア計算
        average_confidence = total_confidence / len(raw_items) if raw_items else 0.0
        
        # 結果をJSONBとして保存
        result_data = {
            "raw_items": raw_items,
            "interpreted_items": interpreted_items,
            "template_id": str(template_id),
            "template_name": template.get('name', 'Unknown'),
            "review_items": review_items
        }
        
        # 抽出データをデータベースに保存
        db_service.create_extracted_data_jsonb(
            db=db, 
            chart_id=chart_id, 
            data=result_data,
            overall_confidence_score=average_confidence,
            needs_review=needs_review
        )
        
        # カルテ状態を更新
        chart.status = ProcessStatus.COMPLETED
        chart.overall_confidence_score = average_confidence
        chart.needs_review = needs_review
        db.commit()
        db.refresh(chart)
        
        return chart
        
    except Exception as e:
        logger.error(f"Error processing chart with template: {str(e)}")
        # エラー状態に更新
        chart.status = ProcessStatus.FAILED
        chart.error_message = str(e)
        db.commit()
        db.refresh(chart)
        raise


async def reprocess_chart(db: Session, chart_id: UUID) -> Chart:
    """
    カルテを再処理する（既に関連付けられたテンプレートを使用）
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        Chart: 更新されたカルテレコード
    """
    chart = db.query(Chart).filter(Chart.id == chart_id).first()
    if not chart:
        raise ValueError(f"Chart not found: {chart_id}")
    
    if not chart.template_id:
        raise ValueError(f"Chart has no associated template: {chart_id}")
    
    return await process_chart_with_template(db, chart_id, chart.template_id)


def get_processed_chart_with_details(db: Session, chart_id: UUID) -> Optional[Dict[str, Any]]:
    """
    処理済みカルテの詳細情報を取得する
    
    Args:
        db: データベースセッション
        chart_id: カルテID
        
    Returns:
        Optional[Dict[str, Any]]: カルテ詳細情報
    """
    # カルテ情報の取得
    chart = db_service.get_chart_by_id(db, chart_id)
    if not chart:
        return None
    
    # 抽出データの取得
    extracted_data = db_service.get_extracted_data_by_chart_id(db, chart_id)
    
    # テンプレート情報の取得
    template = None
    if chart.template_id:
        template = template_service.get_template_by_id(db, chart.template_id)
    
    # 結果の構築
    result = {
        "chart": {
            "id": chart.id,
            "original_filename": chart.original_filename,
            "gcs_uri": chart.gcs_uri,
            "content_type": chart.content_type,
            "upload_timestamp": chart.upload_timestamp,
            "status": chart.status,
            "error_message": chart.error_message,
            "overall_confidence_score": chart.overall_confidence_score,
            "needs_review": chart.needs_review,
            "reviewed_by": chart.reviewed_by,
            "reviewed_at": chart.reviewed_at,
            "template_id": chart.template_id
        },
        "extracted_data": extracted_data.data if extracted_data else None,
        "template": template
    }
    
    return result 