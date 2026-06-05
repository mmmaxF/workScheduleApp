# CSVインポート／エクスポート

## 概要

CSVファイルを使用して、メンバー、予定種類、予定のインポート／エクスポートができます。

## インポート種類

### メンバー (members)

メンバー情報をインポートします。

必須ヘッダー:
- `display_name`: 表示名
- `short_name`: 略称
- `is_active`: 有効フラグ (true/false)
- `display_order`: 表示順

### 予定種類 (event_types)

予定種類マスタをインポートします。

必須ヘッダー:
- `code`: 予定種類コード
- `name`: 予定種類名
- `short_label`: 短縮表示
- `display_color`: 表示色
- `display_symbol`: 表示記号
- `is_leave`: 休暇扱い (true/false)
- `is_work_assignment`: 業務予定扱い (true/false)
- `requires_capacity_check`: 定員チェック対象 (true/false)
- `is_active`: 有効フラグ (true/false)
- `display_order`: 表示順

### 予定 (events)

予定をインポートします。

必須ヘッダー:
- `member_name`: メンバー名
- `event_date`: 予定日 (yyyy-mm-dd)
- `title`: 予定名（必須）

任意ヘッダー:
- `event_type_name`: 予定種類名（指定時のみマスタと照合）
- `display_label`: 表示ラベル（空の場合はtitleを使用）
- `memo`: メモ

**フリーテキスト予定**: `event_type_name` を省略または空欄にすると、フリーテキスト予定として登録されます。定員チェックは行われません。

**マスタ紐づき予定**: `event_type_name` を指定すると、マスタと照合されます。マスタが見つかれば定員チェックが適用されます。

## インポートフロー

1. `/calendar` 画面で「CSVインポート」ボタンをクリック
2. インポート種類を選択
3. CSVファイルをアップロード
4. プレビューを実行
   - ヘッダー検証
   - データ検証
   - メンバー名・予定種類名の照合
   - valid/invalid 行を表示
5. インポート実行
   - valid行のみを登録
   - 予定の場合は `calendar_event_drafts` に登録
6. `/drafts` でドラフトを確認・承認

## エクスポート種類

### メンバー (members)

メンバー情報をエクスポートします。

### 予定種類 (event_types)

予定種類マスタをエクスポートします。

### 予定（全件）(events)

全ての正式予定をエクスポートします。

### 予定（月指定）(monthly)

指定した月の予定をエクスポートします。

クエリパラメータ:
- `year`: 年
- `month`: 月

## API

### POST /api/calendar/imports/csv/preview

CSVファイルをアップロードしてプレビューします。

リクエスト:
```multipart/form-data
import_type: members | event_types | events
file: CSVファイル
```

レスポンス:
```json
{
  "ok": true,
  "data": {
    "import_type": "events",
    "total_rows": 10,
    "valid_rows": 8,
    "invalid_rows": 2,
    "rows": [
      {
        "row_number": 2,
        "status": "valid",
        "data": {
          "member_name": "田中太郎",
          "event_date": "2026-06-01",
          "title": "急きょ対応",
          "event_type_name": "",
          "display_label": "急きょ対応",
          "memo": ""
        },
        "errors": []
      },
      {
        "row_number": 3,
        "status": "invalid",
        "data": {},
        "errors": [
          {
            "field": "member_name",
            "error_code": "MEMBER_NOT_FOUND",
            "message": "メンバーが見つかりません: 山田花子"
          }
        ]
      }
    ]
  },
  "message": "CSVプレビューを作成しました"
}
```

### POST /api/calendar/imports/csv/execute

プレビュー済みのCSVデータを実行します。

リクエスト:
```json
{
  "import_type": "events",
  "rows": [
    {
      "row_number": 2,
      "status": "valid",
      "data": {
        "member_name": "田中太郎",
        "event_date": "2026-06-01",
        "title": "急きょ対応",
        "event_type_name": "",
        "display_label": "急きょ対応",
        "memo": ""
      },
      "errors": []
    }
  ]
}
```

レスポンス:
```json
{
  "ok": true,
  "data": {
    "import_type": "events",
    "success_count": 8,
    "failed_count": 0,
    "created_ids": [1, 2, 3, 4, 5, 6, 7, 8],
    "errors": []
  },
  "message": "CSVインポートを実行しました"
}
```

### GET /api/calendar/exports/csv

CSVファイルをエクスポートします。

クエリパラメータ:
- `export_type`: members | event_types | events | monthly
- `year`: 年（monthly の場合必須）
- `month`: 月（monthly の場合必須）

レスポンス:
- Content-Type: text/csv; charset=utf-8
- Content-Disposition: attachment; filename="calendar_xxx.csv"

## 文字コード

CSVファイルは以下の文字コードに対応しています:
- UTF-8 (BOM付き)
- UTF-8
- CP932
- Shift_JIS

## 注意点

- 予定のインポートは `calendar_event_drafts` に登録され、承認が必要です
- フリーテキスト予定（`event_type_name` 未指定）は定員チェックの対象外です
- マスタ紐づき予定（`event_type_name` 指定）は定員チェックの対象になります
- エクスポートされるCSVはUTF-8 BOM付きで、Excelで開きやすい形式です
