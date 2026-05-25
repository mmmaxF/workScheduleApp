# API仕様

## 共通レスポンス

成功時:

```json
{
  "ok": true,
  "data": {},
  "message": "処理が完了しました"
}
```

失敗時:

```json
{
  "ok": false,
  "error_code": "VALIDATION_ERROR",
  "message": "入力内容に不備があります",
  "details": [],
  "suggestion": "修正方法の提案"
}
```

## メンバーAPI

### GET /api/calendar/members

メンバー一覧を取得します。

### POST /api/calendar/members

メンバーを作成します。

```json
{
  "display_name": "Aさん",
  "short_name": "A",
  "display_order": 1
}
```

### PUT /api/calendar/members/{member_id}

メンバーを更新します。

### POST /api/calendar/members/{member_id}/archive

メンバーを無効化します。

## 予定種類API

### GET /api/calendar/event-types

予定種類一覧を取得します。

### POST /api/calendar/event-types

予定種類を作成します。

```json
{
  "code": "rd",
  "name": "RD",
  "short_label": "RD",
  "display_color": "#dbeafe",
  "display_symbol": "",
  "is_leave": false,
  "is_work_assignment": true,
  "requires_capacity_check": true,
  "display_order": 1
}
```

## draft API

### POST /api/calendar/drafts

draftを作成します。

```json
{
  "member_name_raw": "Aさん",
  "member_id": 1,
  "event_date": "2026-06-01",
  "event_type_name_raw": "RD",
  "event_type_id": 1,
  "title": "RD",
  "display_label": "RD",
  "memo": "",
  "source_type": "manual",
  "source_text": "画面から手入力"
}
```

### POST /api/calendar/drafts/{draft_id}/validate

draftを検証します。

ステップ1の検証内容:

- メンバー存在チェック
- 予定種類存在チェック
- 日付チェック
- 同一メンバー・同日・同一予定種類の重複チェック

### POST /api/calendar/drafts/{draft_id}/approve

draftを承認し、正式予定 `calendar_events` に登録します。

### POST /api/calendar/drafts/{draft_id}/reject

draftを却下します。

## 月間表示API

### GET /api/calendar/events/monthly?year=2026&month=6

月間予定表用データを取得します。
