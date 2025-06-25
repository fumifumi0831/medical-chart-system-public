from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
from datetime import datetime


class TemplateItemBase(BaseModel):
    """テンプレート項目の基本スキーマ"""
    name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    display_order: int = Field(..., gt=0)
    description: Optional[str] = None
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    # 新しい類似度閾値フィールド
    text_similarity_threshold: float = Field(0.8, ge=0.0, le=1.0)
    vector_similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)


class TemplateItemCreate(TemplateItemBase):
    """テンプレート項目作成用スキーマ"""
    id: Optional[UUID] = None  # 既存項目のIDを任意で指定可能に


class TemplateItemUpdate(BaseModel):
    """テンプレート項目更新用スキーマ"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None
    display_order: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    # 下位互換性のため既存フィールドも維持
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    # 新しい類似度閾値フィールド
    text_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    vector_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class TemplateItem(TemplateItemBase):
    """テンプレート項目レスポンススキーマ"""
    id: UUID
    template_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TemplateBase(BaseModel):
    """テンプレートの基本スキーマ"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    type: str = Field(..., pattern=r'^(system|user)$')
    is_active: bool = True


class TemplateCreate(TemplateBase):
    """テンプレート作成用スキーマ"""
    created_by: str = Field(..., min_length=1, max_length=50)
    items: List[TemplateItemCreate] = []


class TemplateUpdate(BaseModel):
    """テンプレート更新用スキーマ"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    items: Optional[List[TemplateItemCreate]] = None


class Template(TemplateBase):
    """テンプレートレスポンススキーマ"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str
    items: List[TemplateItem] = []

    class Config:
        orm_mode = True


class TemplateSimple(BaseModel):
    """テンプレート簡易レスポンススキーマ（項目リストなし）"""
    id: UUID
    name: str
    description: Optional[str] = None
    type: str
    created_at: datetime
    created_by: str
    is_active: bool
    item_count: int

    class Config:
        orm_mode = True


class TemplateList(BaseModel):
    """テンプレート一覧レスポンススキーマ"""
    total: int
    templates: List[TemplateSimple]


class SimilarityThresholdUpdate(BaseModel):
    """類似度閾値更新用スキーマ"""
    item_id: UUID
    text_similarity_threshold: float = Field(..., ge=0.0, le=1.0)
    vector_similarity_threshold: float = Field(..., ge=0.0, le=1.0)


class BulkSimilarityThresholdUpdate(BaseModel):
    """一括類似度閾値更新用スキーマ"""
    updates: List[SimilarityThresholdUpdate] 