# 処理フロー

## 基本フロー

```text
入力
→ 検証（メンバー存在、予定種類存在チェック（指定時のみ）、重複チェック、定員チェック（指定時のみ））
→ calendar_eventsへ直接登録
→ audit_logsへ記録
```

## ステップ2の範囲

ステップ2では、以下の機能を追加しました：

- 所属管理（映像、音声、調整、照明、回線）
- メンバーの複数所属設定
- 予定種類ごとの定員ルール管理
- 予定登録時の定員チェック
- 月間表の所属フィルタ
- 月間表の定員状況表示
- CSVインポート／エクスポート

Dify・音声入力は使いません。

## 予定登録フロー

1. `/api/calendar/events` で予定を作成する
   - メンバー存在チェック
   - 予定種類存在チェック（`event_type_id` が指定されている場合のみ）
   - 同一メンバー・同日・同一予定種類の重複チェック（`event_type_id` が指定されている場合）
   - 同一メンバー・同日・同一予定名の重複チェック（`event_type_id` が null の場合）
   - **定員チェック**（`event_type_id` が指定され、かつ `requires_capacity_check=true` の予定種類の場合）
2. 検証に通れば `calendar_events` に正式予定が作成される
3. `/calendar` の月間表に表示される（所属フィルタ可能）

## 定員チェックフロー

定員チェックは以下の条件で実行されます：

- `event_type_id` が指定されている場合
- 予定種類の `requires_capacity_check` が `true` の場合
- 予定に `event_date` が設定されている場合

チェック手順：

1. 予定種類と日付に対応する定員ルールを検索
2. 曜日タイプ（平日/週末/全日）に一致するルールを適用
3. 既存の正式予定数をカウント
4. 必要人数と現在人数を比較
5. 不足している場合は登録エラー

## 所属フィルタフロー

月間表で所属フィルタを使用する場合：

1. 月間表示APIに `department_id` パラメータを指定
2. 指定された所属に所属するメンバーのみを抽出
3. そのメンバーの予定のみを表示

## CSVインポートフロー

CSVファイルを取り込む場合：

1. `/calendar` 画面で「CSVインポート」ボタンをクリック
2. インポート種類を選択（メンバー、予定種類、予定）
3. CSVファイルをアップロード
4. プレビューを実行
   - メンバー名を `calendar_members.display_name` と照合
   - 予定種類名を `calendar_event_types.name` または `short_label` と照合（指定時のみ）
   - 重複チェック
   - valid/invalid 行を表示
5. インポート実行
   - valid行のみを登録
   - 予定の場合は `calendar_event_drafts` に登録
6. `/drafts` でドラフトを確認・承認

詳細は `docs/csv_import_export.md` を参照してください。

## AIチャットフロー

AIアシスタントチャットを使用する場合：

1. `/calendar` 画面のチャット窓口に質問を入力
2. フロントエンドが現在表示中の `year`、`month` と共に `/api/chat/dify-proxy` へ送信
3. サーバがDify Chat APIへリクエストを転送（APIキーはサーバ側で管理）
4. Dify Workflowが処理：
   - Planner LLMがDB参照の要否を判断
   - 必要なら `/api/ai/calendar/query-batch` を呼び出してDB情報を取得
   - 取得したデータに基づいて回答を生成
5. サーバがDifyからの回答をフロントエンドに返す
6. チャット画面にAI回答を表示

## AI参照APIフロー

DifyからDB情報を取得する場合：

1. Difyが `GET /api/ai/calendar/capabilities` で利用可能なツール一覧を取得
2. Difyが `POST /api/ai/calendar/query-batch` で複数の参照クエリを一括実行
   - 各クエリでツール名、フィルタ、リミットを指定
   - サーバがツール許可、フィルタ許可、リミット、日付範囲を検証
   - 検証通過後に安全にDB参照を実行
3. サーバが結果をDifyに返す
4. Difyが結果を解析して回答を生成

詳細は `docs/dify_chat.md` と `docs/ai_reference_api.md` を参照してください。

