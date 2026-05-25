# Headless Calendar Step 1

ヘッドレス思想のカレンダー／スケジュール管理アプリの最小構成です。

## ステップ1でできること

- メンバー管理
- 予定種類管理
- draft作成
- draft検証
- draft承認
- 正式予定登録
- 月間予定表表示
- ローテーションログ出力

## ステップ1で作らないもの

- ログイン
- SSO
- usersテーブル
- 所属管理
- 定員管理
- Dify連携
- Excel取込
- 音声入力
- Outlook / Google / タイムツリー同期

## 起動方法

`.env` の `POSTGRES_PASSWORD` と `DATABASE_URL` のパスワード部分を同じ値に修正してください。

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

- `/calendar` 月間予定表
- `/masters` メンバー・予定種類の簡易管理
- `/drafts` draft確認・承認

## API

主要APIは以下です。

- `GET /api/calendar/members`
- `POST /api/calendar/members`
- `GET /api/calendar/event-types`
- `POST /api/calendar/event-types`
- `POST /api/calendar/drafts`
- `GET /api/calendar/drafts`
- `POST /api/calendar/drafts/{draft_id}/validate`
- `POST /api/calendar/drafts/{draft_id}/approve`
- `POST /api/calendar/drafts/{draft_id}/reject`
- `GET /api/calendar/events/monthly`

詳細は `docs/api.md` を参照してください。

## DB

ステップ1では以下の5テーブルを作成します。

- `calendar_members`
- `calendar_event_types`
- `calendar_event_drafts`
- `calendar_events`
- `audit_logs`

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
