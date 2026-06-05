# API仕様

## API一覧

### メンバーAPI
- GET /api/calendar/members
- POST /api/calendar/members
- PUT /api/calendar/members/{member_id}
- POST /api/calendar/members/{member_id}/archive

### 予定種類API
- GET /api/calendar/event-types
- POST /api/calendar/event-types
- PUT /api/calendar/event-types/{event_type_id}
- POST /api/calendar/event-types/{event_type_id}/archive

### 所属API
- GET /api/calendar/departments
- POST /api/calendar/departments
- PUT /api/calendar/departments/{department_id}
- POST /api/calendar/departments/{department_id}/archive

### メンバー所属API
- GET /api/calendar/members/{member_id}/departments
- PUT /api/calendar/members/{member_id}/departments

### 定員ルールAPI
- GET /api/calendar/capacity-rules
- POST /api/calendar/capacity-rules
- PUT /api/calendar/capacity-rules/{rule_id}
- POST /api/calendar/capacity-rules/{rule_id}/archive

### 予定API
- GET /api/calendar/events
- POST /api/calendar/events
- POST /api/calendar/events/{event_id}/archive
- POST /api/calendar/events/bulk
- GET /api/calendar/events/monthly

### 番組スケジュールAPI
- POST /api/calendar/program-schedules/bulk

### 履歴イベントAPI
- GET /api/calendar/history-events
- POST /api/calendar/history-events/archive

### 履歴集計API
- GET /api/calendar/history-aggregations
- POST /api/calendar/history-aggregations/update

### 開発者用API
- GET /api/dev/tables
- GET /api/dev/tables/{table_name}

### CSVインポート／エクスポートAPI
- POST /api/calendar/imports/csv/preview
- POST /api/calendar/imports/csv/execute
- GET /api/calendar/exports/csv

### 検索API
- GET /api/calendar/search
- GET /api/calendar/search/programs

### AI参照API（Dify連携用）
- GET /api/ai/calendar/capabilities
- POST /api/ai/calendar/query
- POST /api/ai/calendar/query-batch

### チャットAPI
- POST /api/chat/dify-proxy

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

### PUT /api/calendar/event-types/{event_type_id}

予定種類を更新します。

### POST /api/calendar/event-types/{event_type_id}/archive

予定種類を無効化します。

## 所属API

### GET /api/calendar/departments

所属一覧を取得します。

### POST /api/calendar/departments

所属を作成します。

```json
{
  "name": "映像",
  "code": "video",
  "display_order": 1
}
```

### PUT /api/calendar/departments/{department_id}

所属を更新します。

### POST /api/calendar/departments/{department_id}/archive

所属を無効化します。

## メンバー所属API

### GET /api/calendar/members/{member_id}/departments

メンバーの所属一覧を取得します。

### PUT /api/calendar/members/{member_id}/departments

メンバーの所属を更新します。

```json
{
  "department_ids": [1, 2, 3]
}
```

## 定員ルールAPI

### GET /api/calendar/capacity-rules

定員ルール一覧を取得します。

### POST /api/calendar/capacity-rules

定員ルールを作成します。

```json
{
  "event_type_id": 1,
  "department_id": null,
  "day_type": "weekday",
  "required_count": 1
}
```

`day_type` は `weekday`（平日）、`weekend`（週末）、`all`（全日）のいずれかを指定します。  
`department_id` は `null` で全所属を対象にします。

### PUT /api/calendar/capacity-rules/{rule_id}

定員ルールを更新します。

### POST /api/calendar/capacity-rules/{rule_id}/archive

定員ルールを無効化します。

## 予定API

### GET /api/calendar/events

正式予定一覧を取得します。

### POST /api/calendar/events

正式予定を作成します。

検証内容:

- メンバー存在チェック
- 予定種類存在チェック（`event_type_id` が指定されている場合のみ）
- 同一メンバー・同日・同一予定種類の重複チェック（`event_type_id` が指定されている場合）
- 同一メンバー・同日・同一予定名の重複チェック（`event_type_id` が null の場合）
- 定員チェック（`event_type_id` が指定され、かつ `requires_capacity_check=true` の予定種類の場合）

フリーテキスト予定（`event_type_id` が null）の例:

```json
{
  "member_id": 1,
  "event_date": "2026-06-01",
  "event_type_id": null,
  "title": "急きょ対応",
  "display_label": "急きょ対応",
  "memo": "午後のみ"
}
```

