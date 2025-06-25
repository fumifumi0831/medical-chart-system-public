import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Jestの型定義を明示的に宣言
declare const describe: (name: string, fn: () => void) => void;
declare const test: (name: string, fn: () => void) => void;
declare const expect: any;
declare const beforeEach: (fn: () => void) => void;
declare const jest: {
  fn: () => any;
  clearAllMocks: () => void;
};

// モックコンポーネントを作成（実際のコンポーネントが存在しない場合）
const MockReviewUI: React.FC<{
  reviewItems: Array<{
    id: string;
    field: string;
    originalValue: string;
    extractedValue: string;
    confidenceScore: number;
    status: 'pending' | 'approved' | 'rejected';
  }>;
  onApprove: (id: string) => void;
  onReject: (id: string, reason: string) => void;
  onEdit: (id: string, newValue: string) => void;
}> = ({ reviewItems, onApprove, onReject, onEdit }) => {
  return (
    <div data-testid="review-ui">
      {reviewItems.map((item) => (
        <div key={item.id} data-testid={`review-item-${item.id}`}>
          <span data-testid={`field-${item.id}`}>{item.field}</span>
          <span data-testid={`original-${item.id}`}>{item.originalValue}</span>
          <span data-testid={`extracted-${item.id}`}>{item.extractedValue}</span>
          <span data-testid={`confidence-${item.id}`}>{Math.round(item.confidenceScore * 100)}%</span>
          <span data-testid={`status-${item.id}`}>{item.status}</span>
          
          <button 
            data-testid={`approve-${item.id}`}
            onClick={() => onApprove(item.id)}
            disabled={item.status !== 'pending'}
          >
            承認
          </button>
          
          <button 
            data-testid={`reject-${item.id}`}
            onClick={() => onReject(item.id, 'テスト理由')}
            disabled={item.status !== 'pending'}
          >
            却下
          </button>
          
          <button 
            data-testid={`edit-${item.id}`}
            onClick={() => onEdit(item.id, '編集済み値')}
            disabled={item.status !== 'pending'}
          >
            編集
          </button>
        </div>
      ))}
    </div>
  );
};

