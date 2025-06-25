import axios from 'axios';
import { ChartCreateResponse, ChartStatusResponse, ChartData, ChartDataV2, ReviewItemsResponse, ItemUpdateRequest, ExtractedDataItemV2, TemplatesResponse, Template, TemplateCreateRequest, TemplateUpdateRequest, TemplateItemUpdateRequest, TemplateItem, GenericResponse, BulkSimilarityThresholdUpdate, SimilarityThresholdSettings } from './types';
import { getApiBaseUrl, getApiKey } from './apiConfig';

// APIのベースURL
const API_BASE_URL = getApiBaseUrl();

// APIキー
const API_KEY = getApiKey();

// Axiosインスタンスの作成
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'X-API-KEY': API_KEY,
  },
});

// デバッグモード
const DEBUG = true;

// APIキーをエクスポートしたgetApiKey関数はapiConfig.tsに移動済み

// カルテ画像のアップロード
export const uploadChart = async (file: File): Promise<ChartCreateResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    if (DEBUG) console.log(`APIリクエスト: POST /api/v1/charts (ファイル: ${file.name})`);
    
    const response = await api.post<ChartCreateResponse>('/api/v1/charts', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (DEBUG) console.log('APIレスポンス:', response.data);
    return response.data;
  } catch (error) {
    console.error('APIエラー - uploadChart:', error);
    throw error;
  }
};

// テンプレート指定付きでカルテ画像をアップロード
export const uploadChartWithTemplate = async (file: File, templateId: string): Promise<ChartCreateResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    if (DEBUG) console.log(`APIリクエスト: POST /api/v2/charts/upload?template_id=${templateId} (ファイル: ${file.name})`);
    
    const response = await api.post<ChartCreateResponse>(`/api/v2/charts/upload?template_id=${templateId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (DEBUG) console.log('APIレスポンス:', response.data);
    return response.data;
  } catch (error) {
    console.error('APIエラー - uploadChartWithTemplate:', error);
    throw error;
  }
};

// 処理ステータスの確認
export const getChartStatus = async (chartId: string): Promise<ChartStatusResponse> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v1/charts/${chartId}/status`);
    
    const response = await api.get<ChartStatusResponse>(`/api/v1/charts/${chartId}/status`);
    
    if (DEBUG) console.log('APIレスポンス - getChartStatus:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - getChartStatus (${chartId}):`, error);
    throw error;
  }
};

// 抽出結果の取得 (元の実装)
export const getChartResult = async (chartId: string): Promise<ChartData> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v1/charts/${chartId}`);
    
    const response = await api.get<ChartData>(`/api/v1/charts/${chartId}`);
    
    if (DEBUG) console.log('APIレスポンス - getChartResult:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - getChartResult (${chartId}):`, error);
    throw error;
  }
};

// 抽出結果の取得 (拡張版APIレスポンス対応)
export const getChartResultV2 = async (chartId: string): Promise<ChartDataV2> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v1/charts/${chartId} (V2)`);
    
    const response = await api.get<ChartDataV2>(`/api/v1/charts/${chartId}`);
    
    if (DEBUG) console.log('APIレスポンス - getChartResultV2:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - getChartResultV2 (${chartId}):`, error);
    throw error;
  }
};

// テンプレート指定による再抽出
export const reExtractWithTemplate = async (chartId: string, templateId: string): Promise<ChartStatusResponse> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: POST /api/v2/charts/${chartId}/extract?template_id=${templateId}`);
    
    const response = await api.post<ChartStatusResponse>(`/api/v2/charts/${chartId}/extract?template_id=${templateId}`);
    
    if (DEBUG) console.log('APIレスポンス - reExtractWithTemplate:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - reExtractWithTemplate (${chartId}, ${templateId}):`, error);
    throw error;
  }
};

// 要レビュー項目のリスト取得
export const getReviewItems = async (chartId: string): Promise<ReviewItemsResponse> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v1/charts/${chartId}/review-items`);
    
    const response = await api.get<ReviewItemsResponse>(`/api/v1/charts/${chartId}/review-items`);
    
    if (DEBUG) console.log('APIレスポンス - getReviewItems:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - getReviewItems (${chartId}):`, error);
    throw error;
  }
};

