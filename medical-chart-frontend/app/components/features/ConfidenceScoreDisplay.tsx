import React from 'react';

interface ConfidenceScoreDisplayProps {
  combinedScore: number;
  levenshteinScore: number;
  semanticScore: number;
  needsReview: boolean;
}

/**
 * 信頼性スコア表示コンポーネント
 * 設計書参照: extension3_adr_001_combined_confidence_score.md セクション 4
 */
const ConfidenceScoreDisplay: React.FC<ConfidenceScoreDisplayProps> = ({
  combinedScore,
  levenshteinScore,
  semanticScore,
  needsReview
}) => {
  // スコアに基づいて表示色を決定
  const getScoreColorClass = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  // パーセント表示に変換
  const formatScore = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };

  // ツールチップの内容
  const tooltipContent = `
    見た目の類似度: ${formatScore(levenshteinScore)}
    意味的類似度: ${formatScore(semanticScore)}
    総合信頼度: ${formatScore(combinedScore)}
  `;

  return (
    <div className="flex items-center space-x-2">
      <div className="flex flex-col">
        <span 
          className={`font-medium ${getScoreColorClass(combinedScore)}`}
        >
          {formatScore(combinedScore)}
        </span>
        <div className="flex text-xs text-gray-500 space-x-2">
          <span>{formatScore(levenshteinScore)}</span>
          <span>{formatScore(semanticScore)}</span>
        </div>
      </div>
      
      <div 
        data-testid="confidence-tooltip"
        data-tooltip-content={tooltipContent}
        className="cursor-help relative group"
      >
        <span className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs">
          ?
        </span>
        <div className="absolute hidden group-hover:block bottom-full left-1/2 transform -translate-x-1/2 mb-2 p-2 bg-gray-800 text-white text-xs rounded z-10 w-48">
          {tooltipContent}
        </div>
      </div>

      {needsReview && (
        <div className="flex items-center text-yellow-600">
          <svg 
            data-testid="warning-icon"
            xmlns="http://www.w3.org/2000/svg" 
            className="h-5 w-5 mr-1" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
            />
          </svg>
          <span>要確認</span>
        </div>
      )}
    </div>
  );
};

export default ConfidenceScoreDisplay; 