マスタ紐づき予定（`event_type_id` が指定）の例:

```json
{
  "member_id": 1,
  "event_date": "2026-06-01",
  "event_type_id": 1,
  "title": "RD",
  "display_label": "RD",
  "memo": ""
}
```

定員チェックエラー時:

```json
{
  "ok": false,
  "error_code": "INSUFFICIENT_CAPACITY",
  "message": "定員が不足しています",
  "details": [
    {
      "error_code": "INSUFFICIENT_CAPACITY",
      "message": "定員が不足しています",
      "capacity_check": {
        "sufficient": false,
        "required": 1,
        "current": 0,
        "message": "必要: 1, 現在: 0"
      }
    }
  ],
  "suggestion": "定員ルールを確認してください"
}
```

### POST /api/calendar/events/{event_id}/archive

正式予定を無効化します。

### POST /api/calendar/events/bulk

正式予定を一括作成します。

ID指定の例:

```json
{
  "events": [
    {
      "member_id": 1,
      "event_date": "2026-06-01",
      "event_type_id": 1,
      "title": "RD",
      "display_label": "RD",
      "memo": "",
      "source_type": "manual"
    },
    {
      "member_id": 2,
      "event_date": "2026-06-01",
      "event_type_id": null,
      "title": "フリーテキスト予定",
      "display_label": "フリーテキスト予定",
      "memo": "メモ",
      "source_type": "manual"
    }
  ]
}
```

表示名指定の例:

```json
{
  "events": [
    {
      "member_name": "Aさん",
      "event_date": "2026-06-01",
      "event_type_name": "RD",
      "title": "RD",
      "display_label": "RD",
      "memo": "",
      "source_type": "manual"
    },
    {
      "member_name": "Bさん",
      "event_date": "2026-06-01",
      "event_type_name": null,
      "title": "フリーテキスト予定",
      "display_label": "フリーテキスト予定",
      "memo": "メモ",
      "source_type": "manual"
    }
  ]
}
```

`member_id` と `member_name` のいずれかを指定できます（両方指定した場合は `member_id` が優先されます）。  
`event_type_id` と `event_type_name` のいずれかを指定できます（両方指定した場合は `event_type_id` が優先されます）。  
両方とも指定しない場合はフリーテキスト予定として扱われます。

検証内容（各イベントに対して）:

- メンバー存在チェック（IDまたは表示名）
- 予定種類存在チェック（IDまたは表示名、指定されている場合のみ）
- 同一メンバー・同日・同一予定種類の重複チェック（`event_type_id` が指定されている場合）
- 同一メンバー・同日・同一予定名の重複チェック（`event_type_id` が null の場合）
- 定員チェック（`event_type_id` が指定され、かつ `requires_capacity_check=true` の予定種類の場合）

成功時のレスポンス:

```json
{
  "ok": true,
  "data": {
    "success_count": 2,
    "error_count": 0,
    "created_ids": [1, 2],
    "errors": []
  },
  "message": "バルクインポート完了: 成功 2件, 失敗 0件"
}
```

エラーが発生した場合のレスポンス:

```json
{
  "ok": true,
  "data": {
    "success_count": 1,
    "error_count": 1,
    "created_ids": [1],
    "errors": [
      {
        "index": 1,
        "error": "MEMBER_NOT_FOUND",
        "message": "メンバーID 999 が見つかりません",
        "data": {
          "member_id": 999,
          "event_date": "2026-06-01",
          "event_type_id": null,
          "title": "フリーテキスト予定",
          "display_label": "フリーテキスト予定",
          "memo": "メモ",
          "source_type": "manual"
        }
      }
    ]
  },
  "message": "バルクインポート完了: 成功 1件, 失敗 1件"
}
```

注: エラーが発生しても、成功したイベントはコミットされます。

## 番組スケジュールAPI

### POST /api/calendar/program-schedules/bulk

番組スケジュールを一括作成します。

ID指定の例:

```json
{
  "schedules": [
    {
      "program_id": 1,
      "studio_id": 1,
      "event_date": "2026-06-01"
    },
    {
      "program_id": 2,
      "studio_id": 1,
      "event_date": "2026-06-02"
    }
  ]
}
```

表示名指定の例:

