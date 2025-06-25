import base64
import json
import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple

import google.generativeai as genai
from google.cloud import aiplatform
import httpx
import logging
import random
import time

from app.core.config import settings

# ロガー設定
logger = logging.getLogger(__name__)


class GeminiService:
    """Gemini AI サービスを統合するクラス"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.project_id = settings.GEMINI_PROJECT_ID
        self.model_id = settings.GEMINI_MODEL_ID
        self.location = settings.GEMINI_LOCATION
    
    async def extract_raw_data(self, image_data: bytes, custom_items: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        画像から生テキストデータを抽出する
        
        Args:
            image_data: 画像バイナリデータ
            custom_items: カスタム抽出項目のリスト
            
        Returns:
            List[Dict[str, str]]: 抽出された生テキストデータ
        """
        return await extract_raw_data_from_image(image_data, custom_items)
    
    async def interpret_data(self, raw_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        抽出された生テキストデータを解釈する
        
        Args:
            raw_items: 抽出された生テキストデータ
            
        Returns:
            List[Dict[str, str]]: 解釈されたテキストデータ
        """
        return await interpret_extracted_data(raw_items)
    
    async def extract_and_interpret(self, image_data: bytes, custom_items: Optional[List[str]] = None) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        画像から医療情報を抽出し、解釈する
        
        Args:
            image_data: 画像バイナリデータ
            custom_items: カスタム抽出項目のリスト
            
        Returns:
            Tuple: (生テキストデータ, 解釈されたテキストデータ)
        """
        return await extract_and_interpret_data(image_data, custom_items)
    
    def is_available(self) -> bool:
        """
        Gemini APIが利用可能かチェックする
        
        Returns:
            bool: APIが利用可能かどうか
        """
        return bool(self.api_key or self.project_id)


# シングルトンインスタンス
_gemini_service_instance = None


def get_gemini_service() -> GeminiService:
    """
    GeminiServiceのシングルトンインスタンスを取得する
    
    Returns:
        GeminiService: GeminiServiceインスタンス
    """
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance


# 統一システムプロンプト - カルテ画像テキスト抽出用
def get_unified_prompt():
    """
    統一された日本語システムプロンプトを返す関数
    """
    return """
    この医療カルテ画像から、実際に書かれているテキストのみを抽出してください。

    重要な指示：
    - 画像に実際に存在するテキストだけを抽出する
    - 存在しない情報は決して補完や推測しない
    - 書かれていない項目や見出しは追加しない
    - 形式やフォーマットを勝手に追加しない
    - 余分な説明は一切不要

    具体的な抽出方法：
    1. 画像に見えるテキストをそのまま読み取る
    2. 表形式のデータはスペースや記号で区切って表現
    3. 改行や段落は原文のまま保持
    4. 判読不能な部分は「[判読不能]」と表記
    5. レイアウトをなるべく維持

    例えば、画像に「体温 36.5℃」としか書かれていなければ、余分な見出しや区分けせず「体温 36.5℃」とだけ出力してください。
    """

# カスタム項目用のテキスト構造化プロンプトテンプレート
def get_custom_structured_text_extract_template(items: List[str]) -> str:
    """
    カスタム項目用のテキスト構造化プロンプトテンプレートを生成する
    
    Args:
        items: 抽出する項目のリスト
        
    Returns:
        str: 生成されたプロンプトテンプレート
    """
    # 項目リストをJSON形式のテンプレートに整形
    items_json = ',\n  '.join([f'{{"item_name": "{item}", "raw_text": "（抽出されたテキスト）"}}' for item in items])
    
    return f"""
抽出されたテキストから以下の医療情報を特定し、指定された形式でJSON形式のレスポンスを返してください。
元のテキストをそのまま抽出し、解釈や修正は行わず、原文のまま抜き出してください。

抽出する項目:
{', '.join(items)}

それぞれの項目について、テキストに記載がない場合は「記載なし」と出力してください。
テキストに明示的に「なし」と書かれている場合は「なし」と出力してください。

レスポンス形式:
```json
[
  {items_json}
]
```

JSONのみを返してください。コードブロックの外側にテキストを含めないでください。
"""

# テキスト構造化プロンプト - 生テキスト抽出用
STRUCTURED_TEXT_EXTRACT_TEMPLATE = """
抽出されたテキストから以下の医療情報を特定し、指定された形式でJSON形式のレスポンスを返してください。
元のテキストをそのまま抽出し、解釈や修正は行わず、原文のまま抜き出してください。

抽出する項目:
- 主訴
- 紹介元
- 現病歴
- 既往歴
- 家族歴
- 生活歴
- 内服薬・サプリ
- 患者解釈モデル
- 身体所見

それぞれの項目について、テキストに記載がない場合は「記載なし」と出力してください。
テキストに明示的に「なし」と書かれている場合は「なし」と出力してください。

レスポンス形式:
```json
[
  {"item_name": "主訴", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "紹介元", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "現病歴", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "既往歴", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "家族歴", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "生活歴", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "内服薬・サプリ", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "患者解釈モデル", "raw_text": "（抽出されたテキスト）"},
  {"item_name": "身体所見", "raw_text": "（抽出されたテキスト）"}
]
```

JSONのみを返してください。コードブロックの外側にテキストを含めないでください。
"""

# 解釈・正規化テンプレート
INTERPRET_TEXT_TEMPLATE = """
あなたは医療記録の解釈・正規化を行う医療AIアシスタントです。以下に示す医療カルテから抽出された生テキストに対して、
医学的に適切な表現に修正・正規化し、意味を明確にしてください。
表記のゆれ、略語、誤字脱字があれば修正し、文法的に正しい文章に直してください。
ただし、医学的事実や情報の内容自体は変更しないよう注意してください。

各項目について解釈したテキストを返してください。
入力テキストが「記載なし」または「なし」の場合は、そのまま返してください。

入力:
{raw_items_json}

出力形式:
```json
[
  {{"item_name": "主訴", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "紹介元", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "現病歴", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "既往歴", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "家族歴", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "生活歴", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "内服薬・サプリ", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "患者解釈モデル", "interpreted_text": "（解釈されたテキスト）"}},
  {{"item_name": "身体所見", "interpreted_text": "（解釈されたテキスト）"}}
]
```

JSONのみを返してください。コードブロックの外側にテキストを含めないでください。
"""

# カスタム項目用の解釈・正規化テンプレート生成
def get_custom_interpret_text_template(items: List[str]) -> str:
    """
    カスタム項目用の解釈・正規化テンプレートを生成する
    
    Args:
        items: 解釈する項目のリスト
        
    Returns:
        str: 生成されたテンプレート
    """
    # 項目リストをJSON形式のテンプレートに整形
    items_json = ',\n  '.join([f'{{"item_name": "{item}", "interpreted_text": "（解釈されたテキスト）"}}' for item in items])
    
    return f"""
あなたは医療記録の解釈・正規化を行う医療AIアシスタントです。以下に示す医療カルテから抽出された生テキストに対して、
医学的に適切な表現に修正・正規化し、意味を明確にしてください。
表記のゆれ、略語、誤字脱字があれば修正し、文法的に正しい文章に直してください。
ただし、医学的事実や情報の内容自体は変更しないよう注意してください。

各項目について解釈したテキストを返してください。
入力テキストが「記載なし」または「なし」の場合は、そのまま返してください。

入力:
{{raw_items_json}}

出力形式:
```json
[
  {items_json}
]
```

JSONのみを返してください。コードブロックの外側にテキストを含めないでください。
"""


async def extract_raw_data_from_image(image_data: bytes, custom_items: Optional[List[str]] = None, max_retries=3, initial_delay=2) -> List[Dict[str, str]]:
    """
    Gemini APIを使用して画像から生テキストデータを抽出する
    
    Args:
        image_data: 画像バイナリデータ
        custom_items: カスタム抽出項目のリスト（指定された場合、デフォルト項目の代わりに使用）
        max_retries: 最大リトライ回数
        initial_delay: 初期リトライ遅延時間（秒）
        
    Returns:
        List[Dict[str, str]]: 抽出された生テキストデータ（{item_name, raw_text}の辞書のリスト）
    """
    retries = 0
    while retries <= max_retries:
        try:
            # APIキーによる認証（APIキーがある場合）
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Geminiモデル設定
                model = genai.GenerativeModel(settings.GEMINI_MODEL_ID)
                logger.info(f"Using Gemini model: {settings.GEMINI_MODEL_ID} for raw text extraction")
                
                # 統一システムプロンプト
                unified_prompt = get_unified_prompt()
                
                # 画像をbase64エンコード
                image_parts = [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(image_data).decode("utf-8")
                        }
                    }
                ]
                
                # 2段階処理：まず画像から純粋なテキストを抽出
                raw_text_response = model.generate_content([unified_prompt] + image_parts)
                
                # エラーチェック
                if not hasattr(raw_text_response, 'text') or not raw_text_response.text:
                    logger.error("Gemini APIからの応答にテキストがありません")
                    raise ValueError("No text in Gemini API response")
                
                # 抽出されたテキストを取得
                extracted_raw_text = raw_text_response.text
                logger.info(f"Extracted raw text from image (first 1000 chars): {extracted_raw_text[:1000]}...")
                logger.debug(f"Full extracted raw text: {extracted_raw_text}")
                
                # 抽出されたテキストを構造化する第二段階
                if custom_items:
                    logger.info(f"Using custom items for extraction: {custom_items}")
                    structured_prompt = get_custom_structured_text_extract_template(custom_items)
                else:
                    structured_prompt = STRUCTURED_TEXT_EXTRACT_TEMPLATE
                
                structure_response = model.generate_content([structured_prompt, extracted_raw_text])
                
                # レスポンスからJSONを抽出
                try:
                    json_text = structure_response.text
                    logger.debug(f"Raw response from Gemini API: {json_text}")
                    
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    
                    logger.info(f"Extracted JSON data from Gemini: {json_text}")
                    return json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    logger.error(f"Response text: {structure_response.text}")
                    raise ValueError(f"Failed to parse JSON from response: {e}")
                    
            # サービスアカウントとVertexAI
            elif settings.GEMINI_PROJECT_ID:
                # デフォルト認証情報を使用（Cloud Run環境ではサービスアカウントとして実行される）
                aiplatform.init(
                    project=settings.GEMINI_PROJECT_ID,
                    location=settings.GEMINI_LOCATION
                )
                
                # VertexAI経由でGemini APIを呼び出す - 将来的に実装
                logger.warning("VertexAI implementation not completed yet")
                pass
                
            else:
                # デモ用のモックレスポンス
                if custom_items:
                    return [{"item_name": item, "raw_text": f"{item}のモックデータ"} for item in custom_items]
                else:
                    mock_response = [
                        {"item_name": "主訴", "raw_text": "頭痛、吐き気（モックデータ）"},
                        {"item_name": "紹介元", "raw_text": "○○クリニック（モックデータ）"},
                        {"item_name": "現病歴", "raw_text": "昨日夕方から頭痛あり。市販薬服用するも改善せず。（モックデータ）"},
                        {"item_name": "既往歴", "raw_text": "なし（モックデータ）"},
                        {"item_name": "家族歴", "raw_text": "父：高血圧症（モックデータ）"},
                        {"item_name": "生活歴", "raw_text": "喫煙：なし、飲酒：機会飲酒（モックデータ）"},
                        {"item_name": "内服薬・サプリ", "raw_text": "ロキソニン 60mg 頭痛時、マルチビタミン（モックデータ）"},
                        {"item_name": "患者解釈モデル", "raw_text": "強い光や音で頭痛が悪化すると患者は認識している（モックデータ）"},
                        {"item_name": "身体所見", "raw_text": "体温37.2度、BP 124/78、心音純、呼吸音清、頭痛あり（モックデータ）"}
                    ]
                    return mock_response
            
            # 正常なレスポンスが得られた場合はループを抜ける
            break
            
        except Exception as e:
            retries += 1
            logger.error(f"Attempt {retries}/{max_retries} failed: {str(e)}")
            
            if retries <= max_retries:
                # 指数バックオフでリトライ
                wait_time = initial_delay * (2 ** (retries - 1)) * (0.5 + random.random())
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Max retries ({max_retries}) exceeded. Failing.")
                raise e
    
    # このコードには到達しないはず（正常なレスポンスかエラーで終了）
    raise RuntimeError("Unexpected execution flow in extract_raw_data_from_image")


