# DB仕様

## テーブル一覧

- calendar_members
- calendar_event_types
- calendar_events
- calendar_event_drafts
- audit_logs
- departments
- calendar_member_departments
- calendar_event_type_capacity_rules
- studios
- programs
- program_schedules
- history_events
- history_aggregations

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

予定種類マスタです。定員ルール・色分け・分類に使う予定だけ登録します。通常の予定名はフリーテキストで登録できます。

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
| requires_capacity_check | 定員チェック対象 |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_events

承認済みの正式予定です。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_id | メンバーID |
| event_date | 予定日 |
| event_type_id | 予定種類ID（任意、nullの場合はフリーテキスト予定） |
| title | 予定名（必須） |
| display_label | 表示ラベル（任意、空の場合はtitleを使用） |
| memo | メモ |
| source_type | 入力元 |
| source_detail | 入力元詳細 |
| approval_status | 承認状態 |
| sync_status | 同期状態 |
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

## departments

所属マスタです。映像、音声、調整、照明、回線などを管理します。

| カラム | 用途 |
|---|---|
| id | 主キー |
| name | 所属名 |
| code | 所属コード |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_member_departments

メンバーと所属の多対多関係テーブルです。メンバーは複数の所属を持つことができます。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_id | メンバーID |
| department_id | 所属ID |
| created_at | 作成日時 |

## calendar_event_type_capacity_rules

予定種類ごとの定員ルールです。`requires_capacity_check=true` の予定種類について、draft validate 時に定員チェックを行います。

| カラム | 用途 |
|---|---|
| id | 主キー |
| event_type_id | 予定種類ID |
| department_id | 所属ID（nullで全所属対象） |
| day_type | 曜日タイプ（weekday/weekend/all） |
| required_count | 必要人数 |
| is_active | 有効フラグ |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## calendar_event_drafts

承認前のドラフト予定です。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_name_raw | メンバー名（生データ） |
| member_id | メンバーID（解決後） |
| event_date | 予定日 |
| event_type_name_raw | 予定種類名（生データ） |
| event_type_id | 予定種類ID（解決後） |
| title | 予定名 |
| display_label | 表示ラベル |
| memo | メモ |
| source_type | 入力元 |
| source_text | 入力元テキスト |
| validation_status | 検証状態 |
| approval_status | 承認状態 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## studios

スタジオマスタです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| name | スタジオ名 |
| code | スタジオコード |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## programs

番組マスタです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| name | 番組名 |
| code | 番組コード |
| short_label | 短縮表示 |
| display_color | 表示色 |
| is_active | 有効フラグ |
| display_order | 表示順 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## program_schedules

番組スケジュールです。

| カラム | 用途 |
|---|---|
| id | 主キー |
| program_id | 番組ID |
| studio_id | スタジオID |
| event_date | 予定日 |
| created_at | 作成日時 |
| updated_at | 更新日時 |

## history_events

履歴イベントテーブルです。1ヶ月以上前のイベントがアーカイブされます。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_id | メンバーID |
| member_display_name | メンバー表示名 |
| event_date | 予定日 |
| event_type_id | 予定種類ID |
| event_type_name | 予定種類名 |
| event_type_code | 予定種類コード |
| title | 予定名 |
| display_label | 表示ラベル |
| memo | メモ |
| source_type | 入力元 |
| source_detail | 入力元詳細 |
| original_event_id | 元のイベントID |
| archived_at | アーカイブ日時 |
| created_at | 作成日時 |

## history_aggregations

履歴集計テーブルです。AI分析用に最適化されています。メンバーごとの月次集計を保持します。

| カラム | 用途 |
|---|---|
| id | 主キー |
| member_id | メンバーID |
| member_display_name | メンバー表示名 |
| year | 年 |
| month | 月 |
| event_type_id | 予定種類ID |
| event_type_name | 予定種類名 |
| event_type_code | 予定種類コード |
| count | 件数 |
| updated_at | 更新日時 |
