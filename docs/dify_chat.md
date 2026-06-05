# Difyチャット連携

## 概要

このアプリではDify AIプラットフォームと連携し、ユーザーが自然言語で勤務予定について質問できるAIアシスタントチャット機能を提供します。

## アーキテクチャ

```
ユーザー (ブラウザ)
  ↓
/api/chat/dify-proxy (FastAPI)
  ↓
Dify Chat API
  ↓
Dify Workflow
  ↓
/api/ai/calendar/query-batch (FastAPI) [必要な場合]
  ↓
データベース
```

## セキュリティ設計

### APIキー管理

- **DIFY_CHAT_API_KEY**: サーバ側の `.env` にのみ保存
- ブラウザには露出しない
- `/api/chat/dify-proxy` でサーバがDify APIを呼び出す

### 読み取り専用アクセス

- DifyがDBに直接アクセスできない
- Difyが使用できるのは `/api/ai/calendar/*` の参照専用APIのみ
- 登録・更新・削除系APIはDifyから呼び出せない

### 認証

- AI参照APIには `AI_READ_API_KEY` によるBearer認証
- Dify WorkflowがAI参照APIを呼ぶ際に使用

## APIエンドポイント

### POST /api/chat/dify-proxy

UIからDifyへ安全にメッセージを送信するプロキシAPI。

**リクエスト:**

```json
{
  "message": "明日のRDは？",
  "year": 2026,
  "month": 6
}
```

**レスポンス:**

```json
{
  "ok": true,
  "data": {
    "reply": "明日（6月2日）のRDはAさん、Bさんが担当予定です。"
  },
  "message": "AI応答を取得しました"
}
```

## Dify Workflow設計

### 推奨フロー

1. **入力受信**: ユーザー質問とカレンダーコンテキスト（year, month）を受け取る
2. **Planner LLM**: DB参照の要否を判断
3. **ツール選択**: 必要な参照ツールとフィルタを決定
4. **HTTP Request**: `/api/ai/calendar/query-batch` を呼び出し
5. **結果評価**: 取得したデータで十分か判断
6. **反復**: 必要なら次のiterationで追加クエリ
7. **回答生成**: 十分な情報が揃ったら回答を作成
8. **応答**: UIへ回答を返す

### HTTP Requestノード設定

**エンドポイント:**
```
https://your-server.com/api/ai/calendar/query-batch
```

**ヘッダー:**
```
Authorization: Bearer {AI_READ_API_KEY}
Content-Type: application/json
```

**リクエストボディ:**
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

## 環境変数設定

`.env` に以下を追加してください：

```bash
# Dify Chat API設定
DIFY_CHAT_API_URL=https://api.dify.ai/v1/chat-messages
DIFY_CHAT_API_KEY=your-dify-chat-api-key

# AI参照API認証用（Dify Workflowが使用）
AI_READ_API_KEY=your-secure-read-api-key
```

## UI実装

### チャット窓口

- `/calendar` 画面のタブ内に配置
- ChatGPT風のダークテーマUI
- ユーザー質問と現在表示中のyear/monthを送信
- AI回答をチャット画面に表示

### JavaScript実装

```javascript
const response = await fetch("/api/chat/dify-proxy", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    message,
    year: parseInt(year),
    month: parseInt(month)
  }),
});
```

## 監査ログ

以下の操作は `audit_logs` に記録されます：

- `dify_chat_proxy`: チャットプロキシ呼び出し（質問長、年月のみ記録）
- `ai_capabilities`: AIツール一覧取得
- `ai_query`: 単一AIクエリ実行
- `ai_query_batch`: バッチAIクエリ実行（iteration数、成功数のみ）

**注意:** 質問全文や取得データ全文は大量保存されません。

## ログ

アプリログには以下が記録されます：

- AI capabilities取得
- AI query実行（ツール名、返却件数）
- AI query-batch実行（iteration番号、ツール名、返却件数）
- 認証エラー
- Dify proxy呼び出し

**注意:** APIキーやトークンはログに出力されません。

## 制限事項

- AI参照APIは読み取り専用
- 1回のバッチクエリで最大3つのツール実行
- 各ツールのリミット上限あり（50-100件）
- 日付範囲の最大制限あり（31-365日）
- 更新系操作は許可されない

## トラブルシューティング

### AI応答が返ってこない

1. `.env` の `DIFY_CHAT_API_KEY` が設定されているか確認
2. Dify API URLが正しいか確認
3. サーバログでエラーを確認

### DifyがAI参照APIを呼べない

1. `.env` の `AI_READ_API_KEY` が設定されているか確認
2. Dify WorkflowのHTTP Requestノードで正しいAuthorizationヘッダーを設定しているか確認
3. サーバログで認証エラーを確認

### AIがDB情報を参照できない

1. Dify WorkflowでHTTP Requestノードが正しく設定されているか確認
2. `/api/ai/calendar/capabilities` でツール一覧が取得できるか確認
3. フィルタ条件が正しいか確認