async def interpret_extracted_data(raw_items: List[Dict[str, str]], max_retries=3, initial_delay=2) -> List[Dict[str, str]]:
    """
    抽出された生テキストデータを解釈して正規化する
    
    Args:
        raw_items: 抽出された生テキストデータ（{item_name, raw_text}の辞書のリスト）
        max_retries: 最大リトライ回数
        initial_delay: 初期リトライ遅延時間（秒）
        
    Returns:
        List[Dict[str, str]]: 解釈されたテキストデータ（{item_name, interpreted_text}の辞書のリスト）
    """
    retries = 0
    
    # 項目名のリストを抽出
    item_names = [item["item_name"] for item in raw_items]
    
    while retries <= max_retries:
        try:
            # APIキーによる認証
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Geminiモデル設定
                model = genai.GenerativeModel(settings.GEMINI_MODEL_ID)
                logger.info(f"Using Gemini model: {settings.GEMINI_MODEL_ID} for interpretation")
                
                # 生テキストをJSON形式の文字列に変換
                raw_items_json = json.dumps(raw_items, ensure_ascii=False)
                
                # カスタム項目リストのテンプレートを使用
                interpret_template = get_custom_interpret_text_template(item_names)
                
                # レスポンスのテンプレートを生成し、raw_items_jsonを埋め込む
                prompt = interpret_template.replace("{raw_items_json}", raw_items_json)
                
                # Gemini APIにリクエスト
                interpretation_response = model.generate_content(prompt)
                
                # レスポンスからJSONを抽出
                try:
                    json_text = interpretation_response.text
                    logger.debug(f"Raw interpretation response: {json_text}")
                    
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    
                    logger.info(f"Extracted interpretation JSON: {json_text}")
                    return json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error in interpretation: {e}")
                    logger.error(f"Interpretation response text: {interpretation_response.text}")
                    raise ValueError(f"Failed to parse JSON from interpretation response: {e}")
            
            # モックレスポンス（APIキーがない場合）
            else:
                logger.warning("Using mock interpretation response (no API key)")
                return [{"item_name": item["item_name"], "interpreted_text": f"{item['raw_text']} (解釈済み)"} for item in raw_items]
            
            # 正常なレスポンスが得られた場合はループを抜ける
            break
            
        except Exception as e:
            retries += 1
            logger.error(f"Interpretation attempt {retries}/{max_retries} failed: {str(e)}")
            
            if retries <= max_retries:
                # 指数バックオフでリトライ
                wait_time = initial_delay * (2 ** (retries - 1)) * (0.5 + random.random())
                logger.info(f"Retrying interpretation in {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Max retries ({max_retries}) exceeded for interpretation. Failing.")
                raise e
    
    # このコードには到達しないはず（正常なレスポンスかエラーで終了）
    raise RuntimeError("Unexpected execution flow in interpret_extracted_data")


