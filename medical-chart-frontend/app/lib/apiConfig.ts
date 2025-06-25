/**
 * API設定用のユーティリティ関数
 */

/**
 * URLが正しい形式かどうかを確認し、必要なら修正する
 */
const normalizeApiUrl = (url: string): string => {
  // URLが空の場合はデフォルト値を返す
  if (!url) return 'http://localhost:8000';
  
  // 正規化するURL
  let normalizedUrl = url;
  
  // すでにhttpまたはhttpsで始まっていない場合はhttpを付ける
  if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
    normalizedUrl = `http://${normalizedUrl}`;
  }
  
  // URLの末尾が/で終わっている場合は削除する
  if (normalizedUrl.endsWith('/')) {
    normalizedUrl = normalizedUrl.slice(0, -1);
  }
  
  return normalizedUrl;
};

// APIのベースURLを取得する関数
export const getApiBaseUrl = (): string => {
  // NEXT_PUBLIC_API_BASE_URLとNEXT_PUBLIC_API_URLの両方をサポート
  const rawUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 
                 process.env.NEXT_PUBLIC_API_URL || 
                 'http://localhost:8000';
  
  // URLを正規化
  const normalizedUrl = normalizeApiUrl(rawUrl);
  
  // 開発環境のデバッグ用にログ出力
  if (process.env.NODE_ENV !== 'production') {
    console.log('[apiConfig] 元のAPI URL:', rawUrl);
    console.log('[apiConfig] 正規化されたAPI URL:', normalizedUrl);
  }
  
  return normalizedUrl;
};

// APIキーを取得する関数
export const getApiKey = (): string => {
  return process.env.NEXT_PUBLIC_API_KEY || 'YOUR_DEFAULT_API_KEY';
}; 