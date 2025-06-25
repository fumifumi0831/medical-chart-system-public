import React, { useState, useEffect, useRef } from 'react';
import { fetchTemplateById, createTemplate, updateTemplate, updateTemplateItem, deleteTemplateItem } from '@/app/lib/api';
import { Template, TemplateItem, TemplateCreateRequest, TemplateUpdateRequest } from '@/app/lib/types';
import { SimilarityThresholdSettingsComponent } from './SimilarityThresholdSettings';

interface TemplateEditorProps {
  isOpen: boolean;
  onClose: () => void;
  templateId?: string; // 編集時に指定、新規作成時はundefined
  baseTemplateId?: string; // 新規作成時のベーステンプレートID（オプション）
}

const TemplateEditor: React.FC<TemplateEditorProps> = ({
  isOpen,
  onClose,
  templateId,
  baseTemplateId
}) => {
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [items, setItems] = useState<TemplateItem[]>([]);
  const [newItemName, setNewItemName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [templateType, setTemplateType] = useState<'system' | 'user'>('user');
  const [isEdit, setIsEdit] = useState<boolean>(false);
  
  // ドラッグ関連の状態
  const [draggedItem, setDraggedItem] = useState<number | null>(null);
  
  // 類似度閾値設定モーダル
  const [showThresholdSettings, setShowThresholdSettings] = useState<boolean>(false);

  // テンプレートデータの読み込み
  useEffect(() => {
    if (!isOpen) return;

    const loadTemplate = async () => {
      setLoading(true);
      try {
        let template: Template;
        
        if (templateId) {
          // 既存テンプレートの編集
          template = await fetchTemplateById(templateId);
          setName(template.name);
          setDescription(template.description);
          setItems(template.items);
          setTemplateType(template.type);
          setIsEdit(true);
        } else if (baseTemplateId) {
          // 既存テンプレートをベースにした新規作成
          template = await fetchTemplateById(baseTemplateId);
          setName(`${template.name}のコピー`);
          setDescription(template.description);
          setItems(template.items);
          setTemplateType('user');
          setIsEdit(false);
        } else {
          // 完全な新規作成
          setName('');
          setDescription('');
          setItems([]);
          setTemplateType('user');
          setIsEdit(false);
        }
        
        setLoading(false);
      } catch (err) {
        console.error('テンプレート読み込みエラー:', err);
        setError('テンプレートの読み込みに失敗しました');
        setLoading(false);
      }
    };

    loadTemplate();
  }, [isOpen, templateId, baseTemplateId]);

  // テンプレートの保存
  const handleSave = async () => {
    if (!name) {
      setError('テンプレート名を入力してください');
      return;
    }

    if (items.length === 0) {
      setError('少なくとも1つの項目を追加してください');
      return;
    }

    setSaving(true);
    try {
      if (isEdit && templateId) {
        // 既存テンプレートの更新
        const templateData: TemplateUpdateRequest = {
          name,
          description,
          items: items.map((item, index) => ({
            ...item,
            display_order: index + 1
          }))
        };
        
        await updateTemplate(templateId, templateData);
      } else {
        // 新規テンプレートの作成
        const templateData: TemplateCreateRequest = {
          name,
          description,
          type: templateType,
          created_by: 'frontend_user',
          base_template_id: baseTemplateId,
          items: items.map((item, index) => ({
            ...item,
            display_order: index + 1
          }))
        };
        
        await createTemplate(templateData);
      }
      
      setSaving(false);
      onClose();
    } catch (err) {
      console.error('テンプレート保存エラー:', err);
      setError('テンプレートの保存に失敗しました');
      setSaving(false);
    }
  };

  // ドラッグ開始時のハンドラ
  const handleDragStart = (index: number) => {
    setDraggedItem(index);
  };

  // ドラッグオーバー時のハンドラ
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault(); // ドロップを許可するために必要
  };

  // ドロップ時のハンドラ
  const handleDrop = (e: React.DragEvent<HTMLDivElement>, dropIndex: number) => {
    e.preventDefault();
    
    if (draggedItem === null) return;
    if (draggedItem === dropIndex) return;
    
    const reorderedItems = [...items];
    const [movedItem] = reorderedItems.splice(draggedItem, 1);
    reorderedItems.splice(dropIndex, 0, movedItem);
    
    setItems(reorderedItems);
    setDraggedItem(null);
  };

  // ドラッグ終了時のハンドラ
  const handleDragEnd = () => {
    setDraggedItem(null);
  };

  // 編集履歴管理用のstate
  const [editHistory, setEditHistory] = useState<Array<{
    action: string;
    previousState: any;
    timestamp: Date;
  }>>([]);

  // 編集履歴に追加
  const addToHistory = (action: string, previousState: any) => {
    const newHistory = [...editHistory];
    newHistory.push({
      action,
      previousState,
      timestamp: new Date()
    });
    // 最新5件のみ保持
    if (newHistory.length > 5) {
      newHistory.shift();
    }
    setEditHistory(newHistory);
  };

  // 元に戻す機能
  const undoLastChange = () => {
    if (editHistory.length === 0) return;
    
    const lastChange = editHistory[editHistory.length - 1];
    setItems(lastChange.previousState);
    
    // 履歴から削除
    const newHistory = [...editHistory];
    newHistory.pop();
    setEditHistory(newHistory);
  };

  // 項目の有効/無効切り替え
  const toggleItemEnabled = async (index: number) => {
    const previousState = [...items];
    const updatedItems = [...items];
    updatedItems[index] = {
      ...updatedItems[index],
      enabled: !updatedItems[index].enabled
    };
    
    // 履歴に追加
    addToHistory(`${items[index].name}を${items[index].enabled ? '無効' : '有効'}に変更`, previousState);
    
    setItems(updatedItems);
  };

  // 新規項目の追加
  const addNewItem = () => {
    if (!newItemName.trim()) {
      setError('項目名を入力してください');
      return;
    }
    
    // 同名の項目がないかチェック
    if (items.some(item => item.name === newItemName.trim())) {
      setError('同じ名前の項目が既に存在します');
      return;
    }
    
    const newItem: TemplateItem = {
      name: newItemName.trim(),
      enabled: true,
      display_order: items.length + 1,
      text_similarity_threshold: 0.85,  // テキスト類似度のデフォルト値
      vector_similarity_threshold: 0.90,  // ベクトル類似度のデフォルト値
      confidence_threshold: 0.90  // 下位互換性のため
    };
    
    setItems([...items, newItem]);
    setNewItemName('');
    setError(null);
  };

  // 項目の削除
  const removeItem = (index: number) => {
    const updatedItems = [...items];
    updatedItems.splice(index, 1);
    setItems(updatedItems);
  };

  // 個別項目の更新
  const handleItemUpdate = async (index: number) => {
    const item = items[index];
    
    if (!templateId || !item.id) {
      // 新規作成時はローカルでの更新のみ
      return;
    }

    try {
      setLoading(true);
      
      const updatedItem = await updateTemplateItem(item.id, {
        name: item.name,
        enabled: item.enabled,
        display_order: item.display_order,
        description: item.description,
        // 2つの類似度閾値を個別に送信
        text_similarity_threshold: item.text_similarity_threshold,
        vector_similarity_threshold: item.vector_similarity_threshold,
        // 下位互換性のため既存フィールドも維持
        confidence_threshold: item.confidence_threshold
      });
      
      // 成功したら項目リストを更新
      const updatedItems = [...items];
      updatedItems[index] = updatedItem;
      setItems(updatedItems);
      
      setLoading(false);
      setError(null);
    } catch (error) {
      console.error('項目更新エラー:', error);
      setError('項目の更新に失敗しました');
      setLoading(false);
    }
  };

  // 個別項目の削除
  const handleItemDelete = async (index: number) => {
    const item = items[index];
    
    if (items.length <= 1) {
      setError('テンプレートには少なくとも1つの項目が必要です');
      return;
    }
    
    if (!templateId || !item.id) {
      // 新規作成時はローカルでの削除のみ
      removeItem(index);
      return;
    }
    
    try {
      setLoading(true);
      
      await deleteTemplateItem(item.id);
      
      // 成功したら項目リストから削除
      removeItem(index);
      
      setLoading(false);
      setError(null);
    } catch (error) {
      console.error('項目削除エラー:', error);
      setError('項目の削除に失敗しました');
      setLoading(false);
    }
  };

  // 閾値の更新（自動保存付き）
  const updateTextSimilarityThreshold = async (index: number, threshold: number) => {
    const previousState = [...items];
    
    const updatedItems = [...items];
    updatedItems[index] = {
      ...updatedItems[index],
      text_similarity_threshold: threshold
    };
    
    // 履歴に追加
    addToHistory(`テキスト類似度を${items[index].text_similarity_threshold}→${threshold}に変更`, previousState);
    
    setItems(updatedItems);
  };

  const updateVectorSimilarityThreshold = async (index: number, threshold: number) => {
    const previousState = [...items];
    
    const updatedItems = [...items];
    updatedItems[index] = {
      ...updatedItems[index],
      vector_similarity_threshold: threshold,
      confidence_threshold: threshold  // 下位互換性のため
    };
    
    // 履歴に追加
    addToHistory(`ベクトル類似度を${items[index].vector_similarity_threshold}→${threshold}に変更`, previousState);
    
    setItems(updatedItems);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-3/4 max-w-3xl max-h-[90vh] overflow-hidden">
        <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-800">
              {isEdit ? 'テンプレート編集' : '新規テンプレート作成'}
            </h2>
            {editHistory.length > 0 && (
              <button
                onClick={undoLastChange}
                className="flex items-center px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors text-sm"
                title={`元に戻す: ${editHistory[editHistory.length - 1]?.action}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
                元に戻す
              </button>
            )}
          </div>
        </div>
        
        <div className="p-5 overflow-y-auto max-h-[calc(90vh-170px)]">
          {loading ? (
            <div className="flex justify-center my-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <>
              {error && (
                <div className="bg-red-50 text-red-600 p-3 rounded-md mb-4">
                  {error}
                </div>
              )}
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  テンプレート名 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="テンプレート名を入力"
                  className="w-full p-2 border rounded-md"
                  disabled={templateType === 'system'}
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  説明
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="テンプレートの説明を入力"
                  className="w-full p-2 border rounded-md"
                  rows={3}
                  disabled={templateType === 'system'}
                ></textarea>
              </div>
              
              <div className="mb-6">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-lg font-medium">抽出項目</h3>
                  <div className="flex items-center space-x-2">
                    {/* 類似度閾値設定ボタン */}
                    {isEdit && templateId && (
                      <button
                        type="button"
                        onClick={() => setShowThresholdSettings(true)}
                        className="flex items-center px-3 py-1 text-sm bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-md transition-colors"
                        title="類似度閾値を設定"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                        </svg>
                        類似度設定
                      </button>
                    )}
                    {templateType === 'system' && (
                      <div className="text-amber-600 text-sm">
                        <span className="bg-amber-100 px-2 py-1 rounded-full">
                          ※システムテンプレートは項目の並べ替えと有効/無効の切り替えのみ可能です
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="mb-4">
                  {items.map((item, index) => (
                    <div
                      key={item.name}
                      draggable={true}
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, index)}
                      onDragEnd={handleDragEnd}
                      className={`flex items-center justify-between p-3 mb-2 rounded-md border ${
                        item.enabled ? 'bg-white' : 'bg-gray-50 text-gray-500'
                      } ${draggedItem === index ? 'opacity-50' : 'opacity-100'} cursor-grab`}
                    >
                      <div className="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                        <span>{item.name}</span>
                      </div>
                      <div className="flex items-center">
                        <button
                          onClick={() => toggleItemEnabled(index)}
                          className="text-gray-500 hover:text-blue-500 mr-2"
                          title={item.enabled ? '無効化' : '有効化'}
                        >
                          {item.enabled ? (
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          ) : (
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                            </svg>
                          )}
                        </button>
                        
                        <button
                          onClick={() => handleItemDelete(index)}
                          className="text-gray-500 hover:text-red-500"
                          title="項目を削除"
                          disabled={templateType === 'system' || items.length <= 1}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                
                {templateType === 'user' && (
                  <div className="mt-4 border-t pt-4">
                    <h4 className="text-sm font-medium mb-2">新規項目の追加</h4>
                    <div className="flex">
                      <input
                        type="text"
                        value={newItemName}
                        onChange={(e) => setNewItemName(e.target.value)}
                        placeholder="新しい項目名を入力"
                        className="flex-1 p-2 border rounded-l-md"
                      />
                      <button
                        type="button"
                        onClick={addNewItem}
                        className="bg-blue-500 hover:bg-blue-600 text-white px-4 rounded-r-md transition-colors"
                      >
                        追加
                      </button>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-md transition-colors"
                >
                  キャンセル
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? '保存中...' : '保存'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 類似度閾値設定モーダル */}
      {showThresholdSettings && templateId && (
        <SimilarityThresholdSettingsComponent
          templateId={templateId}
          templateName={name}
          isOpen={showThresholdSettings}
          onClose={() => setShowThresholdSettings(false)}
          onUpdate={() => {
            // 必要に応じてテンプレートデータを再読み込み
            console.log('類似度閾値が更新されました');
          }}
        />
      )}
    </div>
  );
};

export default TemplateEditor; 