async def extract_and_interpret_data(image_data: bytes, custom_items: Optional[List[str]] = None) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    画像から医療情報を抽出し、解釈する
    
    Args:
        image_data: 画像バイナリデータ
        custom_items: カスタム抽出項目のリスト（指定された場合、デフォルト項目の代わりに使用）
        
    Returns:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]: 
            - 抽出された生テキストデータ（{item_name, raw_text}の辞書のリスト）
            - 解釈されたテキストデータ（{item_name, interpreted_text}の辞書のリスト）
    """
    # 画像からテキスト抽出
    raw_items = await extract_raw_data_from_image(image_data, custom_items)
    
    # テキスト解釈
    interpreted_items = await interpret_extracted_data(raw_items)
    
    return raw_items, interpreted_items


def build_extraction_prompt(image_url: str, items: List[str]) -> str:
    """
    指定された項目を抽出するためのプロンプトを構築する
    
    Args:
        image_url: 画像URL
        items: 抽出する項目リスト
        
    Returns:
        str: 構築されたプロンプト
    """
    items_text = ", ".join(items)
    
    prompt = f"""
    以下の医療カルテ画像から、指定された項目の情報を抽出してください。
    抽出する項目: {items_text}
    
    画像URL: {image_url}
    
    各項目に対して以下の情報を含めた結果を返してください:
    - 抽出されたテキスト
    - 信頼度スコア（0.0〜1.0）
    - 画像内の位置情報（可能であれば）
    
    結果は以下のJSON形式で返してください:
    {{
        "extracted_items": [
            {{
                "item_name": "項目名",
                "extracted_text": "抽出されたテキスト",
                "confidence_score": 0.95,
                "needs_review": false
            }},
            ...
        ]
    }}
    """
    
    return prompt