// 抽出項目の編集・承認
export const updateItem = async (
  chartId: string, 
  itemId: number, 
  updateData: ItemUpdateRequest
): Promise<ExtractedDataItemV2> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: PATCH /api/v1/charts/${chartId}/items/${itemId}`, JSON.stringify(updateData, null, 2));
    
    // 常に正しいIDを取得してから更新（itemIdに依存しない）
    let correctItemId = itemId;
    
    try {
      // 実際の正しいIDをreview-itemsから取得
      const reviewItems = await getReviewItems(chartId);
      if (reviewItems.review_items.length > 0) {
        if (DEBUG) console.log(`検索対象item_name: "${updateData.item_name}"`);
        if (DEBUG) console.log('利用可能なreview_items:', reviewItems.review_items.map(item => ({ id: item.id, name: item.item_name })));
        
        // reviewItemsから一致する項目名のアイテムを検索
        const matchingItem = reviewItems.review_items.find(item => 
          item.item_name === updateData.item_name
        );
        
        if (matchingItem) {
          // 一致するアイテムが見つかった場合はそのIDを使用
          correctItemId = matchingItem.id;
          if (correctItemId !== itemId) {
            console.log(`IDを補正: ${itemId} -> ${correctItemId} (item_name: ${updateData.item_name})`);
          } else {
            console.log(`IDは正しいです: ${itemId} (item_name: ${updateData.item_name})`);
          }
        } else {
          console.warn(`警告: "${updateData.item_name}" に一致する項目が見つかりませんでした。fallback IDを使用します。`);
        }
      }
    } catch (error) {
      console.error('レビュー項目取得中にエラーが発生しました:', error);
      // エラーが発生した場合は元のIDを使用
    }
    
    console.log(`最終的に使用するID: ${correctItemId} (item_name: ${updateData.item_name})`);
    console.log('送信データ:', JSON.stringify(updateData, null, 2));
    
    const response = await api.patch<ExtractedDataItemV2>(
      `/api/v1/charts/${chartId}/items/${correctItemId}`,
      updateData
    );
    
    if (DEBUG) console.log('APIレスポンス - updateItem:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - updateItem (${chartId}, ${itemId}, ${updateData.item_name}):`, error);
    throw error;
  }
};

// CSVファイルのダウンロードURL生成
export const getCSVDownloadUrl = (chartId: string): string => {
  return `${API_BASE_URL}/api/v1/charts/${chartId}/csv`;
};

// データ形式を標準形式に変換
export const convertToStandardFormat = async (chartId: string): Promise<GenericResponse> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: POST /api/v1/charts/${chartId}/convert-format`);
    
    const response = await api.post<GenericResponse>(`/api/v1/charts/${chartId}/convert-format`);
    
    if (DEBUG) console.log('APIレスポンス - convertToStandardFormat:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - convertToStandardFormat (${chartId}):`, error);
    throw error;
  }
};

// テンプレート一覧の取得
export const fetchTemplates = async (type?: string, limit: number = 20, offset: number = 0): Promise<TemplatesResponse> => {
  try {
    let url = `/api/v2/templates/?limit=${limit}&offset=${offset}`;
    if (type) {
      url += `&type=${type}`;
    }
    
    if (DEBUG) console.log(`APIリクエスト: GET ${url}`);
    
    const response = await api.get<TemplatesResponse>(url);
    
    if (DEBUG) console.log('APIレスポンス - fetchTemplates:', response.data);
    return response.data;
  } catch (error) {
    console.error('APIエラー - fetchTemplates:', error);
    throw error;
  }
};

// 特定テンプレートの詳細取得
export const fetchTemplateById = async (templateId: string): Promise<Template> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v2/templates/${templateId}`);
    
    const response = await api.get<Template>(`/api/v2/templates/${templateId}`);
    
    if (DEBUG) console.log('APIレスポンス - fetchTemplateById:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - fetchTemplateById (${templateId}):`, error);
    throw error;
  }
};

