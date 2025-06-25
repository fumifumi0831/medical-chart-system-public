from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChartCreateResponse(BaseModel):
    """カルテアップロード時のレスポンス用モデル"""
    chart_id: UUID
    status: str = "pending"
    message: str


class ChartStatusResponse(BaseModel):
    """カルテ処理状態取得のレスポンス用モデル"""
    chart_id: UUID
    status: str
    error_message: Optional[str] = None


class ExtractedDataItem(BaseModel):
    """抽出データ項目モデル"""
    item_name: str
    item_value: Optional[str] = None


class ExtractedItemDetail(BaseModel):
    """抽出項目の詳細情報モデル（要確認機能）"""
    id: int
    item_name: str
    raw_text: Optional[str] = None
    interpreted_text: Optional[str] = None
    similarity_score: Optional[float] = None
    confidence_score: Optional[float] = None
    needs_review: bool = False
    review_comment: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None  # フロントエンドとの一貫性のためstring型に変更


class ChartResultResponse(BaseModel):
    """カルテ処理結果取得のレスポンス用モデル"""
    chart_id: UUID
    original_filename: Optional[str] = None
    gcs_uri: Optional[str] = None
    image_url: Optional[str] = None  # ブラウザで表示可能な画像URL
    status: str
    overall_confidence_score: Optional[float] = None
    needs_review: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None  # フロントエンドとの一貫性のためstring型に変更
    extracted_timestamp: Optional[str] = None  # フロントエンドとの一貫性のためstring型に変更
    extracted_items: Optional[List[ExtractedItemDetail]] = None
    message: Optional[str] = None
    error_message: Optional[str] = None


class ReviewItemsResponse(BaseModel):
    """要レビュー項目のレスポンス用モデル"""
    chart_id: UUID
    review_items: List[ExtractedItemDetail]


class ItemUpdateRequest(BaseModel):
    """項目更新リクエスト用モデル"""
    item_name: str
    interpreted_text: Optional[str] = None
    review_comment: Optional[str] = None
    reviewed_by: str


class ItemUpdateResponse(BaseModel):
    """項目更新レスポンス用モデル"""
    id: int
    item_name: str
    raw_text: Optional[str] = None
    interpreted_text: Optional[str] = None
    similarity_score: Optional[float] = None
    confidence_score: Optional[float] = None
    needs_review: bool = False
    review_comment: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None  # フロントエンドとの一貫性のためstring型に変更


class ExtractedDataCreate(BaseModel):
    """抽出データ作成用モデル（JSONB対応）"""
    chart_id: UUID
    data: Dict[str, Any] = Field(..., description="抽出データのJSONオブジェクト")
    overall_confidence_score: Optional[float] = None
    needs_review: bool = False


class ExtractedDataInDB(ExtractedDataCreate):
    """DB内の抽出データモデル"""
    id: int
    extracted_timestamp: datetime
    
    class Config:
        from_attributes = True


class GenericResponse(BaseModel):
    """汎用的なAPIレスポンス用モデル"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
