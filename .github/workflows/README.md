# GitHub Actions ワークフロー設定

このディレクトリには、医療カルテシステムのCI/CDワークフローが含まれています。

## バックエンドデプロイワークフロー (backend-deploy.yml)

このワークフローは、バックエンドアプリケーションをGoogle Cloud Runにデプロイします。

### トリガー

- `main`または`develop`ブランチへのプッシュ（`medical-chart-backend/`ディレクトリ内のファイル変更時）
- 手動トリガー（GitHub UI上のワークフロー実行ボタン）

### 機能

1. コードのチェックアウト
2. ブランチに基づく環境変数の設定（`main`ブランチ → 本番環境、それ以外 → 開発環境）
3. Google Cloud認証
4. バックエンドのDockerイメージのビルドとプッシュ
5. Cloud Runへのデプロイ
6. データベースマイグレーションの実行

## 必要なシークレット

このワークフローを使用するには、以下のGitHubシークレットを設定する必要があります：

1. `GCP_SA_KEY` - GCPサービスアカウントのJSONキー
2. `GCP_PROJECT_ID` - デプロイ先のGCPプロジェクトID

### 権限要件

サービスアカウントには以下の権限が必要です：

- Cloud Run Admin (`roles/run.admin`)
- Cloud Build Editor (`roles/cloudbuild.builds.editor`)
- Cloud SQL Client (`roles/cloudsql.client`)
- Storage Object Admin (`roles/storage.objectAdmin`)
- Artifact Registry Writer (`roles/artifactregistry.writer`)
- Secret Manager Secret Accessor (`roles/secretmanager.secretAccessor`)

## シークレットの設定手順

1. GitHubリポジトリの「Settings」タブに移動
2. 左側のメニューから「Secrets and variables」→「Actions」を選択
3. 「New repository secret」ボタンをクリック
4. 必要なシークレットを追加

### GCP_SA_KEY の設定方法

1. GCPコンソールで、IAMとアドミン > サービスアカウントに移動
2. ワークフロー用のサービスアカウントを選択（または新規作成）
3. 「キー」タブを選択し、「鍵を追加」→「新しい鍵を作成」をクリック
4. JSONを選択して「作成」をクリック
5. ダウンロードされたJSONファイルの内容をそのままGitHubシークレットとして設定

## 事前準備

以下のGCPリソースが既に作成されていることを確認してください：

1. Artifact Registryリポジトリ (`medical-charts-repo-dev` および/または `medical-charts-repo-prod`)
2. Cloud SQLインスタンス
3. シークレットマネージャーに以下のシークレットが設定されていること：
   - `db-connection-string-dev` (または `-prod`)
   - `api-key-dev` (または `-prod`)
   - `gemini-api-key-dev` (または `-prod`)
4. 適切な権限を持つサービスアカウント

これらが設定されていない場合は、READMEの「環境設定手順」セクションを参照して設定してください。 