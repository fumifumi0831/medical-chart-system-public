// Jest設定ファイル
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // next.config.jsとパッケージディレクトリへのパスを設定
  dir: './'
});

// Jestに渡すカスタム設定
const customJestConfig = {
  // テストが実行されるディレクトリを追加
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    // モジュールエイリアスのマッピング（tsconfig.jsonのpathsと一致させる）
    '^@/app/(.*)$': '<rootDir>/app/$1',
    '^@/components/(.*)$': '<rootDir>/app/components/$1',
    '^@/lib/(.*)$': '<rootDir>/app/lib/$1',
    '^@/styles/(.*)$': '<rootDir>/app/styles/$1'
  }
};

// createJestConfigは、next/jestが非同期でNext.js設定を読み込むために
// エクスポートするasync関数です
module.exports = createJestConfig(customJestConfig); 