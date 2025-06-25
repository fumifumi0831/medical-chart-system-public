import csv
import io
import logging
import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import verify_api_key
from app.core.config import settings
from app.db.models import ProcessStatus
from app.db.session import get_db
from app.schemas import chart as schemas
from app.services import db_service, gcs_service, chart_service, template_service
from app.tasks.process_chart import sync_run_extraction_task

# ロガー設定
logger = logging.getLogger("app.routers.charts")

router = APIRouter(
    prefix="/charts",
    tags=["charts"],
    dependencies=[Depends(verify_api_key)]
)

# 完了したチャートのステータスをキャッシュ (チャートID -> (ステータス, タイムスタンプ))
# 最大キャッシュ時間（秒）
STATUS_CACHE_TTL = 300  # 5分
status_cache: Dict[str, tuple] = {}

# 抽出結果のキャッシュ (チャートID -> (結果データ, タイムスタンプ))
result_cache: Dict[str, tuple] = {}

def get_cached_status(chart_id: str) -> Optional[str]:
    """キャッシュからステータスを取得（TTL切れの場合はNone）"""
    if chart_id not in status_cache:
        return None
    
    status, timestamp = status_cache[chart_id]
    if time.time() - timestamp > STATUS_CACHE_TTL:
        # キャッシュ期限切れ
        del status_cache[chart_id]
        return None
    
    return status

def set_cached_status(chart_id: str, status: str) -> None:
    """ステータスをキャッシュに保存"""
    # 完了済みまたは失敗のステータスのみキャッシュ
    if status.lower() in ['completed', 'failed']:
        status_cache[chart_id] = (status, time.time())
        
        # キャッシュサイズが大きくなりすぎないよう、定期的に古いエントリを削除
        if len(status_cache) > 1000:  # キャッシュサイズの上限
            current_time = time.time()
            expired_keys = [
                k for k, (_, t) in status_cache.items() 
                if current_time - t > STATUS_CACHE_TTL
            ]
            for key in expired_keys:
                del status_cache[key]

def get_cached_result(chart_id: str) -> Optional[schemas.ChartResultResponse]:
    """キャッシュから結果を取得（TTL切れの場合はNone）"""
    if chart_id not in result_cache:
        return None
    
    result, timestamp = result_cache[chart_id]
    if time.time() - timestamp > STATUS_CACHE_TTL:
        # キャッシュ期限切れ
        del result_cache[chart_id]
        return None
    
    return result

def set_cached_result(chart_id: str, result: schemas.ChartResultResponse) -> None:
    """結果をキャッシュに保存"""
    # 完了済みのチャートのみキャッシュ
    if result.status.lower() == 'completed':
        result_cache[chart_id] = (result, time.time())
        
        # キャッシュサイズが大きくなりすぎないよう管理
        if len(result_cache) > 500:  # 結果キャッシュの上限
            current_time = time.time()
            expired_keys = [
                k for k, (_, t) in result_cache.items() 
                if current_time - t > STATUS_CACHE_TTL
            ]
            for key in expired_keys:
                del result_cache[key]


@router.post("", response_model=schemas.ChartCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_chart(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db),
):
    """
    カルテ画像をアップロードし、処理を開始するエンドポイント
    """
    logger.info(f"Received chart upload request: filename={file.filename}, content_type={file.content_type}")
    
    # ファイルバリデーション
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Use JPEG or PNG."
        )
    
    # ファイルサイズチェック
    try:
        logger.debug("Reading file to check size")
        contents = await file.read()
        file_size = len(contents)
        logger.debug(f"File size: {file_size} bytes")
        
        if file_size > settings.MAX_FILE_SIZE:
            logger.warning(f"File size too large: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds limit ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)."
            )
        await file.seek(0)  # ファイルポインタをリセット
    except Exception as e:
        logger.error(f"Error checking file size: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )
    
    chart_id = uuid4()
    logger.info(f"Generated chart ID: {chart_id}")
    
    try:
        # GCSにアップロード
        logger.info(f"Uploading file to storage with chart ID: {chart_id}")
        gcs_uri = await gcs_service.upload_file_to_gcs(file, str(chart_id), file.content_type)
        logger.info(f"File uploaded successfully: {gcs_uri}")
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )
    
    try:
        # DBレコード作成
        logger.info(f"Creating DB record for chart: {chart_id}")
        chart = db_service.create_chart_record(
            db_session, chart_id, file.filename, gcs_uri, file.content_type
        )
        
        # バックグラウンドタスク追加
        logger.info(f"Adding background extraction task for chart: {chart_id}")
        background_tasks.add_task(sync_run_extraction_task, chart_id, gcs_uri, db_session)
        
        return schemas.ChartCreateResponse(
            chart_id=chart.id,
            status=chart.status.value,
            message="Chart processing started."
        )
    except Exception as e:
        logger.error(f"Error in chart processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chart processing: {str(e)}"
        )


