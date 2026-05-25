# DB仕様

## calendar_members

スケジュール表に表示するメンバーです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| display_name | 表示名 |
| short_name | 略称 |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_event_types

予定種類マスタです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| code | 予定種類コード |
| name | 予定種類名 |
| short_label | 短縮表示 |
| display_color | 表示色 |
| display_symbol | 表示記号 |
| is_leave | 休暇扱い |
| is_work_assignment | 業務予定扱い |
| requires_capacity_check | 将来の定員チェック対象 |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_event_drafts

正式登録前の仮予定です。  
将来、Dify・Excel・音声入力からの解析結果もここに保存します。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_name_raw | 入力されたメンバー名 |
| member_id | 解決済みメンバーID |
| event_date | 予定日 |
| event_type_name_raw | 入力された予定種類名 |
| event_type_id | 解決済み予定種類ID |
| title | タイトル |
| display_label | 表示ラベル |
| memo | メモ |
| source_type | 入力元 |
| source_text | 元テキスト |
| validation_status | 検証状態 |
| approval_status | 承認状態 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_events

承認済みの正式予定です。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_id | メンバーID |
| event_date | 予定日 |
| event_type_id | 予定種類ID |
| title | タイトル |
| display_label | 表示ラベル |
| memo | メモ |
| source_type | 入力元 |
| approval_status | 承認状態 |
| is_archived | アーカイブフラグ |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## audit_logs

重要操作ログです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| actor_type | 操作者種別 |
| actor_name | 操作者名 |
| action | 操作 |
| target_type | 対象種別 |
| target_id | 対象ID |
| request_json | リクエスト |
| response_json | レスポンス |
| created_at | 作成日時 |
