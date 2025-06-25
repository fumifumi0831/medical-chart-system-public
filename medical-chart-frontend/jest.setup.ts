// Jest設定ファイル（TypeScript版）
import '@testing-library/jest-dom';

// Jestのグローバル型定義を拡張
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R;
      toHaveTextContent(text: string): R;
      toHaveClass(className: string): R;
      toBeVisible(): R;
      toBeDisabled(): R;
      toBeEnabled(): R;
      toBeChecked(): R;
      toBeRequired(): R;
      toHaveAttribute(attr: string, value?: string): R;
      toHaveFocus(): R;
      toHaveStyle(style: Record<string, any>): R;
      toHaveValue(value: string | string[] | number): R;
    }
  }
}

// グローバルなモック設定やその他のセットアップをここに追加できます 