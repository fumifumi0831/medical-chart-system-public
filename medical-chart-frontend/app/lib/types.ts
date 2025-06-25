export interface ExtractedDataItem {
  item_name: string;
  item_value: string | null;
}

// 拡張版の抽出データ項目
export interface ExtractedDataItemV2 {
  id: number;
  item_name: string;
  raw_text: string | null;
  interpreted_text: string | null;
  similarity_score: number;
  confidence_score: number;
  needs_review: boolean;
  review_comment: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

// 要レビュー項目の取得レスポンス
export interface ReviewItemsResponse {
  chart_id: string;
  review_items: ExtractedDataItemV2[];
}

// 項目更新リクエスト
export interface ItemUpdateRequest {
  item_name: string;
  interpreted_text?: string;
  review_comment?: string;
  reviewed_by: string;
}

export interface ChartData {
  chart_id: string;
  original_filename?: string;
  gcs_uri?: string;
  image_url?: string;
  status: string;
  extracted_data?: ExtractedDataItem[];
  message?: string;
  error_message?: string;
}

// 拡張版のチャートデータ
export interface ChartDataV2 {
  chart_id: string;
  original_filename?: string;
  gcs_uri?: string;
  image_url?: string;
  status: string;
  overall_confidence_score?: number;
  needs_review?: boolean;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  extracted_timestamp?: string;
  extracted_items?: ExtractedDataItemV2[];
  message?: string;
  error_message?: string;
  template_id?: string;
  template_name?: string;
}

export interface ChartStatusResponse {
  chart_id: string;
  status: string; // 'pending' | 'processing' | 'completed' | 'failed' または 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  error_message?: string;
}

export interface ChartCreateResponse {
  chart_id: string;
  status: string;
  message: string;
  template_id?: string;
  template_name?: string;
}

// テンプレート項目
export interface TemplateItem {
  id?: string;
  name: string;
  enabled: boolean;
  display_order: number;
  description?: string;
  // 2つの類似度閾値を個別に管理
  text_similarity_threshold?: number;
  vector_similarity_threshold?: number;
  // 下位互換性のため既存フィールドも維持
  confidence_threshold?: number;
}

// テンプレート
export interface Template {
  id: string;
  name: string;
  description: string;
  type: 'system' | 'user';
  created_at: string;
  updated_at?: string;
  created_by?: string;
  items: TemplateItem[];
  item_count?: number;
}

// テンプレート一覧レスポンス
export interface TemplatesResponse {
  total: number;
  templates: Template[];
}

// テンプレート作成リクエスト
export interface TemplateCreateRequest {
  name: string;
  description: string;
  type: 'system' | 'user';
  created_by: string;
  base_template_id?: string;
  items: TemplateItem[];
}

// テンプレート更新リクエスト
export interface TemplateUpdateRequest {
  name: string;
  description: string;
  items: TemplateItem[];
}

// テンプレート項目更新リクエスト
export interface TemplateItemUpdateRequest {
  name?: string;
  enabled?: boolean;
  display_order?: number;
  description?: string;
  // 2つの類似度閾値を個別に管理
  text_similarity_threshold?: number;
  vector_similarity_threshold?: number;
  // 下位互換性のため既存フィールドも維持
  confidence_threshold?: number;
}

// 類似度閾値更新リクエスト
export interface SimilarityThresholdUpdate {
  item_id: string;
  text_similarity_threshold: number;
  vector_similarity_threshold: number;
}

// 一括類似度閾値更新リクエスト
export interface BulkSimilarityThresholdUpdate {
  updates: SimilarityThresholdUpdate[];
}

// 類似度閾値設定レスポンス
export interface SimilarityThresholdSettings {
  template_id: string;
  template_name: string;
  thresholds: {
    item_id: string;
    item_name: string;
    text_similarity_threshold: number;
    vector_similarity_threshold: number;
    confidence_threshold: number;
  }[];
}

// 汎用的なレスポンス型
export interface GenericResponse {
  success: boolean;
  message: string;
  data?: any;
} 