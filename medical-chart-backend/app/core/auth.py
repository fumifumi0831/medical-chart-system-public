import logging
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# ロガー設定
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> bool:
    """
    APIキーが有効かどうか検証する関数
    
    Args:
        api_key: リクエストヘッダーから取得したAPIキー
        
    Returns:
        bool: 検証結果
        
    Raises:
        HTTPException: APIキーが無効または存在しない場合
    """
    # 期待されるAPIキーを取得
    expected_api_key = settings.API_KEY
    
    # 受信したAPIキーと期待されるAPIキーをログに出力
    # .strip()を追加して比較前の値も確認できるようにする
    received_key_stripped = api_key.strip() if api_key else None
    expected_key_stripped = expected_api_key.strip() if expected_api_key else None
    logger.debug(f"Received API Key Header (raw): {api_key}")
    logger.debug(f"Expected API Key (raw): {expected_api_key}")
    logger.debug(f"Received API Key Header (stripped): {received_key_stripped}")
    logger.debug(f"Expected API Key (stripped): {expected_key_stripped}")


    if not api_key: # チェック自体は元のキーで行う
        logger.error("API Key header is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )

    # 比較前にstrip()を適用
    if received_key_stripped == expected_key_stripped:
        logger.debug("API Key validation successful")
        return True
    else:
        # ！！！重要！！！ 本番環境では受信したキーをログに出力しないこと
        # ここではデバッグ目的で出力していますが、セキュリティリスクになります。
        # 問題解決後はこのログ出力は削除または難読化してください。
        logger.error(f"Invalid API Key received (stripped): {received_key_stripped}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