@router.post("/upload", response_model=schemas.ChartCreateResponse)
async def upload_chart_with_template(
    background_tasks: BackgroundTasks,
    template_id: UUID,
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db),
):
    """
    テンプレートIDを指定してカルテ画像をアップロードし、処理を開始するエンドポイント
    """
    logger.info(f"Received chart upload with template request: filename={file.filename}, content_type={file.content_type}, template_id={template_id}")
    
    # ファイルバリデーション
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Use JPEG or PNG."
        )
    
    # ファイルサイズチェック
    try:
        logger.debug("Reading file to check size")
        contents = await file.read()
        file_size = len(contents)
        logger.debug(f"File size: {file_size} bytes")
        
        if file_size > settings.MAX_FILE_SIZE:
            logger.warning(f"File size too large: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds limit ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)."
            )
        await file.seek(0)  # ファイルポインタをリセット
    except Exception as e:
        logger.error(f"Error checking file size: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )
    
    # テンプレートの存在確認
    template = template_service.get_template_by_id(db_session, template_id)
    if not template:
        logger.warning(f"Template not found: {template_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        )
    
    chart_id = uuid4()
    logger.info(f"Generated chart ID: {chart_id} with template ID: {template_id}")
    
    try:
        # GCSにアップロード
        logger.info(f"Uploading file to storage with chart ID: {chart_id}")
        gcs_uri = await gcs_service.upload_file_to_gcs(file, str(chart_id), file.content_type)
        logger.info(f"File uploaded successfully: {gcs_uri}")
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )
    
    try:
        # DBレコード作成（テンプレートIDも含める）
        logger.info(f"Creating DB record for chart: {chart_id} with template ID: {template_id}")
        chart = db_service.create_chart_record(
            db_session, chart_id, file.filename, gcs_uri, file.content_type, template_id=template_id
        )
        
        # バックグラウンドタスク追加（テンプレートを使った処理）
        logger.info(f"Adding background extraction task with template for chart: {chart_id}")
        background_tasks.add_task(
            chart_service.process_chart_with_template,
            db_session, chart_id, template_id
        )
        
        return schemas.ChartCreateResponse(
            chart_id=chart.id,
            status=chart.status.value,
            message="Chart processing with template started.",
            template_id=str(template_id),
            template_name=template['name']
        )
    except Exception as e:
        logger.error(f"Error in chart processing with template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chart processing with template: {str(e)}"
        )


@router.post("/{chart_id}/process_with_template")
async def process_chart_with_template(
    chart_id: UUID,
    template_id: UUID,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db)
):
    """
    指定されたテンプレートを使用してカルテを処理するエンドポイント
    """
    logger.info(f"Processing chart {chart_id} with template {template_id}")
    
    try:
        # キャッシュをクリア
        chart_id_str = str(chart_id)
        if chart_id_str in status_cache:
            del status_cache[chart_id_str]
        if chart_id_str in result_cache:
            del result_cache[chart_id_str]
        
        # 非同期で処理を実行
        background_tasks.add_task(
            chart_service.process_chart_with_template,
            db_session, chart_id, template_id
        )
        
        return {
            "chart_id": chart_id,
            "template_id": template_id,
            "message": "Chart processing with template started."
        }
    except ValueError as e:
        logger.error(f"Value error when processing chart with template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing chart with template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chart with template: {str(e)}"
        )


@router.post("/{chart_id}/reprocess")
async def reprocess_chart(
    chart_id: UUID,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db)
):
    """
    カルテを再処理するエンドポイント（関連付けられたテンプレートを使用）
    """
    logger.info(f"Reprocessing chart {chart_id}")
    
    try:
        # チャートの存在確認
        chart = db_service.get_chart_by_id(db_session, chart_id)
        if not chart:
            raise ValueError(f"Chart not found: {chart_id}")
        
        # テンプレートの関連付け確認
        if not chart.template_id:
            raise ValueError(f"Chart has no associated template: {chart_id}")
        
        # キャッシュをクリア
        chart_id_str = str(chart_id)
        if chart_id_str in status_cache:
            del status_cache[chart_id_str]
        if chart_id_str in result_cache:
            del result_cache[chart_id_str]
        
        # 非同期で処理を実行
        background_tasks.add_task(
            chart_service.reprocess_chart,
            db_session, chart_id
        )
        
        return {
            "chart_id": chart_id,
            "template_id": chart.template_id,
            "message": "Chart reprocessing started."
        }
    except ValueError as e:
        logger.error(f"Value error when reprocessing chart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error reprocessing chart: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing chart: {str(e)}"
        )


