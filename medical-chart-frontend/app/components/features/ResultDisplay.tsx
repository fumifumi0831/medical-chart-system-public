'use client';

import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import Image from 'next/image';
import { getChartStatus, getChartResult, getChartResultV2, reExtractWithTemplate, convertToStandardFormat } from '@/app/lib/api';
import { ChartData, ChartStatusResponse, ChartDataV2 } from '@/app/lib/types';
import TemplateSettingsButton from './TemplateSettingsButton';
import TemplateSelectionModal from './TemplateSelectionModal';
import TemplateEditor from './TemplateEditor';
import { StatusBar } from '@/app/components/common';
import ExtractedTextViewer from './ExtractedTextViewer';
import CsvDownloader from './CsvDownloader';
import { getApiBaseUrl } from '@/app/lib/apiConfig';

interface ResultDisplayProps {
  chartId: string;
  chartData: ChartData | ChartDataV2 | null;
  onProcessingComplete: (data: ChartData | ChartDataV2) => void;
  onError: (message: string) => void;
}

// ズームコントロールアイコン
const ZoomInIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
  </svg>
);

const ZoomOutIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
  </svg>
);

const ResetIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ResultDisplay: React.FC<ResultDisplayProps> = ({
  chartId,
  chartData,
  onProcessingComplete,
  onError,
}) => {
  const [isPolling, setIsPolling] = useState(true);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [initialCheck, setInitialCheck] = useState(true);
  // 画像表示が失敗した場合のフォールバック用の状態
  const [useDirectImg, setUseDirectImg] = useState(false);
  // useRefを使用してインターバルIDを保存（関数間で共有するため）
  const intervalIdRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const attemptCountRef = useRef<number>(0);
  // V2 APIを試すかどうか
  const [useV2Api, setUseV2Api] = useState(true);
  
  // ズーム/パン機能用の状態
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [startPosition, setStartPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // テンプレート関連の状態
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [isTemplateEditorOpen, setIsTemplateEditorOpen] = useState(false);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [isReExtracting, setIsReExtracting] = useState(false);
  // 変換処理済みフラグを追加
  const [formatConverted, setFormatConverted] = useState(false);

  // ポーリングを停止する関数
  const stopPolling = () => {
    if (intervalIdRef.current) {
      console.log('ポーリングを確実に停止します');
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
    setIsPolling(false);
  };

  // テンプレート関連のハンドラー
  const handleTemplateButtonClick = () => {
    setIsTemplateModalOpen(true);
  };
  
  // テンプレートで再抽出
  const handleReExtractWithTemplate = async (templateId: string) => {
    setIsTemplateModalOpen(false);
    setIsPolling(true);
    
    try {
      await reExtractWithTemplate(chartId, templateId);
      // 再抽出が開始されたら、ポーリングを再開
      attemptCountRef.current = 0;
      setInitialCheck(true);
      
      // ポーリング開始
      if (!intervalIdRef.current) {
        intervalIdRef.current = setInterval(checkStatus, 5000);
      }
      
      // すぐにステータスもチェック
      checkStatus();
    } catch (error) {
      console.error('テンプレート再抽出エラー:', error);
      onError('テンプレートを使用した再抽出に失敗しました');
      setIsPolling(false);
    }
  };
  
  // テンプレート編集ハンドラー
  const handleEditTemplate = (templateId: string) => {
    setIsTemplateModalOpen(false);
    setEditingTemplateId(templateId);
    setIsTemplateEditorOpen(true);
  };
  
  const handleTemplateEditorClose = () => {
    setIsTemplateEditorOpen(false);
    setEditingTemplateId(null);
    // 編集が完了したら、テンプレート選択モーダルを再表示
    setIsTemplateModalOpen(true);
  };

  // ポーリング処理
  const checkStatus = async () => {
    // ポーリングが既に停止されている場合は処理をスキップ
    if (!isPolling) {
      console.log('ポーリングは既に停止されています');
      return;
    }

    try {
      // ステータスチェック
      const statusResponse: ChartStatusResponse = await getChartStatus(chartId);
      console.log('ステータス応答:', statusResponse);
      
      // ステータスを小文字に変換して比較
      const status = statusResponse.status.toLowerCase();
      
      switch (status) {
        case 'completed':
          console.log('処理完了を検出、ポーリングを停止します');
          // ポーリングを停止
          stopPolling();
          
          console.log('処理完了を検出、結果を取得します');
          try {
            if (useV2Api) {
              // 拡張API (V2) を使用
              try {
                const resultDataV2: ChartDataV2 = await getChartResultV2(chartId);
                console.log('V2 APIから取得した結果データ:', resultDataV2);
                onProcessingComplete(resultDataV2);
              } catch (v2Error) {
                console.error('V2 API結果取得エラー:', v2Error);
                console.log('従来のAPIにフォールバックします');
                
                // V2 APIが失敗した場合は従来のAPIにフォールバック
                const resultData: ChartData = await getChartResult(chartId);
                console.log('従来のAPIから取得した結果データ:', resultData);
                onProcessingComplete(resultData);
                
                // フラグを更新
                setUseV2Api(false);
              }
            } else {
              // 従来のAPIを使用
              const resultData: ChartData = await getChartResult(chartId);
              console.log('従来のAPIから取得した結果データ:', resultData);
              onProcessingComplete(resultData);
            }
          } catch (resultError) {
            console.error('結果取得エラー:', resultError);
            onError('抽出結果の取得中にエラーが発生しました。');
          }
          break;
          
        case 'failed':
          // 初回チェックの場合、まだバックエンドの処理が開始されていない可能性があるため、
          // すぐにエラーを表示せず、ポーリングを続行する
          if (!initialCheck) {
            stopPolling();
            onError(statusResponse.error_message || '処理に失敗しました。');
          } else {
            console.log('初回チェックでfailedステータスを検出、ポーリングを継続します');
            setInitialCheck(false);
          }
          break;
          
        case 'pending':
        case 'processing':
          // 初回チェックフラグをクリア
          if (initialCheck) {
            setInitialCheck(false);
          }
          // 引き続きポーリング
          attemptCountRef.current++;
          const MAX_ATTEMPTS = 60; // 5分間（5秒×60）
          console.log(`ポーリング継続中 (${attemptCountRef.current}/${MAX_ATTEMPTS})`);
          if (attemptCountRef.current >= MAX_ATTEMPTS) {
            stopPolling();
            onError('処理がタイムアウトしました。時間をおいて再度お試しください。');
          }
          break;
          
        default:
          // 未知のステータス - 初回チェックの場合はエラー表示を遅らせる
          console.warn(`未知のステータス: ${statusResponse.status}`);
          if (!initialCheck) {
            stopPolling();
            onError(`予期しないステータス: ${statusResponse.status}`);
          } else {
            console.log('初回チェックで未知のステータスを検出、ポーリングを継続します');
            setInitialCheck(false);
          }
      }
    } catch (error) {
      console.error('ステータスチェックエラー:', error);
      // 初回チェックの場合は直ちにエラー表示しない
      if (!initialCheck) {
        stopPolling();
        onError('ステータスの取得中にエラーが発生しました。');
      } else {
        console.log('初回ステータスチェックエラー、ポーリングを継続します');
        setInitialCheck(false);
      }
    }
  };

  // ポーリング処理の設定
  useEffect(() => {
    // コンポーネントがマウントされた時に初回チェックを実行
    if (isPolling) {
      console.log('初回ステータスチェックを実行します');
      checkStatus();
      
      // ポーリング開始（5秒間隔）- ただし既にインターバルが設定されている場合は設定しない
      if (!intervalIdRef.current) {
        console.log('ポーリングを開始します（5秒間隔）');
        intervalIdRef.current = setInterval(checkStatus, 5000);
      }
    }

    // クリーンアップ - コンポーネントがアンマウントされる時にインターバルをクリア
    return () => {
      if (intervalIdRef.current) {
        console.log('コンポーネントアンマウント時にポーリングを停止します');
        clearInterval(intervalIdRef.current);
        intervalIdRef.current = null;
      }
    };
  }, [chartId, isPolling]);

  // 画像URLの設定
  useEffect(() => {
    if (chartData) {
      // ベースURLを取得
      const API_BASE_URL = getApiBaseUrl();
      
      if (!useDirectImg && chartData.image_url) {
        // 相対パスの場合は絶対URLに変換
        if (chartData.image_url.startsWith('/')) {
          setImgSrc(`${API_BASE_URL}${chartData.image_url}`);
        } else if (chartData.image_url.startsWith('gs://')) {
          // gs://バケット名/オブジェクト名 形式を https://storage.googleapis.com/バケット名/オブジェクト名 に変換
          const gsPath = chartData.image_url.replace('gs://', '');
          const [bucketName, ...objectPathParts] = gsPath.split('/');
          const objectPath = objectPathParts.join('/');
          setImgSrc(`https://storage.googleapis.com/${bucketName}/${objectPath}`);
          console.log(`Converting gs:// URL to: https://storage.googleapis.com/${bucketName}/${objectPath}`);
        } else {
          setImgSrc(chartData.image_url);
        }
      } else if (chartData.gcs_uri) {
        if (chartData.gcs_uri.startsWith('gs://')) {
          // gs://バケット名/オブジェクト名 形式を https://storage.googleapis.com/バケット名/オブジェクト名 に変換
          const gsPath = chartData.gcs_uri.replace('gs://', '');
          const [bucketName, ...objectPathParts] = gsPath.split('/');
          const objectPath = objectPathParts.join('/');
          setImgSrc(`https://storage.googleapis.com/${bucketName}/${objectPath}`);
          console.log(`Converting gs:// URI to: https://storage.googleapis.com/${bucketName}/${objectPath}`);
        } else {
          setImgSrc(chartData.gcs_uri);
        }
      }
    }
  }, [chartData, useDirectImg]);

  // 画像読み込みエラー時のハンドラー
  const handleImageError = () => {
    console.log('画像の読み込みに失敗しました。直接GCS URIを使用します');
    setUseDirectImg(true);
  };

  // ズーム関連のハンドラー
  const handleZoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.2, 3));
  };

  const handleZoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
  };

  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  // ドラッグ＆ドロップ関連のハンドラー
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setStartPosition({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    
    setPosition({
      x: e.clientX - startPosition.x,
      y: e.clientY - startPosition.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY * -0.01;
    const newScale = Math.min(Math.max(scale + delta, 0.5), 3);
    setScale(newScale);
  };
  
  // 結果が表示されている場合にテンプレート情報を表示
  const renderTemplateInfo = () => {
    if (!chartData || isPolling) return null;
    
    // V2 APIレスポンスの場合のみテンプレート情報がある
    const v2Data = chartData as ChartDataV2;
    
    if (v2Data.template_id && v2Data.template_name) {
      return (
        <div className="bg-blue-50 text-blue-800 px-3 py-2 rounded-md text-sm mb-4">
          <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span>使用テンプレート: <strong>{v2Data.template_name}</strong></span>
          </div>
        </div>
      );
    }
    
    return null;
  };

  // カスタマイズ抽出データを標準形式に自動変換する
  useEffect(() => {
    // チャートデータがあり、処理中でなく、まだ変換していない場合のみ実行
    if (chartData && !isPolling && chartId && !formatConverted) {
      const checkAndConvertFormat = async () => {
        try {
          // 変換済みフラグを先に立てて重複実行を防止
          setFormatConverted(true);
          // APIを呼び出してデータ形式を変換
          await convertToStandardFormat(chartId);
          console.log('データ形式を標準形式に自動変換しました');
          
          // 変換後のデータを再取得
          const updatedData = await getChartResult(chartId);
          onProcessingComplete(updatedData);
        } catch (error) {
          console.error('データ形式変換エラー:', error);
          // エラーが発生しても変換済みとしてマーク
          setFormatConverted(true);
        }
      };
      
      checkAndConvertFormat();
    }
  }, [chartData, isPolling, chartId, formatConverted, onProcessingComplete]);

  // APIステータス表示
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="relative">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">抽出処理中の画像</h2>
        
        <div className="flex items-center">
          {/* テンプレート再抽出ボタン（処理中以外で表示） */}
          {!isPolling && !isReExtracting && (
            <TemplateSettingsButton onClick={handleTemplateButtonClick} />
          )}
          
          {/* 再抽出中ローディング表示 */}
          {isReExtracting && (
            <div className="flex items-center text-blue-600 mr-3">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              再抽出中...
            </div>
          )}
          
          {/* ズームコントロール */}
          <div className="flex ml-2 space-x-1">
            <button 
              onClick={handleZoomIn}
              className="flex items-center bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-2 py-1 rounded transition-colors"
            >
              <ZoomInIcon />
              拡大
            </button>
            <button 
              onClick={handleZoomOut}
              className="flex items-center bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-2 py-1 rounded transition-colors"
            >
              <ZoomOutIcon />
              縮小
            </button>
            <button 
              onClick={handleReset}
              className="flex items-center bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs px-2 py-1 rounded transition-colors"
            >
              <ResetIcon />
              リセット
            </button>
          </div>
        </div>
      </div>
      
      {/* テンプレート情報表示エリア */}
      {renderTemplateInfo()}
      
      {/* 画像表示エリア */}
      <div 
        ref={containerRef}
        className="rounded-lg overflow-hidden border border-gray-200 bg-gray-50 relative h-[70vh] flex items-center justify-center mb-6"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        {imgSrc ? (
          <div 
            style={{
              transform: `scale(${scale}) translate(${position.x / scale}px, ${position.y / scale}px)`,
              transition: isDragging ? 'none' : 'transform 0.2s',
              height: '100%',
              width: '100%',
              position: 'absolute',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <img
              src={imgSrc}
              alt="カルテ画像"
              className="max-w-full max-h-full object-contain"
              onError={handleImageError}
            />
          </div>
        ) : (
          <div className="text-gray-500 flex items-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            画像読み込み中...
          </div>
        )}
        
        {/* ポーリング中のインジケーター */}
        {isPolling && (
          <div className="absolute bottom-4 right-4 bg-white bg-opacity-90 text-primary px-3 py-2 rounded-full shadow-sm flex items-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            テキスト抽出処理中...
          </div>
        )}
      </div>
      
      {/* APIエラー表示 */}
      {error && (
        <div className="bg-red-50 p-4 rounded-md text-red-700 mb-6">
          <p className="font-semibold">エラーが発生しました</p>
          <p className="text-sm">{error}</p>
        </div>
      )}
      
      {/* テンプレート選択モーダル */}
      <TemplateSelectionModal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        onSelectTemplate={handleReExtractWithTemplate}
        onCreateNewTemplate={() => {
          // 新規テンプレート作成モードでエディタを開く
          setIsTemplateModalOpen(false);
          setEditingTemplateId(null);
          setIsTemplateEditorOpen(true);
        }}
        onEditTemplate={handleEditTemplate}
      />
      
      {/* テンプレートエディタ */}
      <TemplateEditor
        isOpen={isTemplateEditorOpen}
        onClose={handleTemplateEditorClose}
        templateId={editingTemplateId || undefined}
      />
    </div>
  );
};

export default ResultDisplay; 