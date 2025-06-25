import os
import logging
import io
from typing import BinaryIO, Optional
from datetime import datetime, timedelta

from fastapi import UploadFile
from google.cloud import storage
from google.cloud.exceptions import NotFound

from app.core.config import settings

# ロガー設定
logger = logging.getLogger("app.services.gcs_service")
logger.setLevel(logging.DEBUG)

# GCSクライアント初期化
storage_client = None
bucket = None
GCS_KEY_PATH = '/secrets/gcs_key.json'

try:
    logger.info("Initializing GCS client...")
    if os.path.exists(GCS_KEY_PATH):
        logger.info(f"Found service account key file at {GCS_KEY_PATH}, initializing client from JSON key.")
        storage_client = storage.Client.from_service_account_json(GCS_KEY_PATH)
    else:
        # キーファイルがない場合はデフォルト認証を試みる（Cloud Runのサービスアカウントなど）
        logger.info(f"Service account key file not found at {GCS_KEY_PATH}. Attempting default credentials.")
        storage_client = storage.Client()
    
    logger.info("Successfully created storage client.")
    logger.debug("Using project: %s", storage_client.project)
    
    bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
    logger.info("Successfully accessed bucket: %s", settings.GCS_BUCKET_NAME)

except Exception as e:
    logger.error("GCS client initialization failed: %s", str(e), exc_info=True)
    # 必要に応じてフォールバックやエラーハンドリング
    # bucket = None # エラー発生時は bucket を None のままにする


class GCSService:
    """Google Cloud Storage操作を統合するサービスクラス"""
    
    def __init__(self):
        self.storage_client = storage_client
        self.bucket = bucket
    
    async def upload_file(self, file: UploadFile, filename: str, content_type: Optional[str] = None) -> str:
        """
        ファイルをGCSにアップロードする
        
        Args:
            file: アップロードされたファイル
            filename: 保存するファイル名（拡張子を含む）
            content_type: コンテンツタイプ（省略時はファイルから推測）
            
        Returns:
            str: GCSのURI (gs://{bucket_name}/{object_name})
        """
        return await upload_file_to_gcs(file, filename, content_type)
    
    async def download_file(self, gcs_uri: str) -> Optional[bytes]:
        """
        ファイルをGCSからダウンロードする
        
        Args:
            gcs_uri: GCSのURI (gs://{bucket_name}/{object_name})
            
        Returns:
            Optional[bytes]: ファイルの内容、または失敗時はNone
        """
        return await download_file_from_gcs(gcs_uri)
    
    def file_exists(self, gcs_uri: str) -> bool:
        """
        ファイルがGCSに存在するかチェックする
        
        Args:
            gcs_uri: GCSのURI (gs://{bucket_name}/{object_name})
            
        Returns:
            bool: ファイルが存在するかどうか
        """
        try:
            # ローカル開発環境用のURIをチェック
            if gcs_uri.startswith("local://"):
                local_path = gcs_uri.replace("local://", "")
                return os.path.exists(local_path)
            
            # GCSのURIから情報を抽出
            if not gcs_uri.startswith("gs://"):
                return False
            
            _, path = gcs_uri.split("gs://", 1)
            bucket_name, object_name = path.split("/", 1)
            
            if not self.bucket:
                return False
            
            blob = self.bucket.blob(object_name)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def generate_signed_url(self, gcs_uri: str, expiration_minutes: int = 30) -> Optional[str]:
        """
        GCSオブジェクトの署名付きURLを生成する
        
        Args:
            gcs_uri: GCSのURI (gs://{bucket_name}/{object_name})
            expiration_minutes: URL有効期限（分）
            
        Returns:
            Optional[str]: 署名付きURL、失敗時はNone
        """
        try:
            if not gcs_uri.startswith("gs://"):
                return None
            
            _, path = gcs_uri.split("gs://", 1)
            bucket_name, object_name = path.split("/", 1)
            
            return generate_signed_url(bucket_name, object_name, expiration_minutes)
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            return None


# シングルトンインスタンス
_gcs_service_instance = None


def get_gcs_service() -> GCSService:
    """
    GCSServiceのシングルトンインスタンスを取得する
    
    Returns:
        GCSService: GCSServiceインスタンス
    """
    global _gcs_service_instance
    if _gcs_service_instance is None:
        _gcs_service_instance = GCSService()
    return _gcs_service_instance


