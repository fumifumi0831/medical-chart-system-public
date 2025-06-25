FROM python:3.11-slim

WORKDIR /app

# 依存関係はビルド時にインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

# 設定ファイルとアプリケーションコードを先にコピー
COPY pyproject.toml poetry.lock* ./
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 必要なディレクトリを作成
RUN mkdir -p /app/local_storage /app/credentials

# 依存関係のインストール（アプリケーションコードのコピー後に実行）
RUN poetry install --no-interaction --no-ansi --without dev

EXPOSE 8080

# Cloud Run互換の起動コマンド
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
CMD ["--port", "8080"]