'use client';

import { useState, useEffect } from 'react';
import ImageUploader from './components/features/ImageUploader';
import ResultDisplay from './components/features/ResultDisplay';
import StatusBar from './components/common/StatusBar';
import CsvDownloader from './components/features/CsvDownloader';
import ExtractedTextViewer from './components/features/ExtractedTextViewer';
import { ChartData, ChartDataV2, ExtractedDataItemV2 } from './lib/types';
import { getChartResultV2 } from './lib/api';

// アイコン用のSVGコンポーネント
const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const CancelIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default function Home() {
  const [chartId, setChartId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('idle');
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [chartDataV2, setChartDataV2] = useState<ChartDataV2 | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingStartTime, setProcessingStartTime] = useState<number | null>(null);
  const [isV2Api, setIsV2Api] = useState<boolean>(true); // デフォルトでV2 APIを使用
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  const handleUploadSuccess = (id: string) => {
    setChartId(id);
    setStatus('pending');
    setErrorMessage(null);
    setProcessingStartTime(Date.now());
  };

  const handleProcessingComplete = (data: ChartData) => {
    setChartData(data);
    setStatus('completed');
    setProcessingStartTime(null);
  };

  const handleProcessingCompleteV2 = (data: ChartDataV2) => {
    setChartDataV2(data);
    setStatus('completed');
    setProcessingStartTime(null);
    
    // テンプレートIDがレスポンスに含まれている場合は保存
    if (data.template_id) {
      setSelectedTemplateId(data.template_id);
    }
  };

  const handleError = (message: string) => {
    // 空文字列の場合はエラー状態にしない
    if (!message) {
      setErrorMessage(null);
      return;
    }
    
    setErrorMessage(message);
    setStatus('failed');
  };

  const resetState = () => {
    setChartId(null);
    setStatus('idle');
    setChartData(null);
    setChartDataV2(null);
    setErrorMessage(null);
    setProcessingStartTime(null);
    setSelectedTemplateId(null);
  };

  // 項目更新時の処理
  const handleItemUpdated = (updatedItem: ExtractedDataItemV2) => {
    if (!chartDataV2 || !chartDataV2.extracted_items) return;

    // 更新された項目を含む新しい抽出項目配列を作成
    const updatedItems = chartDataV2.extracted_items.map(item => 
      item.id === updatedItem.id && item.item_name === updatedItem.item_name
        ? updatedItem 
        : item
    );

    // まだレビューが必要な項目があるかチェック
    const stillNeedsReview = updatedItems.some(item => item.needs_review);

    // chartDataV2を更新
    setChartDataV2({
      ...chartDataV2,
      extracted_items: updatedItems,
      needs_review: stillNeedsReview,
      // レビュー完了時には全体のレビュー情報も更新
      reviewed_by: !stillNeedsReview ? updatedItem.reviewed_by : chartDataV2.reviewed_by,
      reviewed_at: !stillNeedsReview ? updatedItem.reviewed_at : chartDataV2.reviewed_at
    });
  };

  // プロセスが長時間実行されている場合にステータスをprocessingに更新
  useEffect(() => {
    if (status === 'pending' && processingStartTime) {
      const timeout = setTimeout(() => {
        // 10秒以上pendingの場合はprocessingに更新
        if (Date.now() - processingStartTime > 10000) {
          setStatus('processing');
        }
      }, 10000);
      
      return () => clearTimeout(timeout);
    }
  }, [status, processingStartTime]);

  // 処理完了後にV2 APIデータを再取得（古いAPIフォーマットの結果が先に到着した場合用）
  useEffect(() => {
    if (status === 'completed' && chartId && chartData && !chartDataV2 && isV2Api) {
      const fetchDataV2 = async () => {
        try {
          const data = await getChartResultV2(chartId);
          setChartDataV2(data);
          
          // テンプレートIDがレスポンスに含まれている場合は保存
          if (data.template_id) {
            setSelectedTemplateId(data.template_id);
          }
        } catch (error) {
          console.error('V2データ取得エラー:', error);
          // V2 API取得に失敗した場合はV1データを維持
          setIsV2Api(false);
        }
      };
      
      fetchDataV2();
    }
  }, [status, chartId, chartData, chartDataV2, isV2Api]);

  return (
    <main className="flex min-h-screen flex-col">
      <div className="main-container">
        <div className="left-pane">
          {!chartId ? (
            <ImageUploader 
              onUploadSuccess={handleUploadSuccess} 
              onError={handleError} 
            />
          ) : (
            <ResultDisplay 
              chartId={chartId} 
              chartData={chartDataV2 || chartData} 
              onProcessingComplete={isV2Api ? handleProcessingCompleteV2 : handleProcessingComplete}
              onError={handleError}
            />
          )}
        </div>
        <div className="right-pane">
          <StatusBar status={status} errorMessage={errorMessage} />
          
          {isV2Api && chartDataV2 && status === 'completed' ? (
            <ExtractedTextViewer 
              chartId={chartId!} 
              chartData={chartDataV2} 
              onItemUpdated={handleItemUpdated}
            />
          ) : chartData && chartData.extracted_data && (
            <div className="mb-4 max-h-[calc(90vh-200px)] overflow-y-auto">
              <h2 className="text-xl font-semibold mb-4">抽出結果</h2>
              {chartData.extracted_data.map((item, index) => (
                <div key={index} className="mb-3">
                  <div className="font-bold">{item.item_name}:</div>
                  <div className="pl-2">{item.item_value}</div>
                </div>
              ))}
            </div>
          )}
          
          <div className="fixed bottom-0 right-0 p-4 flex gap-3">
            {chartId && status !== 'completed' && (
              <button 
                className="flex items-center bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg shadow-md hover:shadow-lg hover:from-red-600 hover:to-red-700 transition-all duration-300 transform hover:-translate-y-1"
                onClick={resetState}
              >
                <CancelIcon />
                キャンセル
              </button>
            )}
            
            {status === 'completed' && chartId && (
              <>
                <CsvDownloader chartId={chartId} className="shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1" />
                <button 
                  className="flex items-center bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-4 py-2 rounded-lg shadow-md hover:shadow-lg hover:from-emerald-600 hover:to-teal-600 transition-all duration-300 transform hover:-translate-y-1"
                  onClick={resetState}
                >
                  <UploadIcon />
                  新規アップロード
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
