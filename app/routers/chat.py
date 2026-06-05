import json
import logging
import os
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import success, error
from ..services import add_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/chat/dify-proxy")
async def dify_proxy(request: Request, db: Session = Depends(get_db)):
    """Proxy for UI chat to Dify Workflow - keeps Dify API key server-side"""
    import httpx

    body = await request.json()
    message = body.get("message", "")
    year = body.get("year")
    month = body.get("month")
    conversation_history = body.get("conversation_history", [])

    if not message:
        return error("INVALID_REQUEST", "メッセージが空です")

    # Dify Workflow API configuration
    dify_workflow_api_url = os.getenv("DIFY_WORKFLOW_API_URL", "")
    dify_workflow_api_key = os.getenv("DIFY_WORKFLOW_API_KEY", "")

    if not dify_workflow_api_key:
        logger.warning("DIFY_WORKFLOW_API_KEY not configured")
        return error("DIFY_NOT_CONFIGURED", "Dify Workflow APIキーが設定されていません")

    logger.info(f"Dify Workflow proxy called: year={year}, month={month}")
    add_audit_log(db, "dify_workflow_proxy", "system", None, request={
        "year": year,
        "month": month,
        "message_length": len(message)
    })

    try:
        async with httpx.AsyncClient() as client:
            # Build capabilities for AI reference tools
            capabilities = {
                "tools": [
                    {
                        "name": "calendar_events_search",
                        "max_limit": 100,
                        "allowed_filters": [
                            "year",
                            "month",
                            "date_from",
                            "date_to",
                            "member_name",
                            "source_type",
                        ],
                    },
                    {
                        "name": "calendar_members_list",
                        "max_limit": 100,
                        "allowed_filters": ["is_active"],
                    },
                    {
                        "name": "calendar_capacity_summary",
                        "max_limit": 50,
                        "allowed_filters": [
                            "year",
                            "month",
                            "date_from",
                            "date_to",
                            "department",
                        ],
                    },
                ]
            }

            # Build inputs with all required fields for Workflow API
            inputs = {
                "query": message,
                "current_year": str(year) if year else "2026",
                "current_month": str(month) if month else "6",
                "capabilities": json.dumps(capabilities, ensure_ascii=False),
            }

            # Add conversation history if available
            if conversation_history:
                inputs["conversation_history"] = json.dumps(conversation_history, ensure_ascii=False)

            response = await client.post(
                dify_workflow_api_url,
                headers={
                    "Authorization": f"Bearer {dify_workflow_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": inputs,
                    "response_mode": "blocking",
                    "user": "rd-ict",
                },
                timeout=60.0
            )

            if response.status_code == 200:
                data = response.json()
                # Workflow API response structure: data.outputs.final_answer
                reply = data.get("data", {}).get("outputs", {}).get("final_answer", "")
                if not reply:
                    reply = data.get("data", {}).get("outputs", {}).get("result", "")
                if not reply:
                    reply = data.get("data", {}).get("result", "")
                if not reply:
                    reply = str(data)
                logger.info(f"Dify Workflow proxy response received: {len(reply)} chars")
                return success({"reply": reply}, "AI応答を取得しました")
            else:
                logger.error(f"Dify Workflow API error: {response.status_code} - {response.text}")
                return error("DIFY_API_ERROR", f"Dify Workflow APIエラー: {response.status_code}", 
                            {"status_code": response.status_code, "detail": response.text})
    except Exception as e:
        logger.error(f"Dify Workflow proxy error: {str(e)}")
        return error("DIFY_PROXY_ERROR", f"Dify Workflowプロキシエラー: {str(e)}")
