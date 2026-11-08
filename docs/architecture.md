# システム設計

## 構成

```mermaid
flowchart LR
  Browser["PC / Tablet Browser<br/>HTML, CSS, JavaScript"]
  GH["GitHub<br/>feature/* → develop → main"]
  CI["GitHub Actions<br/>Ruff / pytest / temporary PostgreSQL"]
  Render["Render Web Service<br/>Flask + Gunicorn"]
  Neon["Neon PostgreSQL<br/>Production data"]
  Local["VS Code local<br/>Flask + SQLite"]
  Browser -->|HTTPS| Render
  Local -->|development| SQLite[(SQLite)]
  GH --> CI
  CI -->|required checks| GH
  GH -->|main after CI| Render
  Render -->|DATABASE_URL + SSL| Neon
```

本番の秘密値はRenderの環境変数だけに置く。自動デプロイはGitHub Actionsのチェック成功後に限定する。DBマイグレーションはWebプロセス起動時に暗黙実行せず、承認済みのリリース操作として行う。

## アプリケーション層

- Application Factory が設定、SQLAlchemy、Migrate、ログイン管理、CSRFを初期化する。
- Routes は入力検証、認証・権限検査、サービス呼出し、画面応答を担う。
- Services は在庫操作・トランザクション境界・残高制約を担う。
- Models はユーザー、商品、追記専用在庫移動を定義する。
- Templates / static はJinja2と通常のHTML/CSS/JavaScriptを使う。追加フロントエンドフレームワークは採用しない。

## 画面遷移

```mermaid
flowchart TD
  Start["アクセス"] --> Auth{"ログイン済み?"}
  Auth -->|いいえ| Login["ログイン"]
  Login -->|成功| Inventory["在庫一覧"]
  Auth -->|はい| Inventory
  Inventory --> Search["検索 / 発注アラート"]
  Inventory --> History["入出庫履歴"]
  Inventory --> Receipt["入庫登録"]
  Inventory --> Issue["使用・廃棄登録"]
  Inventory --> Product["商品一覧"]
  Product -->|管理者| Edit["商品登録・編集・有効化切替"]
  Product -->|スタッフ| Forbidden["権限不足"]
  Inventory --> Logout["ログアウト"]
  History --> Correction["訂正記録（理由必須）"]
```

## 入出庫フロー

```mermaid
flowchart TD
  Request["認証・CSRF確認"] --> Validate["商品・種別・正のDecimal数量を検証"]
  Validate --> Begin["DBトランザクション開始"]
  Begin --> Lock["PostgreSQL: 商品行をFOR UPDATEでロック"]
  Lock --> Balance["台帳からロック後の残高を再計算"]
  Balance --> Enough{"差引後在庫は0以上?"}
  Enough -->|いいえ| Rollback["ロールバックし不足エラー"]
  Enough -->|はい| Append["追記専用台帳行を追加"]
  Append --> Commit["コミット"]
  Commit --> Response["成功応答・更新後在庫"]
```

SQLiteはローカル単体テスト用であり、PostgreSQLの行ロック意味論を再現しない。実際の同時出庫テストはCIのPostgreSQLサービスで実行する。PostgreSQLの行ロックはトランザクション内で保持し、残高読取はロック取得後に行う。