```json
{
  "schedules": [
    {
      "program_name": "ニュース番組",
      "studio_name": "スタジオA",
      "event_date": "2026-06-01"
    },
    {
      "program_name": "バラエティ番組",
      "studio_name": "スタジオB",
      "event_date": "2026-06-02"
    }
  ]
}
```

`program_id` と `program_name` のいずれかを指定できます（両方指定した場合は `program_id` が優先されます）。
`studio_id` と `studio_name` のいずれかを指定できます（両方指定した場合は `studio_id` が優先されます）。

検証内容（各スケジュールに対して）:

- 番組存在チェック（IDまたは名前）
- スタジオ存在チェック（IDまたは名前）
- 同一番組・同一スタジオ・同日の重複チェック

成功時のレスポンス:

```json
{
  "ok": true,
  "data": {
    "success_count": 2,
    "error_count": 0,
    "created_ids": [1, 2],
    "errors": []
  },
  "message": "バルクインポート完了: 成功 2件, 失敗 0件"
}
```

エラーが発生した場合のレスポンス:

```json
{
  "ok": true,
  "data": {
    "success_count": 1,
    "error_count": 1,
    "created_ids": [1],
    "errors": [
      {
        "index": 1,
        "error": "PROGRAM_NOT_FOUND",
        "message": "番組名 '存在しない番組' が見つかりません",
        "data": {
          "program_name": "存在しない番組",
          "studio_name": "スタジオA",
          "event_date": "2026-06-02"
        }
      }
    ]
  },
  "message": "バルクインポート完了: 成功 1件, 失敗 1件"
}
```

注: エラーが発生しても、成功したスケジュールはコミットされます。

## 履歴イベントAPI

### GET /api/calendar/history-events

履歴イベント一覧を取得します。

クエリパラメータ:
- `member_id` (オプション): メンバーIDでフィルタ
- `year` (オプション): 年でフィルタ
- `month` (オプション): 月でフィルタ
- `event_type_id` (オプション): 予定種類IDでフィルタ

レスポンス例:

```json
{
  "ok": true,
  "data": [
    {
      "id": 1,
      "member_id": 1,
      "member_display_name": "Aさん",
      "event_date": "2026-05-01",
      "event_type_id": 1,
      "event_type_name": "RD",
      "event_type_code": "RD",
      "title": "RD",
      "display_label": "RD",
      "memo": null,
      "source_type": "manual",
      "source_detail": null,
      "original_event_id": 100,
      "archived_at": "2026-06-01T00:00:00+00:00",
      "created_at": "2026-05-01T00:00:00+00:00"
    }
  ],
  "message": "履歴イベント一覧を取得しました"
}
```

### POST /api/calendar/history-events/archive

1ヶ月以上前のイベントを履歴テーブルにアーカイブします。

クエリパラメータ:
- `cutoff_date` (オプション): アーカイブ対象の cutoff 日付（指定しない場合は今日から1ヶ月前）

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "archived_count": 50,
    "cutoff_date": "2026-05-27"
  },
  "message": "50件のイベントを履歴にアーカイブしました"
}
```

## 履歴集計API

### GET /api/calendar/history-aggregations

履歴集計一覧を取得します。このテーブルはAI分析用に最適化されています。

クエリパラメータ:
- `member_id` (オプション): メンバーIDでフィルタ
- `year` (オプション): 年でフィルタ
- `month` (オプション): 月でフィルタ
- `event_type_id` (オプション): 予定種類IDでフィルタ

レスポンス例:

```json
{
  "ok": true,
  "data": [
    {
      "id": 1,
      "member_id": 1,
      "member_display_name": "Aさん",
      "year": 2026,
      "month": 5,
      "event_type_id": 1,
      "event_type_name": "RD",
      "event_type_code": "RD",
      "count": 10,
      "updated_at": "2026-06-01T00:00:00+00:00"
    }
  ],
  "message": "履歴集計一覧を取得しました"
}
```

### POST /api/calendar/history-aggregations/update

履歴集計テーブルを更新します。履歴イベントから再集計を行います。

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "created_count": 150
  },
  "message": "150件の集計データを更新しました"
}
```

## CSVインポート／エクスポートAPI

### POST /api/calendar/imports/csv/preview

CSVファイルをアップロードしてプレビューします。

### POST /api/calendar/imports/csv/execute

プレビュー済みのCSVデータを実行します。

### GET /api/calendar/exports/csv

CSVファイルをエクスポートします。

