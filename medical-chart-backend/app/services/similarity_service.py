from rapidfuzz import distance, fuzz
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import re
import logging
from difflib import SequenceMatcher

# 閾値設定（環境変数から読み込むように後で変更可能）
SIMILARITY_THRESHOLD = 0.8  # 見た目の類似度閾値
CONFIDENCE_THRESHOLD = 0.7  # 意味的類似度閾値

# ロガー設定
logger = logging.getLogger("app.services.similarity_service")
logger.setLevel(logging.DEBUG)


def normalize_text(text: str) -> str:
    """
    テキストを正規化する
    
    Args:
        text: 正規化対象のテキスト
        
    Returns:
        str: 正規化されたテキスト
    """
    if not text:
        return ""
    
    # 空白文字の正規化
    normalized = re.sub(r'\s+', ' ', text.strip())
    
    # 全角・半角の統一（必要に応じて）
    # normalized = unicodedata.normalize('NFKC', normalized)
    
    return normalized


def calculate_levenshtein_similarity(raw_text: Optional[str], interpreted_text: Optional[str]) -> float:
    """
    生テキストと解釈後テキストの見た目の類似度をレーベンシュタイン距離で計算
    
    Args:
        raw_text: AIが抽出した生テキスト
        interpreted_text: AIが解釈・修正したテキスト
        
    Returns:
        0.0-1.0の類似度スコア（1.0が完全一致）
    """
    # どちらかがNoneまたは空文字の場合の処理
    if raw_text is None or interpreted_text is None:
        if raw_text is None and interpreted_text is None:
            return 1.0  # 両方Noneは完全一致と見なす
        return 0.0  # どちらか一方がNoneは完全不一致
    
    if not raw_text and not interpreted_text:
        return 1.0  # 両方空文字も完全一致
    if not raw_text or not interpreted_text:
        return 0.0  # どちらか一方が空文字は完全不一致
        
    # 前処理
    raw_text = raw_text.strip()
    interpreted_text = interpreted_text.strip()
    
    # レーベンシュタイン距離の計算
    max_len = max(len(raw_text), len(interpreted_text))
    if max_len == 0:
        return 1.0  # 両方空文字
        
    levenshtein_distance = distance.Levenshtein.distance(raw_text, interpreted_text)
    similarity = 1.0 - (levenshtein_distance / max_len)
    
    return similarity


def calculate_semantic_similarity(raw_text: Optional[str], interpreted_text: Optional[str]) -> float:
    """
    生テキストと解釈後テキストの意味的類似度を計算
    
    Args:
        raw_text: AIが抽出した生テキスト
        interpreted_text: AIが解釈・修正したテキスト
        
    Returns:
        0.0-1.0の類似度スコア（1.0が完全一致）
    """
    # どちらかがNoneまたは空文字の場合の処理
    if raw_text is None or interpreted_text is None:
        if raw_text is None and interpreted_text is None:
            return 1.0  # 両方Noneは完全一致と見なす
        return 0.0  # どちらか一方がNoneは完全不一致
        
    # 前処理
    raw_text = raw_text.strip()
    interpreted_text = interpreted_text.strip()
    
    if not raw_text and not interpreted_text:
        return 1.0  # 両方空文字も完全一致
    if not raw_text or not interpreted_text:
        return 0.0  # どちらか一方が空文字は完全不一致
    
    try:
        # rapidfuzz の ratio を使用して類似度を計算
        # ratio は Levenshtein 距離をベースにした類似度スコア (0-100) を返す
        # 100で割って0-1のスケールに正規化
        similarity = fuzz.ratio(raw_text, interpreted_text) / 100.0
        return similarity
    except Exception as e:
        logger.error(f"意味的類似度計算エラー: {e}")
        # エラー時はレーベンシュタイン距離で代用
        return calculate_levenshtein_similarity(raw_text, interpreted_text)


