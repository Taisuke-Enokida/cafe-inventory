# 開発ルール

## ブランチとレビュー

- 作業は `feature/<短い目的>` で行い、`develop` へのPRで統合確認する。
- リリースは `develop` から `main` へのPRとし、CI必須チェック成功後にマージする。
- `main` は本番リリースブランチ。直接push・force pushは禁止する運用をGitHub側で設定する。
- PRでは目的、影響範囲、マイグレーション、テスト結果を説明する。
- 開発環境で `pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push` を実行し、コミット前Ruff・push前pytestを有効化する。

## コード

- Python 3.12、Flask Application Factory、Blueprint、サービス層を使用する。
- RuffのLint・Formatを適用する。既存のスタイルに従い、不必要な抽象化を追加しない。
- UIはJinja2・HTML/CSS/JavaScriptのみとし、日本語表示・PC/タブレット対応を維持する。
- 入力値をサーバー側で検証し、エラーを利用者へ明示する。DB接続文字列や秘密をログへ出さない。

## データ・セキュリティ

- 台帳は追記専用、数量はDecimal/NUMERIC、在庫マイナス禁止、履歴と在庫反映は同一トランザクション。
- 同時入出庫ではPostgreSQL商品行ロック後に残高を再検証する。
- 認証とロールをサーバー側で検証し、CSRFを有効にする。パスワードを安全なハッシュで保存する。
- `.env` と本物の認証情報をコミットしない。`.env.example` はダミー値に限る。
- 本番の `SECRET_KEY` / `DATABASE_URL` は必須。DEBUGを無効化する。
- Neon本番データを使ったテスト、初期化、破壊的マイグレーションを禁止する。

## スキーマ・変更確認

- モデル変更にはFlask-Migrate/Alembicマイグレーションを付け、内容をレビューする。
- 本番マイグレーションは自動起動時に実行しない。破壊的変更は禁止し、承認後に段階的な互換変更を行う。
- 外部GitHub、Render、Neonの作成・変更、push/PR、本番DBへの書込み前に変更内容と影響を示して承認を得る。
- 既存ファイルや未コミット変更を確認し、無関係な変更を上書き・削除しない。