async def upload_file_to_gcs(file: UploadFile, filename: str, content_type: Optional[str] = None) -> str:
    """
    ファイルをGCSにアップロードする
    
    Args:
        file: アップロードされたファイル
        filename: 保存するファイル名（拡張子を含む）
        content_type: コンテンツタイプ（省略時はファイルから推測）
        
    Returns:
        str: GCSのURI (gs://{bucket_name}/{object_name})
    
    Raises:
        Exception: アップロード失敗時
    """
    logger.info("Starting upload to GCS for file: %s, content_type: %s", filename, content_type)
    
    if not bucket:
        # ローカル開発環境用（実際のGCSを使用しない場合）
        # この部分は開発環境設定に応じて調整する
        logger.info("Using local storage (bucket not initialized)")
        local_storage_path = os.path.join(os.getcwd(), "local_storage")
        os.makedirs(local_storage_path, exist_ok=True)
        
        local_file_path = os.path.join(local_storage_path, filename)
        
        try:
            logger.debug("Reading file contents for local storage")
            contents = await file.read()
            logger.debug("File read complete, size: %d bytes", len(contents))
            
            with open(local_file_path, "wb") as f:
                f.write(contents)
            
            logger.info("File saved locally at: %s", local_file_path)
            return f"local://{local_file_path}"
        except Exception as e:
            logger.error("Failed to save file locally: %s", str(e), exc_info=True)
            raise
    
    # GCSにアップロード
    logger.info("Uploading to GCS bucket: %s", settings.GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    
    # コンテンツタイプを設定
    blob_content_type = content_type or file.content_type
    if blob_content_type:
        blob.content_type = blob_content_type
        logger.debug("Content type set to: %s", blob_content_type)
    
    try:
        # ファイルをアップロード
        logger.debug("Reading file contents for GCS upload")
        contents = await file.read()
        logger.debug("File read complete, size: %d bytes", len(contents))
        
        # BytesIOオブジェクトを作成して標準的なファイルインターフェースを提供
        file_obj = io.BytesIO(contents)
        
        logger.debug("Starting upload_from_file to GCS with BytesIO object")
        blob.upload_from_file(file_obj)
        logger.info("File successfully uploaded to GCS")
        
        # GCS URIを返す
        gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/{filename}"
        logger.info("Generated GCS URI: %s", gcs_uri)
        return gcs_uri
    except Exception as e:
        logger.error("Failed to upload file to GCS: %s", str(e), exc_info=True)
        raise


async def download_file_from_gcs(gcs_uri: str) -> Optional[bytes]:
    """
    ファイルをGCSからダウンロードする
    
    Args:
        gcs_uri: GCSのURI (gs://{bucket_name}/{object_name})
        
    Returns:
        Optional[bytes]: ファイルの内容、または失敗時はNone
    """
    logger.info("Starting download from GCS: %s", gcs_uri)
    
    # ローカル開発環境用のURIをチェック
    if gcs_uri.startswith("local://"):
        local_path = gcs_uri.replace("local://", "")
        logger.info("Using local file: %s", local_path)
        try:
            with open(local_path, "rb") as f:
                content = f.read()
                logger.debug("Local file read complete, size: %d bytes", len(content))
                return content
        except Exception as e:
            logger.error("Error reading local file: %s", str(e), exc_info=True)
            return None
    
    # GCSのURIから情報を抽出
    if not gcs_uri.startswith("gs://"):
        logger.error("Invalid GCS URI format: %s", gcs_uri)
        return None
    
    # gs://{bucket_name}/{object_name} 形式からバケット名とオブジェクト名を抽出
    _, path = gcs_uri.split("gs://", 1)
    bucket_name, object_name = path.split("/", 1)
    logger.debug("Extracted bucket: %s, object: %s", bucket_name, object_name)
    
    if not bucket:
        logger.error("GCS bucket not initialized")
        return None
    
    try:
        logger.debug("Getting blob from bucket")
        blob = bucket.blob(object_name)
        content = blob.download_as_bytes()
        logger.info("File successfully downloaded from GCS, size: %d bytes", len(content))
        return content
    except Exception as e:
        logger.error("Error downloading from GCS: %s", str(e), exc_info=True)
        return None


def get_cors_compatible_url(signed_url: str) -> str:
    """署名付きURLをCORS対応形式に変換"""
    # クエリパラメータを保持したまま、必要なら調整を加える
    # 基本的には変更なしで返すことが多い
    logger.debug(f"Processing signed URL for CORS compatibility: {signed_url}")
    return signed_url


def generate_signed_url(bucket_name: str, object_name: str, expiration_minutes: int = 30) -> Optional[str]:
    """
    GCSオブジェクトの署名付きURLを生成する改善版関数
    
    Args:
        bucket_name: GCSバケット名
        object_name: オブジェクト名（ファイル名）
        expiration_minutes: URL有効期限（分）
        
    Returns:
        Optional[str]: 署名付きURL、失敗時はNone
    """
    try:
        logger.info(f"Generating signed URL for {bucket_name}/{object_name}")
        
        # バケットとオブジェクトの存在確認
        client = storage_client or storage.Client()
        bucket_obj = client.bucket(bucket_name)
        
        # オブジェクトが存在するか確認
        blob = bucket_obj.blob(object_name)
        try:
            blob.reload()  # オブジェクトのメタデータを取得（存在確認）
        except NotFound:
            logger.error(f"Object {object_name} not found in bucket {bucket_name}")
            return None
        
        # 署名付きURL生成
        expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        signed_url = blob.generate_signed_url(
            expiration=expiration,
            method='GET',
            version='v4',  # 最新APIバージョンを使用
            response_disposition=None,  # ブラウザで表示するためにダウンロードさせない
            response_type=None if not blob.content_type else blob.content_type,
        )
        
        logger.info(f"Successfully generated signed URL valid until {expiration.isoformat()}")
        return signed_url
        
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {str(e)}", exc_info=True)
        return None


async def get_public_url_from_gcs_uri(gcs_uri: str) -> Optional[str]:
    """
    GCS URIから公開URLまたは署名付きURLを取得する
    
    Args:
        gcs_uri: GCSのURI (gs://{bucket_name}/{object_name})
        
    Returns:
        Optional[str]: 公開URL、または失敗時はNone
    """
    logger.info("Generating public URL from GCS URI: %s", gcs_uri)
    
    # ローカル開発環境用のURIをチェック
    if gcs_uri.startswith("local://"):
        local_path = gcs_uri.replace("local://", "")
        logger.info("Converting local file to URL: %s", local_path)
        
        # 開発環境では、FastAPIのstaticファイル機能を使用することも可能
        # ここでは簡易的な実装として、相対パスを返す
        file_name = os.path.basename(local_path)
        static_url = f"/static/{file_name}"
        logger.info("Generated static URL: %s", static_url)
        
        # 開発環境であればFastAPIのホスト情報を付加
        host = "localhost" if settings.HOST == "0.0.0.0" else settings.HOST
        base_url = f"http://{host}:{settings.PORT}"
        full_url = f"{base_url}{static_url}"
        
        # local_storageディレクトリをstaticディレクトリにシンボリックリンクまたはコピーする必要がある
        logger.info("Full static URL: %s", full_url)
        return full_url
    
    # GCSのURIから情報を抽出
    if not gcs_uri.startswith("gs://"):
        logger.error("Invalid GCS URI format: %s", gcs_uri)
        return None
    
    try:
        # gs://{bucket_name}/{object_name} 形式からバケット名とオブジェクト名を抽出
        _, path = gcs_uri.split("gs://", 1)
        bucket_name, object_name = path.split("/", 1)
        logger.debug("Extracted bucket: %s, object: %s", bucket_name, object_name)
        
        # 改良版の署名付きURL生成関数を使用
        signed_url = generate_signed_url(bucket_name, object_name)
        
        if signed_url:
            logger.info("Successfully generated signed URL")
            return get_cors_compatible_url(signed_url)
        
        # 署名付きURL生成に失敗した場合のフォールバック処理
        logger.warning("Failed to generate signed URL, attempting fallback")
        
        # 環境に関わらずフォールバックを試行
        # 注意: このフォールバックはバケットが公開設定されている場合のみ機能します
        direct_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        logger.info(f"Falling back to direct URL: {direct_url}")
        return direct_url
            
    except Exception as e:
        logger.error("Error generating public URL: %s", str(e), exc_info=True)
        return None
