from fastapi import Depends
from fastapi.security import APIKeyHeader
from app.core.auth import verify_api_key

# APIキー認証を依存性として定義
async def get_api_key(api_key: str = Depends(verify_api_key)):
    """
    APIキー認証を実施する依存性関数
    
    Args:
        api_key: verify_api_key関数から返されるAPIキー
        
    Returns:
        str: 検証済みのAPIキー
    """
    return api_key 