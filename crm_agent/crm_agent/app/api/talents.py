import logging

from fastapi import APIRouter, HTTPException

from app.agents.unified_reply import UnifiedReplyAgent
from app.api.response import api_ok
from app.api.schemas import TalentSimulateRequest, TalentSimulateResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_unified_agent = None


def _get_unified_agent():
    global _unified_agent
    if _unified_agent is None:
        _unified_agent = UnifiedReplyAgent()
    return _unified_agent


class SimulateRequest(TalentSimulateRequest):
    """兼容别名。"""


@router.post("/{talent_id}/simulate", response_model=TalentSimulateResponse)
def simulate_talent_message(talent_id: str, body: TalentSimulateRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    contact = body.contact_username.strip() or talent_id
    try:
        agent = _get_unified_agent()
        result = agent.invoke({
            "task": f"达人的新消息：{body.message}",
            "context": {
                "message": body.message,
                "contact_username": contact,
                "talent_profile": f"昵称：{talent_id}",
                "session_id": f"talent_{talent_id}",
            },
        })
        output = result.get("output", {})
        reply_text = output.get("result", "") if result.get("success") else f"AI回复失败({result.get('error')})"
    except Exception as e:
        logger.exception("AI回复失败: talent_id=%s", talent_id)
        reply_text = f"AI回复失败({type(e).__name__})"
        output = {}

    return api_ok({
        "count": 1,
        "mode": "agent",
        "received": {"direction": "receive", "message": body.message, "intent": "simulate"},
        "reply": {"direction": "send", "message": reply_text, "intent": "simulate_reply"},
        "sources": output.get("sources", []),
        "reply_mode": output.get("reply_mode", ""),
        "history_count": output.get("history_count", 0),
    })
