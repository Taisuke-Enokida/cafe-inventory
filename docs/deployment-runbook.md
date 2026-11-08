# デプロイ・運用ランブック

## ブランチとGitHub

1. GitHubにリポジトリを用意し、`main` をリリースブランチ、`develop` を統合ブランチとする。日常作業は `feature/*` からPRで行う。
2. GitHub Actions のCIワークフローと必要なチェック名を確認し、`main` にPR必須・必須status check・force push禁止・削除禁止を設定する。`develop` にも必要に応じ同様の保護を行う。
3. `gh auth status` でCLI認証を確認できる。リポジトリの作成、remote追加、push、PR作成・マージはリモート状態を変更するため、実行前にユーザー承認を得る。
4. GitHub設定は権限があればWeb UIまたは `gh api` で設定可能。利用者に権限がない場合は、リポジトリ Settings → Rules → Rulesets / Branch protection rules で設定する。

## GitHub Actions

CIはPython環境、requirements、Ruff、SQLite pytest、PostgreSQLサービス統合テストを実行する。`main` のPRに必須チェックを設定し、CI成功前のマージを防ぐ。Neon、本番シークレットはCIへ渡さない。

## Neon

1. ユーザー承認後にNeonプロジェクト/ブランチ/DBを作成し、費用・リージョン・バックアップ等の条件を確認する。
2. Neonの接続文字列をRenderの `DATABASE_URL` Secretとして設定する。ソース、ログ、CIへ記録しない。
3. SQLAlchemyのPostgreSQL接続でSSLを必須にする。接続URLのドライバー接頭辞をアプリが対応する形式へ正規化する。
4. 本番マイグレーションは差分をレビューし、後方互換性とバックアップ/復旧手順を確認後に、個別の承認を得て実行する。自動初期化・テストデータ投入・破壊的変更は禁止する。

## Render

`render.yaml` はWeb Service（Python）、`main`、`pip install -r requirements.txt`、`gunicorn wsgi`、`/health` を定義し、秘密値を含めない。`autoDeploy: false` を初期値にしてCI未確認の自動リリースを防ぐ。Neon DBはBlueprintで作成せず、外部接続値をRender環境変数として手動登録する。

Render公式のデプロイ資料は、Git接続サービスの自動デプロイ方式に「After CI Checks Pass」を案内している。Blueprintの設定だけに依存せず、Render Dashboardで対象サービスのBranchを `main`、Auto-Deployを **After CI Checks Pass** に設定し、GitHub Actionsのチェックが検出されることを確認する。CIチェックがない場合はRenderがデプロイを起動しないため、初回接続時に必ず検証する。参照: [Render Blueprint specification](https://render.com/docs/blueprint-spec)、[Render deploys / CI integration](https://render.com/docs/deploys)。

1. ユーザー承認後にGitHub連携サービスを作成する。プラン・費用・無料枠の制約を事前に確認する。サービス作成時は自動デプロイを無効のままにする。
2. Build Commandは `pip install -r requirements.txt`、Start Commandは `gunicorn wsgi`、Health Check Pathは `/health` とする。
3. `SECRET_KEY` と `DATABASE_URL` を秘密の環境変数として設定する。本番 `FLASK_DEBUG` は無効にする。
4. GitHub Actionsのチェックが検出されることを確認してから、DashboardでAuto-Deployを **After CI Checks Pass** に変更する。初回デプロイと本番URLのログイン・在庫操作は、費用と本番データへの影響を提示し承認を得てから行う。実在庫を使うテストデータを無断で作らない。

## リリース・ロールバック

1. `develop` の検証済みコミットから `main` 向けPRを作り、必須CIとレビューを通す。
2. マイグレーションがある場合はSQL/差分、後方互換性、バックアップ、復旧方法を事前確認し、本番変更の承認を得る。
3. RenderがCI通過後に `main` のコミットをデプロイしたことと `/health` を確認する。
4. 不具合時は既知の正常なアプリコミットへ戻す。DBスキーマの逆戻しやデータ破壊を自動で行わず、別途影響評価と承認を得る。

## 現状の未実施事項

GitHubには `cafe-inventory` private repository を作成し、`main`、`develop`、`feature/initial-inventory` をpush済み。初回CIは3ブランチ全て成功した。ブランチ保護APIとrulesets APIは、private repositoryへの適用にGitHub Proが必要という403応答で拒否された。公開化は行っていないため、現状はmain/developのPR必須・CI必須をGitHub側で強制できていない。GitHub Proへの変更または公開化の承認後に設定する。公開化はソースと履歴を全公開するため、明示承認なしに行わない。

Neonプロジェクト作成/接続、本番マイグレーション、Renderサービス作成/費用発生、本番URL検証は未実施。これらは個別に内容と影響を提示し、ユーザー承認後に実施する。
