# Dify Workflow設定ガイド

## 概要

Headless Calendarアプリと連携するDify Workflowの構成と、使用するAPIエンドポイントを説明します。

## Workflow構成

```
Start
  - 自由な質問文
  - current_year
  - current_month
  - capabilities
↓
Planner LLM
  - DB参照が必要か判断
  - 必要なら capabilities の中から使うtoolを選ぶ
  - filters を作る
↓
条件分岐
  ├─ need_db = true
  │    ↓
  │  HTTP Request
  │    - Plannerが選んだtool/filterをサーバへ送る
  │    ↓
  │  Answer LLM with DB context
  │    - HTTPで返ってきたDB情報を根拠に回答
  │
  └─ need_db = false
       ↓
     Answer LLM without DB context
       - DBを見ずに一般回答・操作説明
↓
End
```

## 入力変数

```
query: ユーザー質問
current_year: カレンダー表示中の年
current_month: カレンダー表示中の月
capabilities: 利用可能な参照ツール一覧（GET /api/ai/calendar/capabilitiesで取得）
```

## 使用するAPI

### GET /api/ai/calendar/search

AI参照ツールをGETクエリパラメータで検索します。

**認証:** `Authorization: Bearer {AI_READ_API_KEY}`

**クエリパラメータ:**
- `tool` (必須): ツール名
- `year`, `month`, `start_date`, `end_date`
- `member_name`, `event_name`, `event_type_name`, `source_type`
- `department_name`, `is_active`
- `limit` (デフォルト50)

**例:**
```
GET /api/ai/calendar/search?tool=calendar_events_search&year=2026&month=6&event_type_name=RD
GET /api/ai/calendar/search?tool=calendar_members_list&department_name=映像
```

### GET /api/ai/calendar/capabilities

利用可能な参照ツール一覧を取得します。

**認証:** `Authorization: Bearer {AI_READ_API_KEY}`

**クエリパラメータ:**
- `tool_name` (オプション): 特定のツール名を指定してそのツールのみを取得

**例:**
```
GET /api/ai/calendar/capabilities
GET /api/ai/calendar/capabilities?tool_name=calendar_events_search
```

**レスポンス:**
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
  }
}
```

### POST /api/ai/calendar/query-batch

複数の参照ツールを一括実行します。

**認証:** `Authorization: Bearer {AI_READ_API_KEY}`

**リクエスト:**
```json
{
  "iteration": 1,
  "queries": [
    {
      "tool": "calendar_events_search",
      "filters": {
        "year": 2026,
        "month": 6,
        "event_type_name": "RD"
      },
      "limit": 50
    }
  ]
}
```

**レスポンス:**
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
      }
    ]
  }
}
```

## HTTP Requestノード設定

**メソッド:** POST
**URL:** `https://your-server.com/api/ai/calendar/query-batch`
**ヘッダー:**
```
Authorization: Bearer {AI_READ_API_KEY}
Content-Type: application/json
```

## 参照ツール一覧

### calendar_events_search

カレンダー予定検索

**許可フィルタ:**
- `year`, `month`, `start_date`, `end_date`
- `member_name`, `event_name`, `event_type_name`, `source_type`

**最大リミット:** 100件

### calendar_members_list

メンバー一覧

**許可フィルタ:**
- `department_name`, `is_active`

**最大リミット:** 100件

### calendar_capacity_summary

定員充足状況

**許可フィルタ:**
- `year` (必須), `month` (必須), `event_type_name`

**最大リミット:** 50件

## 制限

- 1回のバッチで最大3クエリ
- 各ツールにリミット上限あり
- 日付範囲の最大制限あり

