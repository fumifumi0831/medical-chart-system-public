'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ExtractedDataItemV2, ChartDataV2, ReviewItemsResponse, ItemUpdateRequest, Template } from '@/app/lib/types';
import { updateItem, getReviewItems, fetchTemplateById } from '@/app/lib/api';

// アイコンコンポーネント
const EditIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
  </svg>
);

const ApproveIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const CancelIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const SaveIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

interface ExtractedTextViewerProps {
  chartId: string;
  chartData: ChartDataV2 | null;
  onItemUpdated?: (updatedItem: ExtractedDataItemV2) => void;
}

const ExtractedTextViewer: React.FC<ExtractedTextViewerProps> = ({
  chartId,
  chartData,
  onItemUpdated,
}) => {
  // 編集中の項目を管理する（ID + 項目名で一意に特定）
  const [editingItemKey, setEditingItemKey] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [editComment, setEditComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOnlyReviewItems, setShowOnlyReviewItems] = useState(false);
  const [reviewItems, setReviewItems] = useState<ExtractedDataItemV2[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  // 項目名→IDのマッピングを保持
  const [itemIdMap, setItemIdMap] = useState<Record<string, number>>({});
  
  // テンプレート情報と閾値マッピングを追加
  const [templateData, setTemplateData] = useState<Template | null>(null);
  const [thresholdMap, setThresholdMap] = useState<Record<string, { text: number; vector: number }>>({});

  // 表示項目のフィルタリング
  const displayItems = useMemo(() => {
    // reviewItemsにデータがある場合はそれを優先的に使用
    if (reviewItems.length > 0) {
      return showOnlyReviewItems
        ? reviewItems.filter(item => item.needs_review)
        : reviewItems;
    }
    
    // reviewItemsが空の場合はchartDataから取得
    if (chartData && chartData.extracted_items && chartData.extracted_items.length > 0) {
      return showOnlyReviewItems
        ? chartData.extracted_items.filter(item => item.needs_review)
        : chartData.extracted_items;
    }
    
    return [];
  }, [chartData, showOnlyReviewItems, reviewItems]);

  // 項目名から正しいIDを取得する関数
  const getCorrectItemId = useCallback((itemName: string, fallbackId: number): number => {
    // 項目名に対応するIDがあればそれを返す
    if (itemIdMap[itemName] !== undefined) {
      return itemIdMap[itemName];
    }
    
    // レビュー項目から検索
    const reviewItem = reviewItems.find(item => item.item_name === itemName);
    if (reviewItem) {
      return reviewItem.id;
    }
    
    // 見つからなければフォールバックIDを返す
    return fallbackId;
  }, [itemIdMap, reviewItems]);

  // レビュー項目を取得する関数（再利用可能）
  const fetchReviewItems = useCallback(async () => {
    if (!chartId) return;
    
    setIsLoading(true);
    try {
      const response = await getReviewItems(chartId);
      if (response && response.review_items) {
        setReviewItems(response.review_items);
        
        // 項目名→IDのマッピングを構築
        const idMap: Record<string, number> = {};
        response.review_items.forEach(item => {
          idMap[item.item_name] = item.id;
        });
        setItemIdMap(idMap);
        
        console.log('レビュー項目を取得しました:', response.review_items);
        console.log('項目名→IDマッピング:', idMap);
      }
    } catch (err) {
      console.error('レビュー項目取得エラー:', err);
      setError('レビュー項目の取得中にエラーが発生しました。');
    } finally {
      setIsLoading(false);
    }
  }, [chartId]);

  // テンプレート詳細を取得する関数
  const fetchTemplateData = useCallback(async () => {
    if (!chartData?.template_id) {
      console.log('テンプレートIDが指定されていません。デフォルト閾値を使用します。');
      return;
    }

    try {
      console.log(`テンプレート詳細を取得中: ${chartData.template_id}`);
      const template = await fetchTemplateById(chartData.template_id);
      setTemplateData(template);
      
      // 項目名→閾値のマッピングを構築
      const thresholds: Record<string, { text: number; vector: number }> = {};
      template.items.forEach(item => {
        thresholds[item.name] = {
          text: item.text_similarity_threshold ?? 0.8, // デフォルト値
          vector: item.vector_similarity_threshold ?? 0.8 // デフォルト値
        };
      });
      setThresholdMap(thresholds);
      
      console.log('テンプレート詳細を取得しました:', template);
      console.log('閾値マッピング:', thresholds);
    } catch (error) {
      console.error('テンプレート詳細取得エラー:', error);
      // エラーが発生した場合はデフォルト閾値を使用
    }
  }, [chartData?.template_id]);

  // コンポーネントがマウントされた時とカルテIDが変更された時にレビュー項目を取得
  useEffect(() => {
    fetchReviewItems();
    fetchTemplateData();
  }, [fetchReviewItems, fetchTemplateData]);

  // 項目の一意識別キーを生成
  const getItemKey = (item: ExtractedDataItemV2): string => {
    return `${item.id}-${item.item_name}`;
  };

  // 編集開始
  const handleEditStart = (item: ExtractedDataItemV2) => {
    const itemKey = getItemKey(item);
    setEditingItemKey(itemKey);
    setEditText(item.interpreted_text || item.raw_text || '');
    setEditComment(item.review_comment || '');
    setError(null);
  };

  // 編集キャンセル
  const handleEditCancel = () => {
    setEditingItemKey(null);
    setEditText('');
    setEditComment('');
    setError(null);
  };

  // 編集内容を保存・承認
  const handleEditSave = async (item: ExtractedDataItemV2) => {
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      // 正しいIDを取得
      const correctId = getCorrectItemId(item.item_name, item.id);
      
      // IDが異なる場合はログに記録
      if (correctId !== item.id) {
        console.log(`処理中のitemIdを補正: ${item.id} -> ${correctId}`);
      }

      // リクエストデータを準備
      const updateRequest: ItemUpdateRequest = {
        item_name: item.item_name,
        interpreted_text: editText || undefined,
        review_comment: editComment || undefined,
        reviewed_by: 'current_user' // 実際のユーザー識別子に置き換える
      };
      
      console.log('保存して承認リクエスト:', updateRequest);
      
      const updatedItem = await updateItem(chartId, correctId, updateRequest);
      console.log('保存して承認レスポンス:', updatedItem);
      console.log('更新対象ID:', updatedItem.id, '更新対象項目名:', updatedItem.item_name);
      
      // ローカル状態の更新（デバッグ出力追加）
      console.log('更新前のreviewItems:', reviewItems);
      setReviewItems(prevItems => {
        // prevItemsの各アイテムのIDを出力
        prevItems.forEach(prevItem => {
          console.log(`比較: prevItem.id=${prevItem.id}(${typeof prevItem.id}) vs updatedItem.id=${updatedItem.id}(${typeof updatedItem.id})`);
          console.log(`比較: prevItem.item_name="${prevItem.item_name}" vs updatedItem.item_name="${updatedItem.item_name}"`);
        });
        
        // 更新後の配列を作成
        const newItems = prevItems.map(prevItem => {
          // IDと項目名の両方が一致する場合のみ更新
          if (String(prevItem.id) === String(updatedItem.id) && prevItem.item_name === updatedItem.item_name) {
            console.log('更新対象アイテム特定:', prevItem.id, prevItem.item_name);
            console.log('新データ:', updatedItem);
            return updatedItem;
          }
          
          // それ以外のアイテムは変更なし
          console.log('更新対象外アイテム:', prevItem.id, prevItem.item_name);
          return prevItem;
        });
        
        console.log('更新後のreviewItems:', newItems);
        return newItems;
      });
      
      setEditingItemKey(null);
      if (onItemUpdated) {
        onItemUpdated(updatedItem);
      }
      
      // 承認後に最新のレビュー項目を再取得
      await fetchReviewItems();
    } catch (err) {
      console.error('項目更新エラー:', err);
      setError('項目の更新中にエラーが発生しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 直接承認（編集なしで承認のみ）
  const handleApprove = async (item: ExtractedDataItemV2) => {
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      // 正しいIDを取得
      const correctId = getCorrectItemId(item.item_name, item.id);
      
      // IDが異なる場合はログに記録
      if (correctId !== item.id) {
        console.log(`処理中のitemIdを補正: ${item.id} -> ${correctId}`);
      }

      // 編集モード中かどうかチェック
      const itemKey = getItemKey(item);
      const isEditing = editingItemKey === itemKey;
      
      // リクエストデータを作成
      const updateRequest: ItemUpdateRequest = {
        item_name: item.item_name,
        // 編集モード中の場合は編集中のテキストを、そうでなければ現在の解釈テキストを使用
        interpreted_text: isEditing ? editText || undefined : item.interpreted_text || undefined,
        // 編集モード中の場合はコメントを含める
        review_comment: isEditing ? editComment || undefined : item.review_comment || undefined,
        reviewed_by: 'current_user' // 実際のユーザー識別子に置き換える
      };
      
      console.log('承認リクエスト:', updateRequest);
      
      const updatedItem = await updateItem(chartId, correctId, updateRequest);
      console.log('承認レスポンス:', updatedItem);
      console.log('更新対象ID:', updatedItem.id, '更新対象項目名:', updatedItem.item_name);
      
      // ローカル状態の更新（デバッグ出力追加）
      console.log('更新前のreviewItems:', reviewItems);
      setReviewItems(prevItems => {
        // prevItemsの各アイテムのIDを出力
        prevItems.forEach(prevItem => {
          console.log(`比較: prevItem.id=${prevItem.id}(${typeof prevItem.id}) vs updatedItem.id=${updatedItem.id}(${typeof updatedItem.id})`);
          console.log(`比較: prevItem.item_name="${prevItem.item_name}" vs updatedItem.item_name="${updatedItem.item_name}"`);
        });
        
        // 更新後の配列を作成
        const newItems = prevItems.map(prevItem => {
          // IDと項目名の両方が一致する場合のみ更新
          if (String(prevItem.id) === String(updatedItem.id) && prevItem.item_name === updatedItem.item_name) {
            console.log('更新対象アイテム特定:', prevItem.id, prevItem.item_name);
            console.log('新データ:', updatedItem);
            return updatedItem;
          }
          
          // それ以外のアイテムは変更なし
          console.log('更新対象外アイテム:', prevItem.id, prevItem.item_name);
          return prevItem;
        });
        
        console.log('更新後のreviewItems:', newItems);
        return newItems;
      });
      
      // 編集モード中だった場合は編集モードを終了
      if (isEditing) {
        setEditingItemKey(null);
      }
      
      if (onItemUpdated) {
        onItemUpdated(updatedItem);
      }
      
      // 承認後に最新のレビュー項目を再取得
      await fetchReviewItems();
    } catch (err) {
      console.error('項目承認エラー:', err);
      setError('項目の承認中にエラーが発生しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 差分表示用の関数
  const renderDiff = (raw: string | null, interpreted: string | null) => {
    if (!raw) return <span className="text-gray-400">（テキストなし）</span>;
    if (!interpreted) return <span>{raw}</span>;
    if (raw === interpreted) return <span>{raw}</span>;

    return (
      <span>
        <span className="line-through text-red-500">{raw}</span>
        <span className="mx-1">→</span>
        <span className="text-green-600">{interpreted}</span>
      </span>
    );
  };

  // 項目別の閾値を取得する関数
  const getThresholdForItem = useCallback((itemName: string, type: 'text' | 'vector'): number => {
    const threshold = thresholdMap[itemName];
    if (threshold) {
      return type === 'text' ? threshold.text : threshold.vector;
    }
    // フォールバック: デフォルト値を使用
    return 0.8;
  }, [thresholdMap]);

  // 信頼度スコアの色分け（動的閾値対応）
  const getConfidenceColor = useCallback((score: number, itemName: string, scoreType: 'confidence' | 'similarity') => {
    let threshold: number;
    
    if (scoreType === 'similarity') {
      // similarity_scoreの場合はtext_similarity_thresholdを使用
      threshold = getThresholdForItem(itemName, 'text');
    } else {
      // confidence_scoreの場合はvector_similarity_thresholdを使用
      threshold = getThresholdForItem(itemName, 'vector');
    }
    
    if (score >= threshold) return 'text-green-600';
    if (score >= threshold * 0.75) return 'text-yellow-600'; // 閾値の75%以上で黄色
    return 'text-red-600';
  }, [getThresholdForItem]);

  if ((!chartData || !chartData.extracted_items || chartData.extracted_items.length === 0) && reviewItems.length === 0) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg text-center text-gray-500">
        <p>抽出データがありません</p>
        <p className="mt-2 text-sm">抽出項目設定ボタンからテンプレートを選択して再抽出してください</p>
      </div>
    );
  }

  const reviewItemsCount = reviewItems.filter(item => item.needs_review).length || 
                          (chartData?.extracted_items?.filter(item => item.needs_review).length || 0);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">
          抽出結果
          {reviewItemsCount > 0 && (
            <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
              要確認: {reviewItemsCount}
            </span>
          )}
        </h3>
        <div className="flex items-center">
          <input
            type="checkbox"
            id="show-review-only"
            checked={showOnlyReviewItems}
            onChange={(e) => setShowOnlyReviewItems(e.target.checked)}
            className="mr-2"
          />
          <label htmlFor="show-review-only" className="text-sm">
            要確認項目のみ表示
          </label>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded-md mb-4">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="p-4 bg-gray-50 rounded-lg text-center text-gray-500">
          <div className="animate-pulse">データを読み込み中...</div>
        </div>
      ) : displayItems && displayItems.length > 0 ? (
        <div className="space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
          {displayItems.map((item) => (
            <div 
              key={getItemKey(item)} 
              className={`p-4 rounded-lg border shadow-sm hover:shadow-md transition-shadow duration-200 ${
                item.needs_review 
                  ? 'border-l-4 border-l-yellow-500 bg-yellow-50' 
                  : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="font-semibold text-gray-800">{item.item_name}</div>
                <div className="flex space-x-2">
                  {item.needs_review && (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                      要確認
                    </span>
                  )}
                  <span 
                    className={`px-2 py-1 text-xs rounded-full ${getConfidenceColor(item.confidence_score, item.item_name, 'confidence')} bg-opacity-20 relative group`}
                  >
                    内容の正確性: {Math.round(item.confidence_score * 100)}%
                    <span className="ml-1 inline-flex items-center justify-center w-4 h-4 bg-gray-200 rounded-full text-gray-600 text-xs cursor-help">?</span>
                    <span className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                      AIが認識した医療情報の意味が原文とどれだけ一致しているかを示します
                    </span>
                  </span>
                  <span 
                    className={`px-2 py-1 text-xs rounded-full ${getConfidenceColor(item.similarity_score, item.item_name, 'similarity')} bg-opacity-20 relative group`}
                  >
                    文字の認識精度: {Math.round(item.similarity_score * 100)}%
                    <span className="ml-1 inline-flex items-center justify-center w-4 h-4 bg-gray-200 rounded-full text-gray-600 text-xs cursor-help">?</span>
                    <span className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                      AIが読み取った文字が原文とどれだけ正確に一致しているかを示します
                    </span>
                  </span>
                </div>
              </div>

              {editingItemKey === getItemKey(item) ? (
                // 編集モード
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">生テキスト:</label>
                    <div className="p-2 bg-gray-100 rounded">{item.raw_text || '（なし）'}</div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">解釈テキスト:</label>
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-300 focus:border-blue-300"
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">レビューコメント:</label>
                    <textarea
                      value={editComment}
                      onChange={(e) => setEditComment(e.target.value)}
                      className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-300 focus:border-blue-300"
                      rows={2}
                      placeholder="オプションのコメント"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={handleEditCancel}
                      className="flex items-center px-3 py-1.5 bg-gradient-to-r from-gray-300 to-gray-400 text-gray-800 rounded-md hover:from-gray-400 hover:to-gray-500 transition-all duration-200 shadow-sm hover:shadow"
                      disabled={isSubmitting}
                    >
                      <CancelIcon />
                      キャンセル
                    </button>
                    <button
                      onClick={() => handleEditSave(item)}
                      className="flex items-center px-3 py-1.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-md hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-sm hover:shadow"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? <SpinnerIcon /> : <SaveIcon />}
                      {isSubmitting ? '保存中...' : '保存して承認'}
                    </button>
                  </div>
                </div>
              ) : (
                // 表示モード
                <>
                  <div className="mb-3">
                    <div className="text-sm text-gray-600 mb-1">テキスト:</div>
                    <div className="pl-2">
                      {renderDiff(item.raw_text, item.interpreted_text)}
                    </div>
                  </div>

                  {item.review_comment && (
                    <div className="mb-3">
                      <div className="text-sm text-gray-600 mb-1">レビューコメント:</div>
                      <div className="pl-2 text-gray-700">{item.review_comment}</div>
                    </div>
                  )}

                  {item.reviewed_by && (
                    <div className="text-xs text-gray-500 mb-3">
                      レビュー: {item.reviewed_by} ({new Date(item.reviewed_at || '').toLocaleString()})
                    </div>
                  )}

                  <div className="flex justify-end space-x-2">
                    {!item.reviewed_by ? (
                      <>
                        <button
                          onClick={() => handleEditStart(item)}
                          className="flex items-center px-3 py-1.5 bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 rounded-md hover:from-gray-200 hover:to-gray-300 transition-all duration-200 shadow-sm hover:shadow"
                          disabled={isSubmitting}
                        >
                          <EditIcon />
                          編集
                        </button>
                        {/* 内容の正確性または文字の認識精度が閾値未満の場合、または要確認フラグがある場合に承認ボタンを表示 */}
                        {(item.confidence_score < getThresholdForItem(item.item_name, 'vector') || 
                          item.similarity_score < getThresholdForItem(item.item_name, 'text') || 
                          item.needs_review) && (
                          <button
                            onClick={() => handleApprove(item)}
                            className="flex items-center px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-md hover:from-green-600 hover:to-emerald-600 transition-all duration-200 shadow-sm hover:shadow"
                            disabled={isSubmitting}
                          >
                            {isSubmitting ? <SpinnerIcon /> : <ApproveIcon />}
                            {isSubmitting ? '処理中...' : '承認'}
                          </button>
                        )}
                      </>
                    ) : (
                      <button
                        onClick={() => handleEditStart(item)}
                        className="flex items-center px-3 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-md hover:from-indigo-600 hover:to-purple-600 transition-all duration-200 shadow-sm hover:shadow"
                        disabled={isSubmitting}
                      >
                        <EditIcon />
                        再編集
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 bg-gray-50 rounded-lg text-center text-gray-500">
          {showOnlyReviewItems 
            ? (
              <>
                <p>要確認の項目はありません</p>
                <button 
                  onClick={() => setShowOnlyReviewItems(false)}
                  className="mt-2 text-sm text-blue-500 hover:text-blue-700 underline"
                >
                  全ての項目を表示する
                </button>
              </>
            ) 
            : '抽出データがありません'}
        </div>
      )}
    </div>
  );
};

export default ExtractedTextViewer; 