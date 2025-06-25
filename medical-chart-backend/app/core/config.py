import os
import json
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, field_validator, computed_field, Field
from pydantic_settings import BaseSettings

# 現在の環境を取得（デフォルトは"local"に変更）
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# 環境に応じた.envファイルの名前を決定
env_files = [".env"]  # 共通設定は常に読み込む

# 環境別の設定ファイルを追加
if ENVIRONMENT and os.path.exists(f".env.{ENVIRONMENT}"):
    env_files.append(f".env.{ENVIRONMENT}")


class Settings(BaseSettings):
    API_PREFIX: str = "/api/v1"
    API_KEY: str

    # CORS設定
    BACKEND_CORS_ORIGINS: list[str] | str = Field(
        default="*", description="許可するオリジンのリスト (単一URL文字列またはカンマ区切り)"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """環境変数からCORSオリジンリストを組み立てる"""
        if isinstance(v, str) and not v.startswith("["):
            # 単純な文字列（URLまたは '*'）の場合
            if v == "*":
                 return "*" # ワイルドカードの場合はそのまま返す
            # return [i.strip() for i in v.split(",")] # カンマ区切りが必要な場合
            return [v.strip()] # 単一URL文字列の場合はリスト化
        elif isinstance(v, (list, tuple)):
            # 既にリストの場合はそのまま返す
            return v
        elif isinstance(v, str) and v.startswith("["):
            # JSON配列の文字列形式の場合
            try:
                origins = json.loads(v)
                if isinstance(origins, list):
                    return origins
            except Exception as e:
                print(f"Error parsing CORS origins: {e}")
        
        # どの条件にも合致しない場合はlocalhostのリストを返す
        return ["http://localhost:3000"]

    # Database - 接続文字列（優先的に使用）
    DB_CONNECTION_STRING: Optional[str] = None
    
    # Database - 個別パラメータ
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    DB_NAME: Optional[str] = None

    # 動的にDATABASE_URLを生成
    @computed_field
    def DATABASE_URL(self) -> str:
        if self.DB_CONNECTION_STRING:
            return self.DB_CONNECTION_STRING
        elif all([self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]):
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        else:
            raise ValueError("Database connection information is not properly configured")

    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None  # 明示的なファイルパスが必要な場合のみ使用
    GCS_BUCKET_NAME: str
    GCS_PROJECT_ID: Optional[str] = None
    USE_LOCAL_STORAGE: bool = False
    LOCAL_STORAGE_PATH: str = "./local_storage"
    
    # File settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_CONTENT_TYPES: List[str] = ["image/jpeg", "image/png"]

    # Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_PROJECT_ID: Optional[str] = None
    GEMINI_LOCATION: Optional[str] = "us-central1"
    GEMINI_MODEL_ID: str = "gemini-2.0-flash"  # Gemini 2.0 Flash モデルをデフォルトに設定
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash"  # モデル名も一致させる
    GEMINI_MAX_OUTPUT_TOKENS: int = 4096

    # FastAPI settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    RELOAD: bool = False
    ALLOW_SWAGGER_UI: bool = True
    ENVIRONMENT: str = ENVIRONMENT  # 環境変数から読み込んだ値を設定クラスにも反映
    CREATE_TABLES: bool = False  # 初回起動時など、必要に応じてテーブルを作成するかどうか

    # Performance settings
    MAX_BACKGROUND_WORKERS: int = 2
    RATE_LIMIT_PER_MINUTE: int = 60
    REQUEST_TIMEOUT_SECONDS: int = 30

    # Test settings
    TEST_DATABASE_URL: Optional[str] = None

    model_config = {
        "case_sensitive": True,
        "env_file": env_files,  # 複数ファイルを指定
        "extra": "allow"  # 追加フィールドを許可
    }


settings = Settings()