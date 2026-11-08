# 喫茶店 在庫管理アプリ

Flask を中心にした、喫茶店向けの在庫管理 MVP です。日本語のレスポンシブ画面から商品、入庫、使用、廃棄、在庫履歴を管理します。

## 技術構成

- Python 3.12 / Flask / Jinja2
- Flask-SQLAlchemy / Flask-Migrate / Alembic
- 開発・単体テスト: SQLite
- 本番: Neon PostgreSQL（`DATABASE_URL` 経由）
- テスト: pytest / PostgreSQL 統合テストは GitHub Actions の一時サービス
- 品質管理: Ruff / pre-commit
- 本番サーバー: Gunicorn / Render

詳細は [docs/requirements.md](docs/requirements.md)、[docs/architecture.md](docs/architecture.md)、[docs/database-design.md](docs/database-design.md) を参照してください。AI エージェントを含む開発参加者は [AGENTS.md](AGENTS.md) と [docs/development-rules.md](docs/development-rules.md) に従ってください。

## ローカル開発

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
flask --app wsgi db upgrade
flask --app wsgi run
```

ローカル既定値は SQLite の `instance/inventory.db` です。ローカル初回の管理者は `flask --app wsgi create-admin`、スタッフは `flask --app wsgi create-staff` で作成してください。パスワードは対話入力し、ソースやコマンド履歴に含めないでください。

## テストとコード品質

```bash
pytest
ruff check .
ruff format --check .
```

PostgreSQL 固有テストは `TEST_DATABASE_URL` のみを対象にします。CI は一時 PostgreSQL サービスを使用します。本番 Neon のURLをテスト設定に使ってはいけません。詳細は [docs/testing-policy.md](docs/testing-policy.md) を参照してください。

## デプロイ概要

`feature/*` → `develop` → Pull Request → `main` の順に統合します。GitHub Actions の必須チェックが成功した `main` の変更を Render にデプロイする構成です。本番 `DATABASE_URL` と `SECRET_KEY` は Render の Secret Files / 環境変数画面で設定し、リポジトリには保存しません。Render の自動デプロイを「After CI Checks Pass」に設定し、Neon のマイグレーションは承認されたリリース手順で明示的に実行します。

環境構築、GitHub ブランチ保護、Neon、Render の手順と未実施の外部操作は [docs/deployment-runbook.md](docs/deployment-runbook.md) に記載しています。外部リソースの作成・変更や本番DBへの接続は、事前承認なしに実行しないでください。
