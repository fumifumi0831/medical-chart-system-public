"""add_ai_agent_review_feature

Revision ID: b78d6e491a25
Revises: a96815d49633
Create Date: 2025-05-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b78d6e491a25'
down_revision: Union[str, None] = 'a96815d49633'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ProcessStatus列挙型にPARTIAL_SUCCESSを追加
    # 一時的にstatusカラムをテキスト型に変更
    op.execute('ALTER TABLE charts ALTER COLUMN status TYPE TEXT')
    
    # 既存のenumタイプを削除
    op.execute('DROP TYPE processstatus')
    
    # 新しいenumタイプを作成（PARTIAL_SUCCESS追加）
    op.execute("CREATE TYPE processstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL_SUCCESS')")
    
    # statusカラムを新しいenumタイプに戻す
    op.execute('ALTER TABLE charts ALTER COLUMN status TYPE processstatus USING status::processstatus')
    
    # 2. Chartテーブルにレビュー関連のフィールドを追加
    op.add_column('charts', sa.Column('overall_confidence_score', sa.Float(), nullable=True))
    op.add_column('charts', sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('charts', sa.Column('reviewed_by', sa.String(), nullable=True))
    op.add_column('charts', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    
    # 3. ExtractedDataテーブルを削除して新しい構造で再作成
    # インデックスを削除
    op.drop_index('ix_extracted_data_chart_id', table_name='extracted_data')
    op.drop_index('ix_extracted_data_item_name', table_name='extracted_data')
    
    # ExtractedDataテーブルを削除（既存データは移行対象外）
    op.drop_table('extracted_data')
    
    # 新しい構造でExtractedDataテーブルを作成（JSONB型使用）
    op.create_table('extracted_data',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('chart_id', postgresql.UUID(), nullable=False),
        sa.Column('overall_confidence_score', sa.Float(), nullable=True),
        sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extracted_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(['chart_id'], ['charts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 新しいインデックスを作成
    op.create_index(op.f('ix_extracted_data_chart_id'), 'extracted_data', ['chart_id'], unique=False)
    op.create_index(op.f('ix_extracted_data_needs_review'), 'extracted_data', ['needs_review'], unique=False)
    
    # JSONBデータ用のGINインデックスを作成
    op.execute('CREATE INDEX idx_extracted_data_data ON extracted_data USING GIN (data)')
    
    # 要確認項目の検索を高速化するインデックス
    op.execute("CREATE INDEX idx_extracted_data_needs_review_jsonb ON extracted_data USING GIN ((data::jsonb))")


def downgrade() -> None:
    # 1. JSONBインデックスの削除
    op.execute('DROP INDEX IF EXISTS idx_extracted_data_needs_review_jsonb')
    op.execute('DROP INDEX IF EXISTS idx_extracted_data_data')
    
    # 2. 新しいExtractedDataテーブルのインデックスを削除
    op.drop_index('ix_extracted_data_needs_review', table_name='extracted_data')
    op.drop_index('ix_extracted_data_chart_id', table_name='extracted_data')
    
    # 3. 新しいExtractedDataテーブルを削除
    op.drop_table('extracted_data')
    
    # 4. 元のExtractedDataテーブルを再作成
    op.create_table('extracted_data',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('chart_id', postgresql.UUID(), nullable=False),
        sa.Column('item_name', sa.String(), nullable=False),
        sa.Column('item_value', sa.Text(), nullable=True),
        sa.Column('extracted_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chart_id'], ['charts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. 元のインデックスを再作成
    op.create_index(op.f('ix_extracted_data_item_name'), 'extracted_data', ['item_name'], unique=False)
    op.create_index(op.f('ix_extracted_data_chart_id'), 'extracted_data', ['chart_id'], unique=False)
    
    # 6. Chartテーブルから追加したカラムを削除
    op.drop_column('charts', 'reviewed_at')
    op.drop_column('charts', 'reviewed_by')
    op.drop_column('charts', 'needs_review')
    op.drop_column('charts', 'overall_confidence_score')
    
    # 7. ProcessStatus列挙型をPARTIAL_SUCCESSなしに戻す
    op.execute('ALTER TABLE charts ALTER COLUMN status TYPE TEXT')
    op.execute('DROP TYPE processstatus')
    op.execute("CREATE TYPE processstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')")
    op.execute('ALTER TABLE charts ALTER COLUMN status TYPE processstatus USING status::processstatus') 