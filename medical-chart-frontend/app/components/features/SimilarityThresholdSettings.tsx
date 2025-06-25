'use client';

import React, { useState, useEffect } from 'react';
import { 
  getSimilarityThresholds, 
  updateSimilarityThresholds, 
  resetSimilarityThresholds 
} from '@/app/lib/api';
import { 
  SimilarityThresholdSettings, 
  BulkSimilarityThresholdUpdate, 
  SimilarityThresholdUpdate 
} from '@/app/lib/types';

interface SimilarityThresholdSettingsProps {
  templateId: string;
  templateName: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: () => void;
}

export const SimilarityThresholdSettingsComponent: React.FC<SimilarityThresholdSettingsProps> = ({
  templateId,
  templateName,
  isOpen,
  onClose,
  onUpdate
}) => {
  const [settings, setSettings] = useState<SimilarityThresholdSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // 設定データの読み込み
  useEffect(() => {
    if (isOpen && templateId) {
      loadSettings();
    }
  }, [isOpen, templateId]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSimilarityThresholds(templateId);
      setSettings(data);
      setHasChanges(false);
    } catch (err) {
      setError('設定の読み込みに失敗しました');
      console.error('Failed to load similarity threshold settings:', err);
    } finally {
      setLoading(false);
    }
  };

  // 閾値の変更ハンドラ
  const handleThresholdChange = (
    itemId: string, 
    field: 'text_similarity_threshold' | 'vector_similarity_threshold', 
    value: number
  ) => {
    if (!settings) return;

    const updatedSettings = {
      ...settings,
      thresholds: settings.thresholds.map(threshold =>
        threshold.item_id === itemId
          ? { ...threshold, [field]: value }
          : threshold
      )
    };

    setSettings(updatedSettings);
    setHasChanges(true);
  };

  // 設定の保存
  const handleSave = async () => {
    if (!settings || !hasChanges) return;

    setSaving(true);
    setError(null);

    try {
      const updates: SimilarityThresholdUpdate[] = settings.thresholds.map(threshold => ({
        item_id: threshold.item_id,
        text_similarity_threshold: threshold.text_similarity_threshold,
        vector_similarity_threshold: threshold.vector_similarity_threshold
      }));

      const updateData: BulkSimilarityThresholdUpdate = { updates };
      
      await updateSimilarityThresholds(templateId, updateData);
      
      setHasChanges(false);
      onUpdate?.();
      
      // 成功メッセージ表示後に少し待ってから閉じる
      setTimeout(() => {
        onClose();
      }, 1000);
      
    } catch (err) {
      setError('設定の保存に失敗しました');
      console.error('Failed to save similarity threshold settings:', err);
    } finally {
      setSaving(false);
    }
  };

  // リセット処理
  const handleReset = async () => {
    if (!window.confirm('すべての類似度閾値をデフォルト値にリセットしますか？')) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await resetSimilarityThresholds(templateId);
      await loadSettings(); // 設定を再読み込み
      onUpdate?.();
    } catch (err) {
      setError('リセットに失敗しました');
      console.error('Failed to reset similarity threshold settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* ヘッダー */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              類似度閾値設定
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              テンプレート: {templateName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={saving}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* コンテンツ */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">設定を読み込んでいます...</span>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            </div>
          ) : settings ? (
            <div className="space-y-6">
              {/* 説明 */}
              <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <div className="flex">
                  <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <p className="text-sm text-blue-800">
                      各項目の類似度閾値を設定できます。値が高いほど厳密なマッチングが行われます。
                    </p>
                    <ul className="mt-2 text-xs text-blue-700 list-disc list-inside">
                      <li>テキスト類似度: 文字列の類似性を判定する閾値 (0.0-1.0)</li>
                      <li>ベクトル類似度: 意味的な類似性を判定する閾値 (0.0-1.0)</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* 閾値設定テーブル */}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        項目名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        信頼度閾値
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        テキスト類似度
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ベクトル類似度
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {settings.thresholds.map((threshold) => (
                      <tr key={threshold.item_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {threshold.item_name}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-600">
                            {threshold.confidence_threshold.toFixed(2)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={threshold.text_similarity_threshold}
                            onChange={(e) => handleThresholdChange(
                              threshold.item_id,
                              'text_similarity_threshold',
                              parseFloat(e.target.value)
                            )}
                            className="w-20 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="ml-2 text-sm text-gray-600">
                            {threshold.text_similarity_threshold.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={threshold.vector_similarity_threshold}
                            onChange={(e) => handleThresholdChange(
                              threshold.item_id,
                              'vector_similarity_threshold',
                              parseFloat(e.target.value)
                            )}
                            className="w-20 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="ml-2 text-sm text-gray-600">
                            {threshold.vector_similarity_threshold.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>

        {/* フッター */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <button
            onClick={handleReset}
            disabled={saving || loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? '処理中...' : 'デフォルトにリセット'}
          </button>
          
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              キャンセル
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}; 