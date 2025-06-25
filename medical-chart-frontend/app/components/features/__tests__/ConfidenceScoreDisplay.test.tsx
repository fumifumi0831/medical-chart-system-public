import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConfidenceScoreDisplay from '@/components/features/ConfidenceScoreDisplay';

// Jestの型定義を明示的に宣言
declare const describe: (name: string, fn: () => void) => void;
declare const test: (name: string, fn: () => void) => void;
declare const expect: any;

describe('ConfidenceScoreDisplay', () => {
  /**
   * 設計書参照: extension3_adr_001_combined_confidence_score.md セクション 4
   * 仕様書ID: UI-TEST-001-CONFIDENCE
   * 更新日: 2024-06-01
   */
  
  test('renders all confidence scores correctly', () => {
    /**
     * 設計書仕様: 信頼性スコア表示
     * 入力: すべての信頼性スコア値
     * 期待値: すべてのスコアが正しく表示される
     */
    // Arrange
    const combinedScore = 0.82;
    const levenshteinScore = 0.75;
    const semanticScore = 0.89;
    
    // Act
    render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={levenshteinScore}
        semanticScore={semanticScore}
        needsReview={false}
      />
    );
    
    // Assert
    expect(screen.getByText('82%')).toBeInTheDocument(); // Combined score
    expect(screen.getByText('75%')).toBeInTheDocument(); // Levenshtein score
    expect(screen.getByText('89%')).toBeInTheDocument(); // Semantic score
  });
  
  test('displays appropriate color for high confidence score', () => {
    /**
     * 設計書仕様: 信頼性スコア - 高信頼性表示
     * 入力: 高い信頼性スコア（0.8以上）
     * 期待値: 緑色で表示される
     */
    // Arrange
    const combinedScore = 0.85;
    
    // Act
    const { container } = render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.9}
        semanticScore={0.8}
        needsReview={false}
      />
    );
    
    // Assert
    const scoreElement = container.querySelector('.text-green-600');
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement).toHaveTextContent('85%');
  });

  test('displays appropriate color for medium confidence score', () => {
    /**
     * 設計書仕様: 信頼性スコア - 中信頼性表示
     * 入力: 中程度の信頼性スコア（0.6~0.8）
     * 期待値: 黄色で表示される
     */
    // Arrange
    const combinedScore = 0.71;
    
    // Act
    const { container } = render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.65}
        semanticScore={0.77}
        needsReview={false}
      />
    );
    
    // Assert
    const scoreElement = container.querySelector('.text-yellow-600');
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement).toHaveTextContent('71%');
  });

  test('displays appropriate color for low confidence score', () => {
    /**
     * 設計書仕様: 信頼性スコア - 低信頼性表示
     * 入力: 低い信頼性スコア（0.6未満）
     * 期待値: 赤色で表示される
     */
    // Arrange
    const combinedScore = 0.45;
    
    // Act
    const { container } = render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.4}
        semanticScore={0.5}
        needsReview={true}
      />
    );
    
    // Assert
    const scoreElement = container.querySelector('.text-red-600');
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement).toHaveTextContent('45%');
  });
  
  test('displays needs review warning when needed', () => {
    /**
     * 設計書仕様: 要確認表示
     * 入力: 要確認フラグがtrue
     * 期待値: 要確認の警告が表示される
     */
    // Arrange
    const combinedScore = 0.68;
    const needsReview = true;
    
    // Act
    render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.55}
        semanticScore={0.75}
        needsReview={needsReview}
      />
    );
    
    // Assert
    expect(screen.getByText(/要確認/i)).toBeInTheDocument();
    expect(screen.getByTestId('warning-icon')).toBeInTheDocument();
  });
  
  test('does not display needs review warning when not needed', () => {
    /**
     * 設計書仕様: 要確認表示なし
     * 入力: 要確認フラグがfalse
     * 期待値: 要確認の警告が表示されない
     */
    // Arrange
    const combinedScore = 0.90;
    const needsReview = false;
    
    // Act
    render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.92}
        semanticScore={0.88}
        needsReview={needsReview}
      />
    );
    
    // Assert
    expect(screen.queryByText(/要確認/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('warning-icon')).not.toBeInTheDocument();
  });
  
  test('displays tooltip with detailed information on hover', () => {
    /**
     * 設計書仕様: 詳細情報ツールチップ
     * 入力: ホバーアクション
     * 期待値: 詳細情報を含むツールチップが表示される
     */
    // Arrange
    const combinedScore = 0.75;
    
    // Act
    render(
      <ConfidenceScoreDisplay 
        combinedScore={combinedScore}
        levenshteinScore={0.7}
        semanticScore={0.8}
        needsReview={false}
      />
    );
    
    // Assert
    // ツールチップの要素が存在するか確認
    expect(screen.getByTestId('confidence-tooltip')).toBeInTheDocument();
    // 詳細スコア情報が含まれるか確認
    const tooltipContent = screen.getByTestId('confidence-tooltip').getAttribute('data-tooltip-content');
    expect(tooltipContent).toContain('見た目の類似度');
    expect(tooltipContent).toContain('意味的類似度');
  });
}); 