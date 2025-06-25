# 医療カルテ抽出システム - フロントエンド

## 概要

このプロジェクトは医療カルテ画像をアップロードし、Google Gemini 2.5 Pro APIを使用して診療情報を抽出・構造化するシステムのフロントエンドアプリケーションです。Next.jsを使用して実装されています。

## 技術スタック

- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Tailwind CSS - スタイリング
- Axios - API通信

## 機能

- カルテ画像アップロード
- 処理状態表示
- 抽出結果表示
- CSVダウンロード

## 開発環境セットアップ

### 1. 前提条件

- Node.js 18以上
- npm または yarn または pnpm

### 2. 環境変数設定

各環境に応じて以下の環境変数を設定してください：

#### 開発環境での設定方法

1. ローカル開発環境では、プロジェクトルートに `.env.local` ファイルを作成：

```
API_BASE_URL=http://localhost:8000/api/v1
```

2. 開発サーバー環境では、デプロイ設定で環境変数を設定：

```
API_BASE_URL=https://medical-chart-backend-dev-372468689123.asia-northeast1.run.app/api/v1
```

3. 本番環境では、本番デプロイ設定で環境変数を設定：

```
API_BASE_URL=https://production-backend-url.example.com/api/v1
```

※ ビルド時に環境変数が埋め込まれるため、環境変数を変更した場合は再ビルドとデプロイが必要です

### 3. 依存関係インストール

```bash
npm install
# または
yarn install
# または
pnpm install
```

### 4. 開発サーバー起動

```bash
npm run dev
# または
yarn dev
# または
pnpm dev
```

アプリケーションは`http://localhost:3000`で起動します。

## ビルドと本番環境用デプロイ

```bash
# ビルド
npm run build
# または
yarn build
# または
pnpm build

# 本番環境サーバー起動
npm run start
# または
yarn start
# または
pnpm start
```

## プロジェクト構成

```
medical-chart-frontend/
├── app/                # App Router ディレクトリ
│   ├── components/     # コンポーネント
│   │   ├── common/     # 共通コンポーネント
│   │   └── features/   # 機能別コンポーネント
│   ├── hooks/          # カスタムフック
│   ├── lib/            # ユーティリティとAPI
│   ├── providers/      # コンテキストプロバイダー
│   ├── store/          # 状態管理
│   ├── styles/         # スタイル定義
│   ├── layout.tsx      # レイアウト
│   └── page.tsx        # メインページ
├── public/             # 静的ファイル
└── tests/              # テストコード
```

## APIエンドポイント

バックエンドAPIの詳細については、バックエンドのREADMEを参照してください。主なエンドポイント：

- `POST /api/v1/charts` - カルテ画像アップロードと処理開始
- `GET /api/v1/charts/{chart_id}/status` - 処理ステータス確認
- `GET /api/v1/charts/{chart_id}` - 処理結果（抽出テキスト）取得
- `GET /api/v1/charts/{chart_id}/csv` - 抽出結果をCSV形式でダウンロード 