// 新規テンプレート作成
export const createTemplate = async (templateData: TemplateCreateRequest): Promise<Template> => {
  try {
    if (DEBUG) console.log('APIリクエスト: POST /api/v2/templates/', JSON.stringify(templateData, null, 2));
    
    const response = await api.post<Template>('/api/v2/templates/', templateData);
    
    if (DEBUG) console.log('APIレスポンス - createTemplate:', response.data);
    return response.data;
  } catch (error) {
    console.error('APIエラー - createTemplate:', error);
    throw error;
  }
};

// テンプレート更新
export const updateTemplate = async (templateId: string, templateData: TemplateUpdateRequest): Promise<Template> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: PUT /api/v2/templates/${templateId}`, JSON.stringify(templateData, null, 2));
    
    const response = await api.put<Template>(`/api/v2/templates/${templateId}`, templateData);
    
    if (DEBUG) console.log('APIレスポンス - updateTemplate:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - updateTemplate (${templateId}):`, error);
    throw error;
  }
};

// テンプレート削除
export const deleteTemplate = async (templateId: string): Promise<void> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: DELETE /api/v2/templates/${templateId}`);
    
    await api.delete(`/api/v2/templates/${templateId}`);
    
    if (DEBUG) console.log('テンプレートが正常に削除されました');
  } catch (error) {
    console.error(`APIエラー - deleteTemplate (${templateId}):`, error);
    throw error;
  }
};

// テンプレート項目更新
export const updateTemplateItem = async (itemId: string, updateData: TemplateItemUpdateRequest): Promise<TemplateItem> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: PUT /api/v2/templates/items/${itemId}`, JSON.stringify(updateData, null, 2));
    
    const response = await api.put<TemplateItem>(`/api/v2/templates/items/${itemId}`, updateData);
    
    if (DEBUG) console.log('APIレスポンス - updateTemplateItem:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - updateTemplateItem (${itemId}):`, error);
    throw error;
  }
};

// テンプレート項目削除
export const deleteTemplateItem = async (itemId: string): Promise<void> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: DELETE /api/v2/templates/items/${itemId}`);
    
    await api.delete(`/api/v2/templates/items/${itemId}`);
    
    if (DEBUG) console.log('テンプレート項目が正常に削除されました');
  } catch (error) {
    console.error(`APIエラー - deleteTemplateItem (${itemId}):`, error);
    throw error;
  }
};

// 類似度閾値設定の取得
export const getSimilarityThresholds = async (templateId: string): Promise<SimilarityThresholdSettings> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: GET /api/v2/templates/${templateId}/similarity-thresholds`);
    
    const response = await api.get<SimilarityThresholdSettings>(`/api/v2/templates/${templateId}/similarity-thresholds`);
    
    if (DEBUG) console.log('APIレスポンス - getSimilarityThresholds:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - getSimilarityThresholds (${templateId}):`, error);
    throw error;
  }
};

// 類似度閾値の一括更新
export const updateSimilarityThresholds = async (
  templateId: string, 
  thresholdData: BulkSimilarityThresholdUpdate
): Promise<TemplateItem[]> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: PUT /api/v2/templates/${templateId}/similarity-thresholds`, JSON.stringify(thresholdData, null, 2));
    
    const response = await api.put<TemplateItem[]>(`/api/v2/templates/${templateId}/similarity-thresholds`, thresholdData);
    
    if (DEBUG) console.log('APIレスポンス - updateSimilarityThresholds:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - updateSimilarityThresholds (${templateId}):`, error);
    throw error;
  }
};

// 類似度閾値のリセット
export const resetSimilarityThresholds = async (templateId: string): Promise<TemplateItem[]> => {
  try {
    if (DEBUG) console.log(`APIリクエスト: POST /api/v2/templates/${templateId}/reset-thresholds`);
    
    const response = await api.post<TemplateItem[]>(`/api/v2/templates/${templateId}/reset-thresholds`);
    
    if (DEBUG) console.log('APIレスポンス - resetSimilarityThresholds:', response.data);
    return response.data;
  } catch (error) {
    console.error(`APIエラー - resetSimilarityThresholds (${templateId}):`, error);
    throw error;
  }
}; 