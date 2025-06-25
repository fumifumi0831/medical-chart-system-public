"""
医療チャートシステム - サービスモジュール
各種サービスクラスと関数をエクスポート
"""

# 各サービスモジュールをインポート
from . import db_service
from . import chart_service
from . import similarity_service
from . import gcs_service
from . import template_service
from . import gemini_service

# similarity_serviceから関数を直接インポート（テストで使用するため）
from .similarity_service import (
    calculate_levenshtein_similarity,
    calculate_semantic_similarity,
    should_review
)

# gemini_serviceから関数を直接インポート（テストで使用するため）
from .gemini_service import (
    extract_raw_data_from_image,
    interpret_extracted_data,
    extract_and_interpret_data
)

# 便利なエイリアスを提供
__all__ = [
    'db_service',
    'chart_service', 
    'similarity_service',
    'gcs_service',
    'template_service',
    'gemini_service',
    # 直接アクセス可能な関数
    'calculate_levenshtein_similarity',
    'calculate_semantic_similarity',
    'should_review',
    'extract_raw_data_from_image',
    'interpret_extracted_data',
    'extract_and_interpret_data'
]