クエリパラメータ:
- `export_type`: `members` | `event_types` | `events` | `monthly`
- `year`: 年（`monthly` の場合必須）
- `month`: 月（`monthly` の場合必須）

## 月間表示API

### GET /api/calendar/events/monthly?year=2026&month=6&department_id=1

月間予定表用データを取得します。

`department_id` を指定すると、その所属に所属するメンバーのみを表示します。

## 検索API

### GET /api/calendar/search

メンバー予定を柔軟に検索します。複数の条件を組み合わせて検索できます。

クエリパラメータ:
- `start_date` (オプション): 開始日 (YYYY-MM-DD)
- `end_date` (オプション): 終了日 (YYYY-MM-DD)
- `member_id` (オプション): メンバーID
- `member_name` (オプション): メンバー表示名
- `event_type_id` (オプション): 予定種類ID
- `event_type_name` (オプション): 予定種類名
- `department_id` (オプション): 所属ID
- `department_name` (オプション): 所属名

例: 2026年6月の映像所属のRDを検索

```
GET /api/calendar/search?start_date=2026-06-01&end_date=2026-06-30&department_name=映像&event_type_name=RD
```

レスポンス例:

```json
{
  "ok": true,
  "data": [
    {
      "id": 1,
      "member_id": 1,
      "member_name": "Aさん",
      "event_date": "2026-06-01",
      "event_type_id": 1,
      "event_type_name": "RD",
      "title": "RD",
      "display_label": "RD",
      "memo": null
    }
  ],
  "message": "検索結果を取得しました"
}
```

### GET /api/calendar/search/programs

番組スケジュールを柔軟に検索します。

クエリパラメータ:
- `start_date` (オプション): 開始日 (YYYY-MM-DD)
- `end_date` (オプション): 終了日 (YYYY-MM-DD)
- `program_id` (オプション): 番組ID
- `program_name` (オプション): 番組名
- `studio_id` (オプション): スタジオID
- `studio_name` (オプション): スタジオ名

例: 2026年6月のスタジオAのスケジュールを検索

```
GET /api/calendar/search/programs?start_date=2026-06-01&end_date=2026-06-30&studio_name=スタジオA
```

レスポンス例:

```json
{
  "ok": true,
  "data": [
    {
      "id": 1,
      "program_id": 1,
      "program_name": "ニュース番組",
      "program_short_label": "ニュース",
      "studio_id": 1,
      "studio_name": "スタジオA",
      "event_date": "2026-06-01"
    }
  ],
  "message": "番組スケジュール検索結果を取得しました"
}
```

## AI参照API

### GET /api/ai/calendar/search

AI参照ツールをGETクエリパラメータで検索します。

認証:
- Header: `Authorization: Bearer {AI_READ_API_KEY}`

クエリパラメータ:
- `tool` (必須): ツール名
- `year` (オプション): 年
- `month` (オプション): 月
- `start_date` (オプション): 開始日 (YYYY-MM-DD)
- `end_date` (オプション): 終了日 (YYYY-MM-DD)
- `member_name` (オプション): メンバー表示名
- `event_name` (オプション): 予定名
- `event_type_name` (オプション): 予定種類名
- `source_type` (オプション): ソースタイプ
- `department_name` (オプション): 所属名
- `is_active` (オプション): 有効フラグ
- `limit` (オプション): 最大件数（デフォルト50）

例: 2026年6月のRDを検索
```
GET /api/ai/calendar/search?tool=calendar_events_search&year=2026&month=6&event_type_name=RD
```

例: 映像所属のメンバー一覧
```
GET /api/ai/calendar/search?tool=calendar_members_list&department_name=映像
```

例: 2026年6月の定員状況
```
GET /api/ai/calendar/search?tool=calendar_capacity_summary&year=2026&month=6
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "count": 10,
    "events": [...]
  },
  "message": "AI search 'calendar_events_search' executed"
}
```

### GET /api/ai/calendar/capabilities

Difyが使用可能な参照ツール一覧を取得します。

認証:
- Header: `Authorization: Bearer {AI_READ_API_KEY}`

クエリパラメータ:
- `tool_name` (オプション): 特定のツール名を指定してそのツールのみを取得

例: 全ツール一覧を取得
```
GET /api/ai/calendar/capabilities
```