@router.get("/{chart_id}/status", response_model=schemas.ChartStatusResponse)
async def get_chart_status(
    chart_id: UUID,
    db_session: Session = Depends(get_db)
):
    """
    カルテの処理状態を取得するエンドポイント
    """
    chart_id_str = str(chart_id)
    logger.debug(f"Checking status for chart: {chart_id}")
    
    # キャッシュからステータスを確認
    cached_status = get_cached_status(chart_id_str)
    if cached_status:
        logger.debug(f"Using cached status for chart: {chart_id} - Status: {cached_status}")
        return schemas.ChartStatusResponse(
            chart_id=chart_id,
            status=cached_status,
            error_message=None  # キャッシュからはエラーメッセージを取得しない
        )
    
    # キャッシュになければDBから取得
    chart = db_service.get_chart_by_id(db_session, chart_id)
    if not chart:
        logger.warning(f"Chart not found: {chart_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found"
        )
    
    # 完了済みステータスはキャッシュに保存
    status_value = chart.status.value
    set_cached_status(chart_id_str, status_value)
    
    logger.debug(f"Status for chart {chart_id}: {status_value}")
    return schemas.ChartStatusResponse(
        chart_id=chart_id,
        status=status_value,
        error_message=chart.error_message
    )


@router.get("/{chart_id}", response_model=schemas.ChartResultResponse)
async def get_chart_result(
    chart_id: UUID,
    db_session: Session = Depends(get_db)
):
    """
    カルテの処理結果を取得するエンドポイント
    """
    chart_id_str = str(chart_id)
    logger.debug(f"Getting result for chart: {chart_id}")
    
    # キャッシュから結果を確認
    cached_result = get_cached_result(chart_id_str)
    if cached_result:
        logger.debug(f"Using cached result for chart: {chart_id}")
        return cached_result
    
    # ステータスをキャッシュから確認
    cached_status = get_cached_status(chart_id_str)
    if cached_status and cached_status.lower() != 'completed':
        logger.debug(f"Chart not completed (from cache): {chart_id}, status: {cached_status}")
        return schemas.ChartResultResponse(
            chart_id=chart_id,
            status=cached_status,
            message=f"Processing not completed. Current status: {cached_status}"
        )
    
    # キャッシュになければDBから取得
    chart = db_service.get_chart_by_id(db_session, chart_id)
    if not chart:
        logger.warning(f"Chart not found: {chart_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chart with ID {chart_id} not found"
        )
    
    # 処理が完了している場合は抽出結果も取得
    response = schemas.ChartResultResponse(
        chart_id=chart.id,
        original_filename=chart.original_filename,
        gcs_uri=chart.gcs_uri,
        status=chart.status.value
    )
    
    # GCS URIからブラウザで表示可能なURLを生成
    if chart.gcs_uri:
        try:
            image_url = await gcs_service.get_public_url_from_gcs_uri(chart.gcs_uri)
            if image_url:
                logger.debug(f"Generated public image URL for chart: {chart_id}")
                response.image_url = image_url
            else:
                logger.warning(f"Failed to generate public image URL for chart: {chart_id}")
        except Exception as e:
            logger.error(f"Error generating public URL for chart {chart_id}: {str(e)}", exc_info=True)
    
    if chart.status == ProcessStatus.COMPLETED:
        logger.debug(f"Retrieving extracted data for completed chart: {chart_id}")
        extracted_data = db_service.get_extracted_data_by_chart_id(db_session, chart_id)
        
        if extracted_data and extracted_data.data:
            # 抽出データがある場合、extracted_itemsを構築
            items = []
            
            # データ構造が変わっているかチェック
            review_items = extracted_data.data.get("review_items", [])
            
            if review_items:
                # 古い形式: "review_items"キーに配列がある場合
                logger.debug(f"Found {len(review_items)} review items in old format for chart: {chart_id}")
                
                for i, item in enumerate(review_items):
                    items.append(
                        schemas.ExtractedItemDetail(
                            id=i + 1,  # インデックスベースのID
                            item_name=item.get("item_name", ""),
                            raw_text=item.get("raw_text"),
                            interpreted_text=item.get("interpreted_text"),
                            similarity_score=1.0,  # 仮の値
                            confidence_score=item.get("confidence_score", 0.8),
                            needs_review=item.get("needs_review", False),
                            review_comment=item.get("review_comment"),
                            reviewed_by=item.get("reviewed_by"),
                            reviewed_at=item.get("reviewed_at")
                        )
                    )
            else:
                # 新しい形式: 項目名がキーの辞書形式
                # 各項目に対して処理
                logger.debug(f"Processing data in new format with {len(extracted_data.data)} items for chart: {chart_id}")
                
                for i, (item_name, item_data) in enumerate(extracted_data.data.items()):
                    # キーが"review_items"の場合はスキップ（既に上で処理済み）
                    if item_name == "review_items":
                        continue
                        
                    # 辞書形式のデータのみ処理
                    if isinstance(item_data, dict):
                        items.append(
                            schemas.ExtractedItemDetail(
                                id=i + 1,  # インデックスベースのID
                                item_name=item_name,
                                raw_text=item_data.get("raw_text"),
                                interpreted_text=item_data.get("interpreted_text"),
                                similarity_score=item_data.get("similarity_score", 1.0),
                                confidence_score=item_data.get("confidence_score", 0.8),
                                needs_review=item_data.get("needs_review", False),
                                review_comment=item_data.get("review_comment"),
                                reviewed_by=item_data.get("reviewed_by"),
                                reviewed_at=item_data.get("reviewed_at")
                            )
                        )
            
            response.extracted_items = items
            response.extracted_timestamp = extracted_data.extracted_timestamp
            response.needs_review = chart.needs_review
            response.overall_confidence_score = chart.overall_confidence_score
            response.reviewed_by = chart.reviewed_by
            response.reviewed_at = chart.reviewed_at
            
            logger.debug(f"Returning {len(items)} extracted items for chart: {chart_id}")
        
        # 完了したチャートの結果をキャッシュ
        set_cached_result(chart_id_str, response)
    elif chart.status == ProcessStatus.FAILED:
        logger.warning(f"Chart processing failed: {chart_id}, error: {chart.error_message}")
        response.error_message = chart.error_message
        response.message = "Processing failed."
    else:
        logger.debug(f"Chart processing not completed: {chart_id}, status: {chart.status.value}")
        response.message = f"Processing not completed. Current status: {chart.status.value}"
    
    # ステータスをキャッシュに保存
    set_cached_status(chart_id_str, chart.status.value)
    
    return response


