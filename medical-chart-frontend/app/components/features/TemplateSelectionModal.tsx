import React, { useState, useEffect } from 'react';
import { fetchTemplates, fetchTemplateById, deleteTemplate } from '@/app/lib/api';
import { Template } from '@/app/lib/types';

interface TemplateSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (templateId: string) => void;
  onCreateNewTemplate: () => void;
  onEditTemplate?: (templateId: string) => void;
}

const TemplateSelectionModal: React.FC<TemplateSelectionModalProps> = ({
  isOpen,
  onClose,
  onSelectTemplate,
  onCreateNewTemplate,
  onEditTemplate
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // プレビュー用の状態
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchTemplates()
        .then(data => {
          setTemplates(data.templates);
          setLoading(false);
        })
        .catch(err => {
          setError('テンプレート一覧の取得に失敗しました');
          setLoading(false);
        });
    } else {
      // モーダルが閉じられたらプレビュー状態をリセット
      setPreviewTemplate(null);
    }
  }, [isOpen]);

  // テンプレート詳細を取得する関数
  const handlePreviewTemplate = async (templateId: string) => {
    setPreviewLoading(true);
    try {
      const template = await fetchTemplateById(templateId);
      setPreviewTemplate(template);
    } catch (err) {
      console.error('テンプレート詳細取得エラー:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  // プレビューを閉じる
  const handleClosePreview = () => {
    setPreviewTemplate(null);
  };

  // テンプレート削除処理
  const handleDeleteTemplate = async (templateId: string, templateName: string) => {
    if (!confirm(`テンプレート「${templateName}」を削除してもよろしいですか？この操作は元に戻せません。`)) {
      return;
    }

    try {
      setLoading(true);
      await deleteTemplate(templateId);
      
      // テンプレート一覧を再取得
      const data = await fetchTemplates();
      setTemplates(data.templates);
      
      // プレビュー中のテンプレートが削除された場合はプレビューを閉じる
      if (previewTemplate && previewTemplate.id === templateId) {
        setPreviewTemplate(null);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('テンプレート削除エラー:', err);
      setError('テンプレートの削除に失敗しました');
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-3/4 max-w-3xl max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
          <h2 className="text-xl font-semibold text-gray-800">抽出項目テンプレート選択</h2>
        </div>
        
        <div className="p-5 overflow-y-auto max-h-[calc(80vh-130px)]">
          {loading ? (
            <div className="flex justify-center my-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="text-red-500 text-center my-8">{error}</div>
          ) : previewTemplate ? (
            // テンプレートプレビュー表示
            <div className="bg-white p-4 rounded-lg">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">{previewTemplate.name}</h3>
                <button 
                  onClick={handleClosePreview}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="text-sm text-gray-600 mb-3">{previewTemplate.description}</div>
              
              <div className="mb-4">
                <span className={`text-xs px-2 py-1 rounded-full ${previewTemplate.type === 'system' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}`}>
                  {previewTemplate.type === 'system' ? 'システム' : 'カスタム'}
                </span>
                <span className="text-xs text-gray-500 ml-2">
                  作成日: {new Date(previewTemplate.created_at).toLocaleDateString()}
                </span>
              </div>
              
              <div className="border-t pt-3">
                <h4 className="font-medium mb-2">テンプレート項目一覧</h4>
                <ul className="space-y-2">
                  {previewTemplate.items
                    .filter(item => item.enabled)
                    .sort((a, b) => a.display_order - b.display_order)
                    .map((item, index) => (
                      <li key={index} className="flex items-center p-2 bg-gray-50 rounded-md">
                        <span className="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-800 rounded-full mr-2">
                          {index + 1}
                        </span>
                        <span>{item.name}</span>
                        {item.description && (
                          <span className="ml-2 text-xs text-gray-500">{item.description}</span>
                        )}
                      </li>
                    ))}
                </ul>
              </div>
              
              <div className="mt-4 flex justify-between">
                {/* カスタムテンプレートの場合のみ編集・削除ボタンを表示 */}
                {previewTemplate.type === 'user' && (
                  <div className="flex space-x-2">
                    {onEditTemplate && (
                      <button 
                        className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded-md transition-colors flex items-center"
                        onClick={() => onEditTemplate(previewTemplate.id)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        編集
                      </button>
                    )}
                    <button 
                      className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-md transition-colors flex items-center"
                      onClick={() => handleDeleteTemplate(previewTemplate.id, previewTemplate.name)}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      削除
                    </button>
                  </div>
                )}
                <button 
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors"
                  onClick={() => onSelectTemplate(previewTemplate.id)}
                >
                  このテンプレートを使用
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {templates.map(template => (
                <div 
                  key={template.id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-gradient-to-r from-white to-gray-50"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium text-lg">{template.name}</h3>
                    <span className={`text-xs px-2 py-1 rounded-full ${template.type === 'system' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}`}>
                      {template.type === 'system' ? 'システム' : 'カスタム'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                  <div className="text-xs text-gray-500 mb-3">
                    項目数: {template.item_count !== undefined ? template.item_count : (template.items ? template.items.filter(item => item.enabled).length : 0)}
                  </div>
                  <div className="flex justify-between">
                    <div className="flex space-x-2">
                      <button 
                        className="text-blue-600 hover:text-blue-800 text-sm"
                        onClick={() => handlePreviewTemplate(template.id)}
                      >
                        詳細を見る
                      </button>
                      {/* カスタムテンプレートの場合のみ編集・削除アイコンを表示 */}
                      {template.type === 'user' && (
                        <>
                          {onEditTemplate && (
                            <button 
                              className="text-gray-600 hover:text-gray-800 text-sm"
                              onClick={() => onEditTemplate(template.id)}
                              title="テンプレートを編集"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </button>
                          )}
                          <button 
                            className="text-red-500 hover:text-red-700 text-sm"
                            onClick={() => handleDeleteTemplate(template.id, template.name)}
                            title="テンプレートを削除"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </>
                      )}
                    </div>
                    <button 
                      className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm transition-colors"
                      onClick={() => onSelectTemplate(template.id)}
                    >
                      選択
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {previewLoading && (
            <div className="fixed inset-0 bg-black bg-opacity-25 flex items-center justify-center z-10">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          )}
        </div>
        
        <div className="p-4 border-t bg-gray-50 flex justify-between">
          <button
            onClick={onCreateNewTemplate}
            className="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-md transition-colors flex items-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            新規テンプレート作成
          </button>
          <button
            onClick={onClose}
            className="bg-gray-300 hover:bg-gray-400 text-gray-800 px-4 py-2 rounded-md transition-colors"
          >
            キャンセル
          </button>
        </div>
      </div>
    </div>
  );
};

export default TemplateSelectionModal; 