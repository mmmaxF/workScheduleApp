# Headless Calendar Step 2

ヘッドレス思想のカレンダー／スケジュール管理アプリです。

## ステップ2でできること

- メンバー管理
- 予定種類管理
- 所属管理（映像、音声、調整、照明、回線）
- メンバーの複数所属設定
- 予定種類ごとの定員ルール管理
- 予定登録（フリーテキスト予定名・定員チェック・重複チェック付き）
- 月間予定表表示（所属フィルタ対応・定員状況表示）
- ローテーションログ出力
- CSVインポート／エクスポート
- **AIアシスタントチャット（Dify連携）**
- **AI参照API（DifyからDB情報を安全に取得）**
- **開発者用DBビューアー**

## ステップ2で作らないもの

- ログイン
- SSO
- usersテーブル
- draft機能（直接予定登録のみ）
- 音声入力
- Outlook / Google / タイムツリー同期

## 起動方法

`.env` の以下の設定を確認してください：

- `POSTGRES_PASSWORD` と `DATABASE_URL` のパスワード部分を同じ値に修正
- **AI機能を使用する場合、以下を追加:**
  - `AI_READ_API_KEY`: DifyからAI参照APIを呼ぶための読み取り専用APIキー
  - `DIFY_CHAT_API_URL`: Dify Chat APIのURL（例: https://api.dify.ai/v1/chat-messages）
  - `DIFY_CHAT_API_KEY`: Dify Chat APIのキー
- **開発者用DBビューアーを使用する場合、以下を追加:**
  - `DEV_API_KEY`: 開発者用APIキー

```bash
chmod +x start.sh
./start.sh
```

起動後、以下へアクセスします。

```text
Web UI: http://localhost:8000/calendar
API docs: http://localhost:8000/docs
```

## 画面

- `/calendar` 月間予定表（所属フィルタ対応・定員状況表示）
- `/masters` メンバー・予定種類・所属・定員ルールの簡易管理
- `/dev/db-viewer` 開発者用DBビューアー

## API

主要APIは以下です。

### メンバーAPI
- `GET /api/calendar/members`
- `POST /api/calendar/members`
- `PUT /api/calendar/members/{member_id}`
- `POST /api/calendar/members/{member_id}/archive`

### 予定種類API
- `GET /api/calendar/event-types`
- `POST /api/calendar/event-types`
- `PUT /api/calendar/event-types/{event_type_id}`
- `POST /api/calendar/event-types/{event_type_id}/archive`

### 所属API
- `GET /api/calendar/departments`
- `POST /api/calendar/departments`
- `PUT /api/calendar/departments/{department_id}`
- `POST /api/calendar/departments/{department_id}/archive`

### メンバー所属API
- `GET /api/calendar/members/{member_id}/departments`
- `PUT /api/calendar/members/{member_id}/departments`

### 定員ルールAPI
- `GET /api/calendar/capacity-rules`
- `POST /api/calendar/capacity-rules`
- `PUT /api/calendar/capacity-rules/{rule_id}`
- `POST /api/calendar/capacity-rules/{rule_id}/archive`

### 予定API
- `GET /api/calendar/events`
- `POST /api/calendar/events`（フリーテキスト予定名・定員チェック・重複チェック付き）
- `POST /api/calendar/events/{event_id}/archive`

### CSVインポート／エクスポートAPI
- `POST /api/calendar/imports/csv/preview`
- `POST /api/calendar/imports/csv/execute`
- `GET /api/calendar/exports/csv`

### AI参照API（Dify連携用）
- `GET /api/ai/calendar/capabilities` - 利用可能な参照ツール一覧
- `POST /api/ai/calendar/query` - 単一参照ツール実行
- `POST /api/ai/calendar/query-batch` - 複数参照ツール一括実行

### チャットAPI
- `POST /api/chat/dify-proxy` - UIからDifyへのプロキシ

### 開発者用API
- `GET /api/dev/tables` - 全テーブル一覧
- `GET /api/dev/tables/{table_name}` - テーブルデータ取得

### 月間表示API
- `GET /api/calendar/events/monthly?year=2026&month=6&department_id=1`

詳細は `docs/api.md` を参照してください。

AI連携の詳細は `docs/dify_chat.md` と `docs/ai_reference_api.md` を参照してください。

## DB

ステップ2では以下の11テーブルを作成します。

- `calendar_members`
- `calendar_event_types`
- `calendar_events`
- `audit_logs`
- `departments`
- `calendar_member_departments`
- `calendar_event_type_capacity_rules`
- `studios`
- `programs`
- `program_schedules`

詳細は `docs/database.md` を参照してください。

## ログ

アプリログは以下に出力されます。

```text
logs/app.log
```

ログはローテーションされます。

## 注意点

`.env.example` は作成していません。  
`.env` に `要設定_` が残っている場合、`start.sh` は起動を止めます。
