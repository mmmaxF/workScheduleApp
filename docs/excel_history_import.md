# Excel履歴インポート機能

## 概要

過去にExcelで管理していた勤務表をデータベースに取り込む機能です。将来的にAIが勤務自動作成を行う際の参照データとして使用するために、過去の実績データを蓄積します。

## 目的

- 過去Excel勤務表のデータをDBに取り込む
- AIによる勤務自動作成の学習データとして活用
- 過去の定員状況やパターンを分析可能にする

## 重要方針

### 新規テーブルは作成しない

以下のテーブルは作成しません：

- excel_import_jobs
- excel_import_rows
- calendar_event_type_aliases
- calendar_member_aliases

### 追跡範囲

- この予定がどのExcelファイルのどのセルから来たかは追跡しません
- セル番地やファイル名は保存しません
- 別名マスタは使用しません

### 照合方法

- メンバー名は `calendar_members.display_name` と完全一致で照合
- 予定種類名は `calendar_event_types.name` または `short_label` と完全一致で照合
- 一致しない行は invalid としてプレビューに表示

### 取り込み先

- `calendar_event_drafts` には入れない
- 過去データなので `calendar_events` に直接登録

## source_type について

Excel履歴から取り込んだ予定は、`calendar_events.source_type` に `excel_history` を設定します。

これは「この予定が過去Excel取込由来である」と分かるようにするための区分です。

## 登録時の値

```python
{
    "member_id": <member_id>,
    "event_date": <event_date>,
    "event_type_id": <event_type_id>,
    "title": <event_name>,
    "display_label": <event_name>,
    "memo": None,
    "source_type": "excel_history",
    "source_detail": "過去Excel取込",
    "approval_status": "approved",
    "sync_status": "none",
    "is_archived": False
}
```

## API

### POST /api/calendar/imports/excel-history/preview

Excelファイルをアップロードしてプレビューします。

**リクエスト:**

```multipart/form-data
file: Excelファイル (.xlsx, .xls)
```

**レスポンス:**

```json
{
  "ok": true,
  "data": {
    "valid": [
      {
        "row": 2,
        "col": 3,
        "member_id": 1,
        "member_name": "田中太郎",
        "event_type_id": 1,
        "event_name": "RD",
        "event_date": "2026-06-01",
        "title": "RD",
        "display_label": "RD"
      }
    ],
    "invalid": [
      {
        "row": 3,
        "col": 2,
        "member_name": "山田花子",
        "event_name": "不明な予定",
        "event_date": "2026-06-02",
        "reason": "予定種類が見つかりません"
      }
    ],
    "summary": {
      "valid_count": 10,
      "invalid_count": 2
    }
  },
  "message": "Excel履歴プレビュー完了"
}
```

### POST /api/calendar/imports/excel-history/execute

プレビュー済みのデータをインポートします。

**リクエスト:**

```json
{
  "valid": [
    {
      "row": 2,
      "col": 3,
      "member_id": 1,
      "member_name": "田中太郎",
      "event_type_id": 1,
      "event_name": "RD",
      "event_date": "2026-06-01",
      "title": "RD",
      "display_label": "RD"
    }
  ]
}
```

**レスポンス:**

```json
{
  "ok": true,
  "data": {
    "created_count": 8,
    "skipped_count": 2,
    "errors": []
  },
  "message": "Excel履歴インポート完了: 8件作成、2件スキップ"
}
```

## Excelの想定形式

### 基本形式

- 横軸が日付
- 縦軸がメンバー
- 各セルに予定名が入っている

### 具体例

```
|          | 2026-06-01 | 2026-06-02 | 2026-06-03 | ... |
|----------|------------|------------|------------|-----|
| 田中太郎 | RD         | 年休       | RD         | ... |
| 山田花子 | ★          | RD         | ★          | ... |
| 佐藤次郎 | RD         | RD         | 年休       | ... |
```

### セルの扱い

- 空欄セルは無視
- 1セルに複数行がある場合は改行で分割
- セル色は使用しない
- セル番地は保存しない
- ファイル名は保存しない

### 日付行の位置

- 1行目がヘッダー（日付）
- 2行目以降がデータ（メンバー名 + 予定）

### 日付形式

- `datetime` オブジェクト: 自動的に日付として解析
- 文字列: `YYYY-MM-DD` 形式で解析

## 定員チェックについて

過去実績の取り込みなので、定員チェックは行いません。

過去データは「当時の実績」として取り込むため、RDが不足していた日や多かった日があっても登録できます。

ただし、重複チェックは行います。

## 重複チェック

以下の条件で重複をチェックします：

- 同一メンバー
- 同一日
- 同一予定種類
- `source_type = excel_history`

重複がある行は invalid としてプレビューに表示されます。

## Web UI

### アクセス方法

1. `/calendar` 画面にアクセス
2. 「CSVインポート」ボタンをクリック
3. インポート種類で「Excel履歴（過去勤務表）」を選択

### UI要素

- Excelファイル選択
- プレビュー実行ボタン
- valid / invalid 表示
- インポート実行ボタン

### プレビュー表示

- 有効行数
- 無効行数
- 無効行の詳細（最大20件）

### インポート実行

- valid行のみをインポート
- 実行後に `/calendar` で確認可能

## ログ

### logs/app.log

以下を記録します：

- Excel履歴プレビュー開始・終了
- Excel履歴インポート実行
- valid件数
- invalid件数
- 正式予定作成件数
- スキップ件数

### audit_logs

以下を記録します：

- `excel_history_preview`
- `excel_history_execute`

Excelの全内容はログに保存しません。

## 既存機能との互換性

以下の機能は引き続き動作します：

- `/calendar` - 月間予定表
- `/masters` - マスタ管理
- `/drafts` - 下書き管理
- `/csv` - CSVインポート/エクスポート
- CSVインポート
- CSVエクスポート
- draft validate
- draft approve
- 月間予定表表示

## 動作確認

最低限、以下を確認してください：

1. Excelファイルを選択できる
2. プレビューできる
3. valid / invalid が表示される
4. valid行だけインポート実行できる
5. calendar_events に source_type=excel_history で入る
6. /calendar に表示される
7. 同じExcelを再度取り込んだ場合、重複行はスキップまたはinvalidになる

## 注意点

- メンバー名と予定種類名は完全一致が必要
- 大文字小文字の区別がある
- 前後の空白は自動的にトリムされる
- 過去データなので定員チェックは行われない
- 重複チェックは行われる
- 同じExcelを再度取り込むと重複エラーになる
