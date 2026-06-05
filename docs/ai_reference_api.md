# AI参照API仕様

## 概要

AI参照APIは、Dify Workflowからデータベース情報を安全に取得するための読み取り専用APIです。DifyがSQLを直接実行したりDBにアクセスしたりすることを防ぎ、定義された参照ツールのみを通じてデータを取得します。

## セキュリティ原則

1. **読み取り専用**: 登録・更新・削除系操作は許可しない
2. **ツール制限**: 許可されたツールのみ実行可能
3. **フィルタ制限**: 各ツールで許可されたフィルタのみ使用可能
4. **リミット制限**: 各ツールで最大リミットを設定
5. **日付範囲制限**: 過度に広い日付範囲を禁止
6. **SQL禁止**: SQL文字列や任意クエリを受け取らない
7. **認証必須**: `AI_READ_API_KEY` によるBearer認証

## 認証

すべてのAI参照APIには以下のヘッダーが必要です：

```
Authorization: Bearer {AI_READ_API_KEY}
```

## APIエンドポイント

### GET /api/ai/calendar/capabilities

利用可能な参照ツール一覧を取得します。

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
  },
  "message": "AI capabilities retrieved"
}
```

### POST /api/ai/calendar/query

単一の参照ツールを実行します。

**リクエスト:**

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

**バリデーション:**

- `tool` が許可リストにあるか
- `limit` がツールの `max_limit` 以下か
- `filters` のキーが `allowed_filters` に含まれるか
- 日付範囲が `max_date_range_days` 以下か

**レスポンス:**

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

複数の参照ツールを一括実行します。Dify Workflowのforループ対応。

**リクエスト:**

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

**バリデーション:**

- `queries` の数が3以下か
- 各クエリが単一クエリと同じバリデーションを通過するか

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

## 参照ツール詳細

### calendar_events_search

カレンダー予定を検索します。

**許可フィルタ:**
- `year`: 年（int）
- `month`: 月（int）
- `start_date`: 開始日（YYYY-MM-DD）
- `end_date`: 終了日（YYYY-MM-DD）
- `member_name`: メンバー表示名（string）
- `event_name`: 予定名（string、部分一致）
- `event_type_name`: 予定種類名（string）
- `source_type`: ソースタイプ（string）

**最大リミット:** 100件
**最大日付範囲:** 365日

**レスポンスデータ:**

```json
{
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
}
```

### calendar_members_list

メンバー一覧を取得します。

**許可フィルタ:**
- `department_name`: 所属名（string）
- `is_active`: 有効フラグ（boolean）

**最大リミット:** 100件
**最大日付範囲:** なし

**レスポンスデータ:**

```json
{
  "count": 5,
  "members": [
    {
      "id": 1,
      "display_name": "Aさん",
      "short_name": "A",
      "is_active": true
    }
  ]
}
```

### calendar_capacity_summary

指定年月・予定種類ごとの定員充足状況を取得します。

**許可フィルタ:**
- `year`: 年（int、必須）
- `month`: 月（int、必須）
- `event_type_name`: 予定種類名（string、オプション）

**最大リミット:** 50件
**最大日付範囲:** 31日

**レスポンスデータ:**

```json
{
  "count": 2,
  "summaries": [
    {
      "event_type_name": "RD",
      "department_name": "映像",
      "day_type": "weekday",
      "daily": [
        {
          "date": "2026-06-01",
          "required": 2,
          "current": 2,
          "sufficient": true
        }
      ]
    }
  ]
}
```

## エラーレスポンス

### 認証エラー

```json
{
  "ok": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing Authorization header"
  }
}
```

### ツール許可エラー

```json
{
  "ok": false,
  "error": {
    "code": "TOOL_NOT_ALLOWED",
    "message": "Tool 'invalid_tool' not allowed"
  }
}
```

### フィルタ許可エラー

```json
{
  "ok": false,
  "error": {
    "code": "FILTER_NOT_ALLOWED",
    "message": "Filter 'invalid_filter' not allowed for tool 'calendar_events_search'"
  }
}
```

### リミット超過エラー

```json
{
  "ok": false,
  "error": {
    "code": "LIMIT_EXCEEDED",
    "message": "Limit exceeds maximum of 100"
  }
}
```

### 日付範囲エラー

```json
{
  "ok": false,
  "error": {
    "code": "DATE_RANGE_TOO_LARGE",
    "message": "Date range exceeds maximum of 365 days"
  }
}
```

## セキュリティ検証

サーバ側で以下の検証を実行します：

1. **ツール検証**: リクエストされたツールが `ALLOWED_AI_TOOLS` に含まれるか
2. **フィルタ検証**: 各フィルタがツールの `allowed_filters` に含まれるか
3. **リミット検証**: リミットがツールの `max_limit` 以下か
4. **日付範囲検証**: 日付範囲がツールの `max_date_range_days` 以下か
5. **SQL注入防止**: 文字列連結によるクエリ構築を行わない
6. **更新操作防止**: INSERT/UPDATE/DELETE操作を許可しない

## 監査ログ

以下の操作は `audit_logs` に記録されます：

- `ai_capabilities`: ツール一覧取得
- `ai_query`: 単一クエリ実行（ツール名、フィルタ、リミット、結果件数）
- `ai_query_batch`: バッチクエリ実行（iteration数、クエリ数、成功数）

**注意:** 質問全文や取得データ全文は大量保存されません。

## ログ

アプリログには以下が記録されます：

- AI capabilities取得
- AI query実行（ツール名、返却件数）
- AI query-batch実行（iteration番号、ツール名、返却件数）
- 認証エラー
- 各種バリデーションエラー

**注意:** APIキーやトークンはログに出力されません。

## 拡張性

### 新しいツールの追加

新しい参照ツールを追加する場合：

1. `ALLOWED_AI_TOOLS` にツール名を追加
2. `TOOL_DEFINITIONS` にツール定義を追加
3. `execute_ai_tool()` に分岐を追加
4. ツール実装関数を作成

**例:**

```python
ALLOWED_AI_TOOLS = {
    "calendar_events_search",
    "calendar_members_list",
    "calendar_capacity_summary",
    "new_tool_name"  # 追加
}

TOOL_DEFINITIONS = {
    # ... 既存ツール ...
    "new_tool_name": {
        "name": "new_tool_name",
        "description": "New tool description",
        "allowed_filters": ["filter1", "filter2"],
        "max_limit": 50,
        "max_date_range_days": 30
    }
}

def execute_ai_tool(tool_name: str, filters: dict, limit: int, db: Session) -> dict:
    if tool_name == "new_tool_name":
        return tool_new_tool_name(filters, limit, db)
    # ... 既存分岐 ...

def tool_new_tool_name(filters: dict, limit: int, db: Session) -> dict:
    # ツール実装
    pass
```

## トラブルシューティング

### 401 Unauthorized

- `AI_READ_API_KEY` が `.env` に設定されているか確認
- Authorizationヘッダーが正しい形式か確認

### 403 Forbidden

- APIキーが正しいか確認
- ツールが許可リストにあるか確認

### 400 Bad Request

- リクエスト形式が正しいか確認
- フィルタが許可されているか確認
- リミットが範囲内か確認
- 日付範囲が制限内か確認
