"""add_similarity_thresholds

Revision ID: c12d3e4f5678
Revises: bf78f09c4326
Create Date: 2025-06-23 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'c12d3e4f5678'
down_revision: Union[str, None] = 'bf78f09c4326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """テンプレート項目テーブルに類似度閾値カラムを追加"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # extraction_template_itemsテーブルの存在確認
    if 'extraction_template_items' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('extraction_template_items')}
        
        # text_similarity_threshold カラムを追加（存在しない場合のみ）
        if 'text_similarity_threshold' not in columns:
            op.add_column('extraction_template_items', 
                         sa.Column('text_similarity_threshold', sa.Float(), 
                                 server_default=sa.text('0.8'), nullable=True))
        
        # vector_similarity_threshold カラムを追加（存在しない場合のみ）
        if 'vector_similarity_threshold' not in columns:
            op.add_column('extraction_template_items', 
                         sa.Column('vector_similarity_threshold', sa.Float(), 
                                 server_default=sa.text('0.7'), nullable=True))


def downgrade() -> None:
    """マイグレーションのロールバック"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'extraction_template_items' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('extraction_template_items')}
        
        # 追加したカラムを削除
        if 'vector_similarity_threshold' in columns:
            op.drop_column('extraction_template_items', 'vector_similarity_threshold')
        
        if 'text_similarity_threshold' in columns:
            op.drop_column('extraction_template_items', 'text_similarity_threshold') 