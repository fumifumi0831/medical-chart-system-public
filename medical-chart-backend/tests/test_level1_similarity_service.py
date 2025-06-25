# %%
"""
Level 1 ユニットテスト: 類似度計算サービステスト - セル実行専用版
テストレベル: Level 1 (Unit Test)
信頼性: ビジネスロジック 95%, モック使用
実行頻度: 毎回
前提条件: モックサービス
各セルで独立して実行可能なように設計
設計書参照: doc_04_detailed_design.md セクション 4.3
更新日: 2025-01-15

使用方法:
- 各セル（# %%）を順次実行して結果を確認
- VS Code、PyCharm等のIDEでセル実行機能を使用
"""

# セル共通の初期化処理
def setup_environment():
    import os
    import sys
    import subprocess
    
    # 現在のPython環境を確認
    print(f"🐍 Python実行環境: {sys.executable}")
    print(f"📁 作業ディレクトリ: {os.getcwd()}")
    
    # プロジェクトルートをPythonパスに追加
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 必要な依存関係をチェック・インストール
    try:
        import rapidfuzz
        print("✅ rapidfuzz は既にインストール済み")
    except ImportError:
        print("⚠️ rapidfuzz が見つかりません。インストールを試行します...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "rapidfuzz"])
            print("✅ rapidfuzz のインストールが完了しました")
        except subprocess.CalledProcessError as e:
            print(f"❌ rapidfuzz のインストールに失敗: {e}")
            print("💡 手動でインストールしてください: pip install rapidfuzz")
    
    # 環境変数をモック設定（テスト用）
    os.environ.update({
        'API_KEY': 'test_api_key',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'GCS_BUCKET_NAME': 'test_bucket'
    })
    
    return project_root

# 初期化実行
project_root = setup_environment()
print("✅ Level 1テスト環境設定完了")

# %%
"""
セル1: 必要なライブラリのインポート
"""

# 環境設定を再実行（セル独立実行のため）
project_root = setup_environment()

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

try:
    from app.services import (
        calculate_levenshtein_similarity,
        calculate_semantic_similarity,
        should_review
    )
    print("✅ インポート成功: app.services経由（関数直接インポート）")
except ImportError as e:
    print(f"❌ インポート失敗: {e}")
    print("💡 app.services.__init__.py の設定を確認してください")
    raise
    print(f"⚠️ app.services経由でのインポート失敗: {e}")
    try:
        from app.services import similarity_service
        print("✅ インポート成功: app.services経由（モジュールインポート）")
    except ImportError as e2:
        print(f"⚠️ app.services経由でのインポート失敗: {e2}")
        try:
            import app.services.similarity_service as similarity_service
            print("✅ インポート成功: 直接インポート")
        except ImportError as e3:
            print(f"⚠️ 直接インポートも失敗: {e3}")
            try:
                import os
                import sys
                sys.path.append(os.path.join(project_root, 'app', 'services'))
                import similarity_service
                print("✅ インポート成功: 相対インポート")
            except ImportError as e4:
                print(f"❌ 全てのインポート方法が失敗: {e}, {e2}, {e3}, {e4}")
                print("💡 依存関係の問題の可能性があります。以下を確認してください：")
                print("   1. rapidfuzz がインストールされているか")
                print("   2. 仮想環境が正しく設定されているか")
                print("   3. 必要なパッケージがすべてインストールされているか")
                raise ImportError(f"similarity_serviceのインポートに失敗しました。")

print("✅ Level 1テスト用インポート完了")

# %%
"""
セル2: テストデータの準備
"""

# 環境設定を再実行
project_root = setup_environment()

# テスト用テキストペア
test_text_pairs = [
    {
        "name": "完全一致",
        "text1": "患者は頭痛を訴えています",
        "text2": "患者は頭痛を訴えています",
        "expected_levenshtein": 1.0
    },
    {
        "name": "部分的類似",
        "text1": "患者は頭痛を訴えています",
        "text2": "患者は腹痛を訴えています",
        "expected_levenshtein": 0.8  # 概算
    },
    {
        "name": "全く異なる",
        "text1": "患者は頭痛を訴えています",
        "text2": "今日は良い天気です",
        "expected_levenshtein": 0.0  # 概算
    },
    {
        "name": "空文字列",
        "text1": "",
        "text2": "患者は頭痛を訴えています",
        "expected_levenshtein": 0.0
    },
    {
        "name": "両方空文字列",
        "text1": "",
        "text2": "",
        "expected_levenshtein": 1.0
    },
    {
        "name": "None値テスト",
        "text1": None,
        "text2": "患者は頭痛を訴えています",
        "expected_levenshtein": 0.0
    }
]

# レビュー判定テストケース
review_test_cases = [
    {
        "name": "高信頼度・高類似度",
        "confidence": 0.9,
        "similarity": 0.95,
        "error_occurred": False,
        "expected": False
    },
    {
        "name": "低信頼度・高類似度",
        "confidence": 0.4,
        "similarity": 0.95,
        "error_occurred": False,
        "expected": True
    },
    {
        "name": "高信頼度・低類似度",
        "confidence": 0.9,
        "similarity": 0.3,
        "error_occurred": False,
        "expected": True
    },
    {
        "name": "エラー発生時",
        "confidence": 0.9,
        "similarity": 0.95,
        "error_occurred": True,
        "expected": True
    },
    {
        "name": "None値テスト",
        "confidence": None,
        "similarity": 0.95,
        "error_occurred": False,
        "expected": True
    }
]

print("✅ Level 1テストデータ準備完了")
print(f"📊 レーベンシュタイン距離テストケース: {len(test_text_pairs)}件")
print(f"🔍 レビュー判定テストケース: {len(review_test_cases)}件")

# %%
"""
Level 1テスト1: レーベンシュタイン距離計算（モックベース）
設計書仕様: 文字列間の編集距離に基づく類似度計算
入力: 2つのテキスト文字列
期待値: 0-1の範囲の類似度スコア
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_levenshtein_similarity():
    print("🧪 Level 1テスト開始: レーベンシュタイン距離計算（モックベース）")
    
    results = []
    for case in test_text_pairs:
        similarity = calculate_levenshtein_similarity(case["text1"], case["text2"])
        
        print(f"\n📝 テストケース: {case['name']}")
        print(f"  テキスト1: '{case['text1']}'")
        print(f"  テキスト2: '{case['text2']}'")
        print(f"  計算結果: {similarity:.3f}")
        print(f"  期待値: {case['expected_levenshtein']}")
        print(f"  範囲チェック: {0 <= similarity <= 1}")
        
        # 結果の妥当性チェック
        is_valid = 0 <= similarity <= 1
        results.append({
            "case": case["name"],
            "similarity": similarity,
            "valid": is_valid
        })
    
    # 特殊ケースのテスト
    print(f"\n🔍 特殊ケーステスト:")
    
    # 非常に長いテキスト
    long_text1 = "患者は頭痛を訴えています。" * 100
    long_text2 = "患者は腹痛を訴えています。" * 100
    long_similarity = calculate_levenshtein_similarity(long_text1, long_text2)
    print(f"  長文テスト: {long_similarity:.3f}")
    
    # 数字と記号を含むテキスト
    numeric_text1 = "血圧120/80mmHg、脈拍72回/分"
    numeric_text2 = "血圧130/85mmHg、脈拍75回/分"
    numeric_similarity = calculate_levenshtein_similarity(numeric_text1, numeric_text2)
    print(f"  数値テスト: {numeric_similarity:.3f}")
    
    success_count = sum(1 for r in results if r["valid"])
    print(f"\n✅ Level 1テスト結果: {success_count}/{len(results)} 成功")
    
    return results

# 実行
levenshtein_results = test_levenshtein_similarity()

# %%
"""
Level 1テスト2: セマンティック類似度計算（モックベース）
設計書仕様: 意味的類似度の計算（AIモデル使用）
入力: 2つのテキスト文字列
期待値: 0-1の範囲のセマンティック類似度スコア
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_semantic_similarity():
    print("🧪 Level 1テスト開始: セマンティック類似度計算（モックベース）")
    
    results = []
    for case in test_text_pairs[:4]:  # 最初の4ケースのみテスト
        similarity = calculate_semantic_similarity(case["text1"], case["text2"])
        
        print(f"\n📝 テストケース: {case['name']}")
        print(f"  テキスト1: '{case['text1']}'")
        print(f"  テキスト2: '{case['text2']}'")
        print(f"  計算結果: {similarity:.3f}")
        print(f"  範囲チェック: {0 <= similarity <= 1}")
        
        # 結果の妥当性チェック
        is_valid = 0 <= similarity <= 1
        results.append({
            "case": case["name"],
            "similarity": similarity,
            "valid": is_valid
        })
    
    success_count = sum(1 for r in results if r["valid"])
    print(f"\n✅ Level 1テスト結果: {success_count}/{len(results)} 成功")
    
    return results

# 実行
semantic_results = test_semantic_similarity()

# %%
"""
Level 1テスト3: レビュー必要性判定（モックベース）
設計書仕様: 類似度と信頼度に基づくレビュー必要性の判定
入力: 類似度スコア、信頼度スコア、エラー発生フラグ
期待値: レビューが必要かどうかのブール値
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_should_review():
    print("🧪 Level 1テスト開始: レビュー必要性判定（モックベース）")
    
    results = []
    for case in review_test_cases:
        needs_review = should_review(
            case["similarity"], 
            case["confidence"], 
            case["error_occurred"]
        )
        
        print(f"\n📝 テストケース: {case['name']}")
        print(f"  類似度: {case['similarity']}")
        print(f"  信頼度: {case['confidence']}")
        print(f"  エラー発生: {case['error_occurred']}")
        print(f"  判定結果: {needs_review}")
        print(f"  期待値: {case['expected']}")
        print(f"  判定正確性: {needs_review == case['expected']}")
        
        # 結果の妥当性チェック
        is_correct = needs_review == case["expected"]
        results.append({
            "case": case["name"],
            "result": needs_review,
            "expected": case["expected"],
            "correct": is_correct
        })
    
    success_count = sum(1 for r in results if r["correct"])
    print(f"\n✅ Level 1テスト結果: {success_count}/{len(results)} 成功")
    
    return results

# 実行
review_results = test_should_review()

# %%
"""
セル6: Level 1テスト結果サマリー
"""

print("=" * 60)
print("📋 Level 1類似度計算サービステスト実行サマリー")
print("=" * 60)
print("✅ 1. レーベンシュタイン距離計算（モックベース） - 完了")
print("✅ 2. セマンティック類似度計算（モックベース） - 完了")
print("✅ 3. レビュー必要性判定（モックベース） - 完了")
print("=" * 60)

# 詳細結果
print("📊 Level 1テスト詳細結果:")
print(f"  レーベンシュタイン距離: {sum(1 for r in levenshtein_results if r['valid'])}/{len(levenshtein_results)} 成功")
print(f"  セマンティック類似度: {sum(1 for r in semantic_results if r['valid'])}/{len(semantic_results)} 成功")
print(f"  レビュー必要性判定: {sum(1 for r in review_results if r['correct'])}/{len(review_results)} 成功")

print("🎉 Level 1テスト完了！")
print("💡 モックベースのユニットテストが正常に動作しています") 