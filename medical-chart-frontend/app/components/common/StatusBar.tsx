'use client';

import React from 'react';

// ステータスアイコンコンポーネント
const IdleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const PendingIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="animate-spin h-4 w-4 mr-1.5 text-blue-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CompletedIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5 text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const FailedIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5 text-red-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

interface StatusBarProps {
  status: string;
  errorMessage: string | null;
}

const StatusBar: React.FC<StatusBarProps> = ({ status, errorMessage }) => {
  const getStatusText = () => {
    switch (status) {
      case 'idle':
        return 'アイドル状態';
      case 'pending':
        return 'アップロード完了、処理待機中...';
      case 'processing':
        return '画像解析処理中...';
      case 'completed':
        return '処理完了';
      case 'failed':
        return errorMessage || '処理に失敗しました';
      default:
        return status;
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'idle':
        return <IdleIcon />;
      case 'pending':
      case 'processing':
        return <PendingIcon />;
      case 'completed':
        return <CompletedIcon />;
      case 'failed':
        return <FailedIcon />;
      default:
        return <IdleIcon />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'idle':
        return 'from-gray-100 to-gray-200 text-gray-700 border-gray-300';
      case 'pending':
      case 'processing':
        return 'from-blue-50 to-blue-100 text-blue-800 border-blue-200';
      case 'completed':
        return 'from-green-50 to-green-100 text-green-800 border-green-200';
      case 'failed':
        return 'from-red-50 to-red-100 text-red-800 border-red-200';
      default:
        return 'from-gray-100 to-gray-200 text-gray-700 border-gray-300';
    }
  };

  return (
    <div className={`rounded-lg ${status === 'completed' ? 'bg-gradient-to-r from-green-400 to-emerald-500' : status === 'failed' ? 'bg-gradient-to-r from-red-400 to-red-500' : status === 'processing' || status === 'pending' ? 'bg-gradient-to-r from-blue-400 to-indigo-500' : 'bg-gradient-to-r from-gray-300 to-gray-400'} shadow-md`}>
      <div className={`flex items-center py-2 px-3 rounded-md bg-gradient-to-r ${getStatusColor()}`}>
        {getStatusIcon()}
        <div className="font-medium text-sm flex items-center">
          <span className="mr-1">ステータス:</span> {getStatusText()}
          {(status === 'pending' || status === 'processing') && (
            <div className="flex ml-2 space-x-1">
              <span className="h-1 w-1 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></span>
              <span className="h-1 w-1 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></span>
              <span className="h-1 w-1 bg-blue-600 rounded-full animate-pulse" style={{ animationDelay: '600ms' }}></span>
            </div>
          )}
        </div>
      </div>
      {errorMessage && status === 'failed' && (
        <div className="px-3 py-1.5 text-red-700 text-xs bg-red-50 rounded-b-md border-t border-red-200">
          {errorMessage}
        </div>
      )}
    </div>
  );
};

export default StatusBar; 