def should_review(
    similarity_score: Optional[float], 
    confidence_score: Optional[float],
    error_occurred: bool = False
) -> bool:
    """
    要確認フラグを判定する関数
    
    Args:
        similarity_score: 見た目の類似度スコア
        confidence_score: 意味的類似度スコア
        error_occurred: AI処理でエラーが発生したかどうか
        
    Returns:
        True: レビューが必要、False: レビュー不要
    """
    # エラーが発生した場合は常にレビューが必要
    if error_occurred:
        return True
    
    # どちらかのスコアがNoneまたは計算不能の場合もレビューが必要
    if similarity_score is None or confidence_score is None:
        return True
    
    # スコアに基づく判定 - 「または」条件で評価
    # 見た目の類似度が閾値未満 または 意味的類似度が閾値未満の場合は要確認
    return similarity_score < SIMILARITY_THRESHOLD or confidence_score < CONFIDENCE_THRESHOLD 


def calculate_hybrid_similarity(text1: str, text2: str) -> float:
    """
    ハイブリッド類似度を計算する（レーベンシュタイン + セマンティック）
    
    Args:
        text1: 比較対象テキスト1
        text2: 比較対象テキスト2
        
    Returns:
        float: ハイブリッド類似度スコア（0.0〜1.0）
    """
    levenshtein_score = calculate_levenshtein_similarity(text1, text2)
    semantic_score = calculate_semantic_similarity(text1, text2)
    
    # 重み付き平均（レーベンシュタイン30%、セマンティック70%）
    hybrid_score = (levenshtein_score * 0.3) + (semantic_score * 0.7)
    
    logger.debug(f"Hybrid similarity: Levenshtein={levenshtein_score:.3f}, Semantic={semantic_score:.3f}, Hybrid={hybrid_score:.3f}")
    
    return hybrid_score


class SimilarityService:
    """テキスト類似度計算を統合するサービスクラス"""
    
    def __init__(self):
        self.default_threshold = 0.7
    
    def calculate_levenshtein_similarity(self, text1: str, text2: str) -> float:
        """
        レーベンシュタイン距離ベースの類似度を計算する
        
        Args:
            text1: 比較対象テキスト1
            text2: 比較対象テキスト2
            
        Returns:
            float: 類似度スコア（0.0〜1.0）
        """
        return calculate_levenshtein_similarity(text1, text2)
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        セマンティック類似度を計算する
        
        Args:
            text1: 比較対象テキスト1
            text2: 比較対象テキスト2
            
        Returns:
            float: 類似度スコア（0.0〜1.0）
        """
        return calculate_semantic_similarity(text1, text2)
    
    def should_review_texts(self, raw_text: str, interpreted_text: str, threshold: float = None) -> bool:
        """
        レビューが必要かどうかを判定する
        
        Args:
            raw_text: 生テキスト
            interpreted_text: 解釈後テキスト
            threshold: 閾値（指定されない場合はデフォルト値を使用）
            
        Returns:
            bool: レビューが必要かどうか
        """
        if threshold is None:
            threshold = self.default_threshold
        
        levenshtein_score = self.calculate_levenshtein_similarity(raw_text, interpreted_text)
        semantic_score = self.calculate_semantic_similarity(raw_text, interpreted_text)
        
        return should_review(levenshtein_score, semantic_score)
    
    def calculate_hybrid_similarity(self, text1: str, text2: str) -> float:
        """
        ハイブリッド類似度を計算する（レーベンシュタイン + セマンティック）
        
        Args:
            text1: 比較対象テキスト1
            text2: 比較対象テキスト2
            
        Returns:
            float: ハイブリッド類似度スコア（0.0〜1.0）
        """
        return calculate_hybrid_similarity(text1, text2)


# シングルトンインスタンス
_similarity_service_instance = None


def get_similarity_service() -> SimilarityService:
    """
    SimilarityServiceのシングルトンインスタンスを取得する
    
    Returns:
        SimilarityService: SimilarityServiceインスタンス
    """
    global _similarity_service_instance
    if _similarity_service_instance is None:
        _similarity_service_instance = SimilarityService()
    return _similarity_service_instance 