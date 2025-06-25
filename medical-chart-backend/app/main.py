"""
医療カルテ解析システムのバックエンドAPIサーバー
"""

import os
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import charts, review, templates
from app.db.database import init_db

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# 環境変数デバッグ
credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    logger.info(f"GOOGLE_APPLICATION_CREDENTIALS is set to: {credentials_path}")
    if os.path.exists(credentials_path):
        logger.info(f"Service account key file exists: {os.path.abspath(credentials_path)}")
    else:
        logger.warning(f"Service account key file NOT FOUND: {os.path.abspath(credentials_path)}")
else:
    logger.warning("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")

logger.info("Starting Medical Chart Extraction API")

# Ensure local storage directory exists
local_storage_path = Path("local_storage")
local_storage_path.mkdir(exist_ok=True)

# Create FastAPI application
app = FastAPI(
    title="Medical Chart API",
    description="API for extracting data from medical charts",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Exception handler for all exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    グローバル例外ハンドラー
    """
    logging.exception(f"Uncaught exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )

# Exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP例外ハンドラー
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# API root endpoint
@app.get("/api/v1")
async def root():
    """
    APIルートエンドポイント
    """
    return {"message": "Welcome to Medical Chart API"}

# Health check endpoint
@app.get("/api/v1/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "ok"}

# V2 API root endpoint
@app.get("/api/v2")
async def root_v2():
    """
    API V2 ルートエンドポイント
    """
    return {"message": "Welcome to Medical Chart API V2"}

# V2 Health check endpoint
@app.get("/api/v2/health")
async def health_check_v2():
    """
    V2 ヘルスチェックエンドポイント
    """
    return {"status": "ok", "version": "v2"}

# Include routers
from fastapi import APIRouter

# v1 API ルーター
v1_charts_router = APIRouter()
v1_charts_router.include_router(charts.router)
app.include_router(v1_charts_router, prefix="/api/v1")

v1_review_router = APIRouter()
v1_review_router.include_router(review.router, prefix="/charts")
app.include_router(v1_review_router, prefix="/api/v1")

v1_templates_router = APIRouter()
v1_templates_router.include_router(templates.router, prefix="/templates")
app.include_router(v1_templates_router, prefix="/api/v1")

# v2 API ルーター
v2_charts_router = APIRouter()
v2_charts_router.include_router(charts.router)
app.include_router(v2_charts_router, prefix="/api/v2")

v2_templates_router = APIRouter()
v2_templates_router.include_router(templates.router, prefix="/templates")
app.include_router(v2_templates_router, prefix="/api/v2")

# ローカルストレージディレクトリが存在する場合、staticファイルとしてマウント
if os.path.exists(local_storage_path) and os.path.isdir(local_storage_path):
    logger.info(f"Mounting local storage directory as static files: {local_storage_path}")
    app.mount("/static", StaticFiles(directory=local_storage_path), name="static")

# すべてのルーティング登録後にCORS設定を適用
# 環境変数から取得したorigins、またはデフォルト値を使用
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    アプリケーション起動時のイベントハンドラー
    """
    logger.info("Application startup event triggered")
    
    # Initialize database
    if settings.CREATE_TABLES:
        try:
            logger.info("Initializing database...")
            await init_db()
            logger.info("Database initialization complete")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # エラーをログに記録するだけで、アプリは起動させる
            # 接続エラーの場合、後でリトライすることを期待
    
    logging.info("Application startup complete")
    logging.info(f"Debug mode: {settings.DEBUG}")
    logging.info(f"CORS origins: {settings.BACKEND_CORS_ORIGINS}")

if __name__ == "__main__":
    import uvicorn
    
    # 開発サーバー起動
    logger.info("Starting development server")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
