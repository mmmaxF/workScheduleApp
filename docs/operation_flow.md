# 処理フロー

## 基本フロー

```text
入力
→ draftとして保存
→ validate APIで検証
→ approve APIで承認
→ calendar_eventsへ正式登録
→ audit_logsへ記録
```

## ステップ1の範囲

ステップ1では、Dify・Excel・音声入力は使いません。  
ただし、将来それらの入口が増えても、まず `calendar_event_drafts` に入れる構造にしています。

## draft承認フロー

1. `/api/calendar/drafts` でdraftを作成する
2. `/api/calendar/drafts/{draft_id}/validate` で検証する
3. 問題がなければ `/api/calendar/drafts/{draft_id}/approve` を呼ぶ
4. `calendar_events` に正式予定が作成される
5. `/calendar` の月間表に表示される
