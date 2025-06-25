'use client';

import React, { useState } from 'react';
import { getCSVDownloadUrl } from '@/app/lib/api';
import { getApiKey } from '@/app/lib/apiConfig';

// CSVアイコンコンポーネント
const CsvIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
  </svg>
);

interface CsvDownloaderProps {
  chartId: string;
  className?: string;
}

const CsvDownloader: React.FC<CsvDownloaderProps> = ({ chartId, className = '' }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    
    try {
      // CSV URLの取得
      const csvUrl = getCSVDownloadUrl(chartId);
      const apiKey = getApiKey();
      
      // APIキーをリクエストヘッダに含めてFetchする
      const response = await fetch(csvUrl, {
        headers: {
          'X-API-KEY': apiKey
        }
      });
      
      if (!response.ok) {
        throw new Error(`サーバーエラー: ${response.status} ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      // ダウンロードリンクを作成
      const link = document.createElement('a');
      link.href = url;
      
      // ファイル名の設定
      link.download = `chart-data-${chartId}.csv`;
      
      // クリックをシミュレート
      document.body.appendChild(link);
      link.click();
      
      // クリーンアップ
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('CSVダウンロードエラー:', error);
      alert('CSVのダウンロード中にエラーが発生しました。');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <button 
      className={`flex items-center bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-4 py-2 rounded-lg hover:from-blue-600 hover:to-indigo-600 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed ${className}`}
      onClick={handleDownload}
      disabled={isDownloading}
    >
      {isDownloading ? (
        <>
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          ダウンロード中...
        </>
      ) : (
        <>
          <CsvIcon />
          CSVダウンロード
        </>
      )}
    </button>
  );
};

export default CsvDownloader; 