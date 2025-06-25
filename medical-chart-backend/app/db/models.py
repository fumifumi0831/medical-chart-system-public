from sqlalchemy import Column, String, DateTime, Text, ForeignKey, BigInteger, Boolean, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from uuid import uuid4

from app.db.session import Base


class ProcessStatus(str, enum.Enum):
    """カルテ処理状態を表す列挙型"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # 一部の項目が抽出に失敗した場合


class Chart(Base):
    """カルテのメタ情報を管理するテーブル"""
    __tablename__ = "charts"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    original_filename = Column(String)
    gcs_uri = Column(String, nullable=False)
    content_type = Column(String)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(ENUM(ProcessStatus), nullable=False, default=ProcessStatus.PENDING)
    error_message = Column(Text)
    overall_confidence_score = Column(Float)
    needs_review = Column(Boolean, default=False, nullable=False)
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime(timezone=True))
    # テンプレート機能のための外部キー追加
    template_id = Column(UUID, ForeignKey("extraction_templates.id"), nullable=True)

    # リレーションシップ
    extracted_data = relationship("ExtractedData", back_populates="chart", cascade="all, delete-orphan")
    template = relationship("ExtractionTemplate", back_populates="charts")


class ExtractedData(Base):
    """抽出データを管理するテーブル（JSONB型を使用）"""
    __tablename__ = "extracted_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chart_id = Column(UUID, ForeignKey("charts.id"), nullable=False, index=True)
    extracted_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # JSONB型カラム - 抽出データの詳細を格納
    data = Column(JSONB, nullable=False)
    
    # リレーションシップ
    chart = relationship("Chart", back_populates="extracted_data")


class ExtractionTemplate(Base):
    """抽出項目テンプレートを管理するテーブル"""
    __tablename__ = "extraction_templates"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(String(10), nullable=False)  # "system" または "user"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # リレーションシップ
    items = relationship("ExtractionTemplateItem", back_populates="template", cascade="all, delete-orphan")
    charts = relationship("Chart", back_populates="template")
    
    def __repr__(self):
        return f"ExtractionTemplate(id={self.id}, name={self.name}, type={self.type})"


class ExtractionTemplateItem(Base):
    """テンプレート項目を管理するテーブル"""
    __tablename__ = "extraction_template_items"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    template_id = Column(UUID, ForeignKey("extraction_templates.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    display_order = Column(Integer, nullable=False)
    description = Column(Text)
    # 2つの類似度閾値を個別に管理
    text_similarity_threshold = Column(Float, default=0.8)  # テキスト類似度閾値
    vector_similarity_threshold = Column(Float, default=0.7)  # ベクトル類似度閾値
    # 下位互換性のため既存フィールドも維持
    confidence_threshold = Column(Float, default=0.7)  # 既存の閾値フィールド
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    template = relationship("ExtractionTemplate", back_populates="items")
    
    def __repr__(self):
        return f"ExtractionTemplateItem(id={self.id}, name={self.name}, enabled={self.enabled})"
