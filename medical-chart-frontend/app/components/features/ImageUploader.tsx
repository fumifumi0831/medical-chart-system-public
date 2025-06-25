'use client';

import React, { useState, useCallback, useRef } from 'react';
import { uploadChart, uploadChartWithTemplate } from '@/app/lib/api';
import TemplateSettingsButton from './TemplateSettingsButton';
import TemplateSelectionModal from './TemplateSelectionModal';
import TemplateEditor from './TemplateEditor';

// 最大ファイルサイズ（10MB）
const MAX_FILE_SIZE = 10 * 1024 * 1024;
// 許可するMIMEタイプ
const ALLOWED_TYPES = ['image/jpeg', 'image/png'];

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

interface ImageUploaderProps {
  onUploadSuccess: (chartId: string) => void;
  onError: (message: string) => void;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({ onUploadSuccess, onError }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [internalError, setInternalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // テンプレート関連の状態
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [isTemplateEditorOpen, setIsTemplateEditorOpen] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [baseTemplateId, setBaseTemplateId] = useState<string | null>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);

  // ズーム/パン機能用の状態
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [startPosition, setStartPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // ファイル選択時の処理
  const handleFileChange = (selectedFile: File | null) => {
    if (!selectedFile) return;

    // ファイルタイプの検証
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      setInternalError('ファイル形式はJPEGまたはPNGのみです。');
      return;
    }

    // ファイルサイズの検証
    if (selectedFile.size > MAX_FILE_SIZE) {
      setInternalError(`ファイルサイズは10MBまでです。（現在: ${(selectedFile.size / (1024 * 1024)).toFixed(2)}MB）`);
      return;
    }

    // プレビューの生成
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    setFile(selectedFile);

    // エラーメッセージのクリア
    setInternalError(null);
    
    // ズーム・位置をリセット
    setScale(1);
    setPosition({ x: 0, y: 0 });

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  };

  // アップロード処理
  const handleUpload = async () => {
    if (!file) {
      setInternalError('ファイルを選択してください。');
      return;
    }

    setIsUploading(true);

    try {
      let response;
      
      if (selectedTemplateId) {
        // テンプレートを指定してアップロード
        response = await uploadChartWithTemplate(file, selectedTemplateId);
      } else {
        // 通常のアップロード
        response = await uploadChart(file);
      }
      
      onUploadSuccess(response.chart_id);
    } catch (error) {
      console.error('アップロードエラー:', error);
      onError('アップロード中にエラーが発生しました。もう一度お試しください。');
    } finally {
      setIsUploading(false);
    }
  };

  // ドラッグ&ドロップ関連のハンドラー
  const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  }, []);

  // ファイル選択ダイアログを開く
  const openFileSelector = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // テンプレート選択のハンドラー
  const handleTemplateSettingsClick = () => {
    setIsTemplateModalOpen(true);
  };

  const handleTemplateModalClose = () => {
    setIsTemplateModalOpen(false);
  };

  const handleTemplateSelected = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setIsTemplateModalOpen(false);
  };

  const handleCreateNewTemplate = () => {
    setIsTemplateModalOpen(false);
    setIsTemplateEditorOpen(true);
    setBaseTemplateId(null);
    setEditingTemplateId(null);
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
    // テンプレートが更新された場合は、モーダルを再表示して最新の情報を取得
    setIsTemplateModalOpen(true);
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

  // ドラッグ＆ドロップ関連のハンドラー（画像パン操作用）
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!previewUrl) return; // 画像がない場合は何もしない
    e.stopPropagation(); // イベントの伝播を止める（ファイル選択イベントを防ぐ）
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
    if (!previewUrl) return; // 画像がない場合は何もしない
    e.preventDefault();
    const delta = e.deltaY * -0.01;
    const newScale = Math.min(Math.max(scale + delta, 0.5), 3);
    setScale(newScale);
  };

  return (
    <div className="mb-2">
      <div className="flex justify-between items-center mb-2">
        <div>
          <TemplateSettingsButton onClick={handleTemplateSettingsClick} />
        </div>
        
        {/* プレビュー表示時のみズームコントロールを表示 */}
        {previewUrl && (
          <div className="flex space-x-1">
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
        )}
      </div>
      
      <div 
        ref={containerRef}
        className={`border-2 border-dashed rounded-lg p-2 text-center relative mb-2 ${
          dragActive ? 'border-primary bg-blue-50' : 'border-gray-300'
        }`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{ 
          height: previewUrl ? '75vh' : 'auto',
          cursor: previewUrl ? (isDragging ? 'grabbing' : 'grab') : 'pointer',
          overflow: 'hidden'
        }}
      >
        <input 
          type="file" 
          className="hidden" 
          accept="image/jpeg,image/png" 
          onChange={(e) => e.target.files && handleFileChange(e.target.files[0])}
          ref={fileInputRef}
        />
        
        {previewUrl ? (
          <>
            <div 
              className="w-full h-full flex items-center justify-center"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              onClick={(e) => e.stopPropagation()} // ファイル選択ダイアログが開かないようにする
            >
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
                  src={previewUrl} 
                  alt="アップロード前のプレビュー" 
                  className="max-h-full max-w-full object-contain"
                  style={{ maxHeight: 'calc(75vh - 20px)' }}
                />
              </div>
            </div>
            <div 
              className="absolute bottom-2 right-2 bg-white bg-opacity-80 rounded-full p-1 cursor-pointer z-10" 
              onClick={(e) => {
                e.stopPropagation();
                openFileSelector();
              }}
            >
              <svg className="h-6 w-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
          </>
        ) : (
          <div onClick={openFileSelector}>
            <svg 
              className="mx-auto h-12 w-12 text-gray-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
              xmlns="http://www.w3.org/2000/svg"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth="2" 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-600">
              ここに画像をドラッグ＆ドロップ または
              <span className="text-primary font-medium"> ファイルを選択</span>
            </p>
            <p className="mt-1 text-xs text-gray-500">
              JPEG/PNG, 10MBまで
            </p>
          </div>
        )}
      </div>

      {internalError && (
        <div className="text-red-600 text-sm mb-2 text-center">
          {internalError}
        </div>
      )}

      <div className="flex justify-center items-center mt-2">
        {selectedTemplateId && (
          <div className="mr-4 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            テンプレート選択済み
            <button 
              className="ml-2 text-blue-600 hover:text-blue-800"
              onClick={() => setSelectedTemplateId(null)}
            >
              ×
            </button>
          </div>
        )}
        
        <button
          className="bg-primary text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          onClick={handleUpload}
          disabled={!file || isUploading || !!internalError}
        >
          {isUploading ? '処理中...' : 'アップロード＆処理開始'}
        </button>
      </div>
      
      {/* モーダルコンポーネント */}
      <TemplateSelectionModal
        isOpen={isTemplateModalOpen}
        onClose={handleTemplateModalClose}
        onSelectTemplate={handleTemplateSelected}
        onCreateNewTemplate={handleCreateNewTemplate}
        onEditTemplate={handleEditTemplate}
      />
      
      <TemplateEditor
        isOpen={isTemplateEditorOpen}
        onClose={handleTemplateEditorClose}
        templateId={editingTemplateId || undefined}
        baseTemplateId={baseTemplateId || undefined}
      />
    </div>
  );
};

export default ImageUploader; 