@router.get("/{chart_id}/csv")
async def get_chart_csv(
    chart_id: UUID,
    db_session: Session = Depends(get_db)
):
    """
    カルテの処理結果をCSVでダウンロードするエンドポイント
    """
    chart_id_str = str(chart_id)
    logger.info(f"Generating CSV for chart: {chart_id}")
    
    # キャッシュからステータスを確認して完了していない場合はエラー
    cached_status = get_cached_status(chart_id_str)
    if cached_status and cached_status.lower() != 'completed':
        logger.warning(f"Cannot generate CSV - chart processing not completed (from cache): {chart_id}, status: {cached_status}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processing not completed. Current status: {cached_status}"
        )
    
    chart = db_service.get_chart_by_id(db_session, chart_id)
    if not chart:
        logger.warning(f"Chart not found: {chart_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chart with ID {chart_id} not found"
        )
    
    if chart.status != ProcessStatus.COMPLETED:
        logger.warning(f"Cannot generate CSV - chart processing not completed: {chart_id}, status: {chart.status.value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processing not completed. Current status: {chart.status.value}"
        )
    
    try:
        extracted_data = db_service.get_extracted_data_by_chart_id(db_session, chart_id)
        
        # UTF-8 BOMを追加したStringIOを使用
        output = io.StringIO()
        # UTF-8 BOMを追加
        output.write('\ufeff')
        
        writer = csv.writer(output)
        writer.writerow(["項目名", "内容"])
        
        if extracted_data:
            for item_name, item_data in extracted_data.data.items():
                interpreted_text = item_data.get("interpreted_text") if isinstance(item_data, dict) else None
                writer.writerow([item_name, interpreted_text or ""])
        
        output.seek(0)
        
        # CSVをストリーミングレスポンスとして返す
        filename = f"chart_{chart_id}_extracted_data.csv"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        logger.info(f"CSV generated successfully for chart: {chart_id}")
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv; charset=utf-8",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error generating CSV for chart {chart_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating CSV: {str(e)}"
        )