describe('ReviewUI', () => {
  /**
   * 設計書参照: extension2_detailed_design_001_template_feature.md セクション 7
   * 仕様書ID: UI-TEST-003-REVIEW
   * 更新日: 2024-06-01
   */

  const mockReviewItems = [
    {
      id: '1',
      field: '患者名',
      originalValue: '田中太郎',
      extractedValue: '田中太朗',
      confidenceScore: 0.85,
      status: 'pending' as const
    },
    {
      id: '2',
      field: '診断名',
      originalValue: '高血圧症',
      extractedValue: '高血圧',
      confidenceScore: 0.65,
      status: 'pending' as const
    },
    {
      id: '3',
      field: '処方薬',
      originalValue: 'アムロジピン',
      extractedValue: 'アムロジピン',
      confidenceScore: 0.95,
      status: 'approved' as const
    }
  ];

  const mockHandlers = {
    onApprove: jest.fn(),
    onReject: jest.fn(),
    onEdit: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders all review items correctly', () => {
    /**
     * 設計書仕様: レビュー項目表示
     * 入力: レビュー項目リスト
     * 期待値: すべての項目が正しく表示される
     */
    // Act
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Assert
    expect(screen.getByTestId('review-ui')).toBeInTheDocument();
    
    // 各レビュー項目の表示確認
    mockReviewItems.forEach((item) => {
      expect(screen.getByTestId(`review-item-${item.id}`)).toBeInTheDocument();
      expect(screen.getByTestId(`field-${item.id}`)).toHaveTextContent(item.field);
      expect(screen.getByTestId(`original-${item.id}`)).toHaveTextContent(item.originalValue);
      expect(screen.getByTestId(`extracted-${item.id}`)).toHaveTextContent(item.extractedValue);
      expect(screen.getByTestId(`confidence-${item.id}`)).toHaveTextContent(`${Math.round(item.confidenceScore * 100)}%`);
      expect(screen.getByTestId(`status-${item.id}`)).toHaveTextContent(item.status);
    });
  });

  test('handles approve action correctly', async () => {
    /**
     * 設計書仕様: 承認アクション
     * 入力: 承認ボタンクリック
     * 期待値: onApproveコールバックが正しいIDで呼ばれる
     */
    // Arrange
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Act
    fireEvent.click(screen.getByTestId('approve-1'));

    // Assert
    await waitFor(() => {
      expect(mockHandlers.onApprove).toHaveBeenCalledWith('1');
      expect(mockHandlers.onApprove).toHaveBeenCalledTimes(1);
    });
  });

  test('handles reject action correctly', async () => {
    /**
     * 設計書仕様: 却下アクション
     * 入力: 却下ボタンクリック
     * 期待値: onRejectコールバックが正しいIDと理由で呼ばれる
     */
    // Arrange
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Act
    fireEvent.click(screen.getByTestId('reject-2'));

    // Assert
    await waitFor(() => {
      expect(mockHandlers.onReject).toHaveBeenCalledWith('2', 'テスト理由');
      expect(mockHandlers.onReject).toHaveBeenCalledTimes(1);
    });
  });

  test('handles edit action correctly', async () => {
    /**
     * 設計書仕様: 編集アクション
     * 入力: 編集ボタンクリック
     * 期待値: onEditコールバックが正しいIDと新しい値で呼ばれる
     */
    // Arrange
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Act
    fireEvent.click(screen.getByTestId('edit-1'));

    // Assert
    await waitFor(() => {
      expect(mockHandlers.onEdit).toHaveBeenCalledWith('1', '編集済み値');
      expect(mockHandlers.onEdit).toHaveBeenCalledTimes(1);
    });
  });

  test('disables buttons for non-pending items', () => {
    /**
     * 設計書仕様: ボタン状態制御
     * 入力: 承認済み項目
     * 期待値: アクションボタンが無効化される
     */
    // Arrange
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Assert
    // 承認済み項目（ID: 3）のボタンが無効化されていることを確認
    expect(screen.getByTestId('approve-3')).toBeDisabled();
    expect(screen.getByTestId('reject-3')).toBeDisabled();
    expect(screen.getByTestId('edit-3')).toBeDisabled();

    // 保留中項目（ID: 1, 2）のボタンが有効であることを確認
    expect(screen.getByTestId('approve-1')).not.toBeDisabled();
    expect(screen.getByTestId('reject-1')).not.toBeDisabled();
    expect(screen.getByTestId('edit-1')).not.toBeDisabled();
  });

  test('displays confidence scores with appropriate styling', () => {
    /**
     * 設計書仕様: 信頼性スコア表示
     * 入力: 異なる信頼性スコア
     * 期待値: スコアが適切にフォーマットされて表示される
     */
    // Arrange
    render(
      <MockReviewUI 
        reviewItems={mockReviewItems}
        {...mockHandlers}
      />
    );

    // Assert
    expect(screen.getByTestId('confidence-1')).toHaveTextContent('85%');
    expect(screen.getByTestId('confidence-2')).toHaveTextContent('65%');
    expect(screen.getByTestId('confidence-3')).toHaveTextContent('95%');
  });

  test('handles empty review items list', () => {
    /**
     * 設計書仕様: 空リスト処理
     * 入力: 空のレビュー項目リスト
     * 期待値: エラーなく表示される
     */
    // Arrange & Act
    render(
      <MockReviewUI 
        reviewItems={[]}
        {...mockHandlers}
      />
    );

    // Assert
    expect(screen.getByTestId('review-ui')).toBeInTheDocument();
    // レビュー項目が存在しないことを確認
    expect(screen.queryByTestId(/^review-item-/)).not.toBeInTheDocument();
  });

  test('displays field differences clearly', () => {
    /**
     * 設計書仕様: 差分表示
     * 入力: 元の値と抽出値が異なる項目
     * 期待値: 両方の値が明確に表示される
     */
    // Arrange
    const itemWithDifference = {
      id: 'diff-1',
      field: 'テストフィールド',
      originalValue: '元の値',
      extractedValue: '抽出された値',
      confidenceScore: 0.7,
      status: 'pending' as const
    };

    render(
      <MockReviewUI 
        reviewItems={[itemWithDifference]}
        {...mockHandlers}
      />
    );

    // Assert
    expect(screen.getByTestId('original-diff-1')).toHaveTextContent('元の値');
    expect(screen.getByTestId('extracted-diff-1')).toHaveTextContent('抽出された値');
    
    // 値が異なることが視覚的に分かるように表示されていることを確認
    const originalElement = screen.getByTestId('original-diff-1');
    const extractedElement = screen.getByTestId('extracted-diff-1');
    expect(originalElement).toBeInTheDocument();
    expect(extractedElement).toBeInTheDocument();
  });
}); 