例: 特定のツールのみを取得
```
GET /api/ai/calendar/capabilities?tool_name=calendar_events_search
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "tools": [
      {
        "name": "calendar_events_search",
        "description": "Search calendar events by various filters",
        "allowed_filters": ["year", "month", "start_date", "end_date", "member_name", "event_name", "event_type_name", "source_type"],
        "max_limit": 100
      },
      {
        "name": "calendar_members_list",
        "description": "List calendar members with optional filters",
        "allowed_filters": ["department_name", "is_active"],
        "max_limit": 100
      },
      {
        "name": "calendar_capacity_summary",
        "description": "Get capacity summary for a given year/month and event types",
        "allowed_filters": ["year", "month", "event_type_name"],
        "max_limit": 50
      }
    ]
  },
  "message": "AI capabilities retrieved"
}
```

### POST /api/ai/calendar/query

単一の参照ツールを実行します。

認証:
- Header: `Authorization: Bearer {AI_READ_API_KEY}`

リクエスト例:

```json
{
  "tool": "calendar_events_search",
  "filters": {
    "year": 2026,
    "month": 6,
    "event_type_name": "RD"
  },
  "limit": 50
}
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "count": 10,
    "events": [
      {
        "id": 1,
        "member_name": "Aさん",
        "event_date": "2026-06-01",
        "event_type_name": "RD",
        "title": "RD",
        "display_label": "RD",
        "source_type": "manual"
      }
    ]
  },
  "message": "AI query 'calendar_events_search' executed"
}
```

### POST /api/ai/calendar/query-batch

複数の参照ツールを一括実行します（Dify Workflowのforループ対応）。

認証:
- Header: `Authorization: Bearer {AI_READ_API_KEY}`

リクエスト例:

```json
{
  "iteration": 1,
  "queries": [
    {
      "tool": "calendar_events_search",
      "filters": {
        "year": 2026,
        "month": 6
      },
      "limit": 50
    },
    {
      "tool": "calendar_members_list",
      "filters": {
        "department_name": "映像"
      },
      "limit": 50
    }
  ]
}
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "iteration": 1,
    "results": [
      {
        "tool": "calendar_events_search",
        "success": true,
        "data": {
          "count": 10,
          "events": [...]
        }
      },
      {
        "tool": "calendar_members_list",
        "success": true,
        "data": {
          "count": 5,
          "members": [...]
        }
      }
    ]
  },
  "message": "AI query-batch executed: iteration 1"
}
```

## 開発者用API

### GET /api/dev/tables

データベースの全テーブル一覧を取得します（開発者用）。

認証:
- Header: `Authorization: Bearer {DEV_API_KEY}`

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "tables": [
      "calendar_members",
      "calendar_event_types",
      "calendar_events",
      "departments",
      "calendar_member_departments",
      "calendar_event_type_capacity_rules",
      "studios",
      "programs",
      "program_schedules",
      "history_events",
      "history_aggregations",
      "program_history_events",
      "program_history_aggregations",
      "audit_logs"
    ]
  },
  "message": "Tables listed"
}
```

### GET /api/dev/tables/{table_name}

指定したテーブルのデータを取得します（開発者用）。

認証:
- Header: `Authorization: Bearer {DEV_API_KEY}`

クエリパラメータ:
- `limit` (オプション): 最大件数（デフォルト100）
- `offset` (オプション): オフセット（デフォルト0）

例: calendar_membersテーブルの最初の50件を取得
```
GET /api/dev/tables/calendar_members?limit=50&offset=0
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "table_name": "calendar_members",
    "columns": [
      "id",
      "display_name",
      "short_name",
      "is_active",
      "display_order"
    ],
    "data": [
      {
        "id": 1,
        "display_name": "山田太郎",
        "short_name": "山田",
        "is_active": true,
        "display_order": 1
      }
    ],
    "total": 10,
    "limit": 50,
    "offset": 0
  },
  "message": "Data from table 'calendar_members' retrieved"
}
```

## チャットAPI

### POST /api/chat/dify-proxy

UIからDifyへ安全にメッセージを送信するプロキシAPIです。

リクエスト例:

```json
{
  "message": "明日のRDは？",
  "year": 2026,
  "month": 6
}
```

レスポンス例:

```json
{
  "ok": true,
  "data": {
    "reply": "明日（6月2日）のRDはAさん、Bさんが担当予定です。"
  },
  "message": "AI応答を取得しました"
}
```
