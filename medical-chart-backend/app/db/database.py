"""
データベース初期化と管理を行うユーティリティモジュール
"""

import logging
import time
from typing import Optional
from sqlalchemy.exc import OperationalError

from app.db.session import engine
from app.db import models

logger = logging.getLogger("app.db.database")

async def init_db():
    """
    テーブルの初期化
    """
    logger.info("Initializing database tables")
    try:
        # データベース接続を再試行
        retry_db_connection(max_retries=10, delay=10)
        
        # テーブルが存在しない場合は作成
        # 非同期SQLAlchemyではここでcreate_allを実行できない
        # 同期版SQLAlchemyメソッドは同期コンテキストで実行する必要がある
        # async with engine.begin()は使えないので、代わりにalembicを使うべき
        # とりあえずログだけ出して終了
        logger.info("Tables should be created using alembic migrations")
        logger.info("Run: docker exec -it medical-chart-backend alembic upgrade head")
        logger.info("Database tables initialization deferred to alembic")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def retry_db_connection(max_retries: int = 10, delay: int = 10) -> bool:
    """
    データベース接続を指定回数再試行する
    
    Args:
        max_retries: 最大再試行回数
        delay: 再試行間の待機時間（秒）
    
    Returns:
        bool: 接続成功したかどうか
    """
    retries = 0
    
    while retries < max_retries:
        try:
            # 接続テスト - 同期SQLAlchemyを使用
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection established successfully")
                return True
        except OperationalError as e:
            retries += 1
            logger.warning(f"Database connection attempt {retries}/{max_retries} failed: {e}")
            
            if retries < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                # 同期処理なのでtime.sleepを使用
                import time
                time.sleep(delay)
            else:
                logger.error("Maximum retry attempts reached. Could not connect to database.")
                raise
    
    return False 