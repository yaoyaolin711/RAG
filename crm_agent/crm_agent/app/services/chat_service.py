"""统一聊天服务 — 统一 Agent 入口。"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.unified_reply import UnifiedReplyAgent
from app.api.schemas import ChatMode
from app.services.chat_history import save_chat_turn
from services.models import UserTag
from services.user_tags import try_upgrade_user_tag
from vectorstore import check_milvus_connection

logger = logging.getLogger(__name__)

_unified_agent: UnifiedReplyAgent | None = None


def _get_unified_agent() -> UnifiedReplyAgent:
    global _unified_agent
    if _unified_agent is None:
        check_milvus_connection()
        _unified_agent = UnifiedReplyAgent()
    return _unified_agent


def _serialize_agent_result(
    result: dict,
    *,
    user_id: str,
    user_tag: str,
    talent_id: str,
    message: str,
    tag_upgrade: dict | None = None,
) -> dict[str, Any]:
    output = result.get("output", {})
    sources = output.get("sources", [])
    answer = output.get("result", "")
    reply_mode = output.get("reply_mode", "no_hit")

    return {
        "count": len(sources),
        "mode": "agent",
        "answer": answer,
        "user_id": user_id,
        "user_tag": user_tag,
        "talent_id": talent_id or None,
        "route": "unified_agent",
        "reply_mode": reply_mode,
        "rag_hit": output.get("rag_hit", False),
        "history_count": output.get("history_count", 0),
        "sources": sources,
        "tools_used": output.get("tools_used", []),
        "tag_upgrade": tag_upgrade,
        "received": {"direction": "receive", "message": message},
        "reply": {"direction": "send", "message": answer},
        "success": result.get("success", False),
    }


def handle_chat(
    message: str,
    mode: ChatMode = ChatMode.AUTO,
    user_id: str = "wx_demo_user_001",
    user_tag: str = "B",
    talent_id: str = "",
    contact_username: str = "",
) -> dict[str, Any]:
    """
    统一 Agent 处理入口。
    mode 参数保留兼容；所有消息均走 UnifiedReplyAgent（RAG 检索 → 读历史对话 → 拼接 → 生成）。
    """
    text = message.strip()
    if not text:
        raise ValueError("消息不能为空")

    tag = UserTag(user_tag.upper())
    effective_tag, upgrade_event = try_upgrade_user_tag(user_id, tag, text)
    tag_upgrade = None
    if upgrade_event:
        tag_upgrade = {
            "from": upgrade_event.from_tag.value,
            "to": upgrade_event.to_tag.value,
            "keywords": upgrade_event.trigger_keywords,
            "applied": upgrade_event.applied,
        }

    contact = contact_username.strip() or user_id
    profile_name = talent_id.strip() or user_id

    agent = _get_unified_agent()
    result = agent.invoke({
        "task": f"用户新消息：{text}",
        "context": {
            "message": text,
            "contact_username": contact,
            "talent_profile": f"昵称/ID：{profile_name}",
            "session_id": f"session_{user_id}",
            "history_limit": 50,
        },
    })

    if not result.get("success"):
        raise RuntimeError(result.get("error") or "Agent 处理失败")

    answer = (result.get("output") or {}).get("result", "")
    try:
        save_chat_turn(
            contact_username=contact,
            self_username=user_id,
            incoming_message=text,
            outgoing_message=answer,
        )
    except Exception:
        logger.exception("写入历史对话库失败（不影响本次回复）")

    return _serialize_agent_result(
        result,
        user_id=user_id,
        user_tag=effective_tag.value,
        talent_id=talent_id,
        message=text,
        tag_upgrade=tag_upgrade,
    )


def get_health() -> dict[str, Any]:
    milvus_status = "connected"
    try:
        check_milvus_connection()
    except Exception as e:
        milvus_status = f"error: {e}"
    return {
        "count": 0,
        "status": "ok" if milvus_status == "connected" else "degraded",
        "milvus": milvus_status,
        "llm": "configured",
        "agent": "unified_reply",
    }


def get_meta() -> dict[str, Any]:
    from settings import (
        KB_DOC_NAME,
        LLM_MODEL_NAME,
        RAG_COLLECTION_NAME,
        RAG_RELEVANCE_THRESHOLD,
        UPGRADE_TO_A_KEYWORDS,
    )

    return {
        "count": len(UPGRADE_TO_A_KEYWORDS),
        "version": "2.1.0",
        "agent": "unified_reply",
        "llm_model": LLM_MODEL_NAME,
        "collection": RAG_COLLECTION_NAME,
        "relevance_threshold": RAG_RELEVANCE_THRESHOLD,
        "kb_doc": KB_DOC_NAME,
        "upgrade_keywords_count": len(UPGRADE_TO_A_KEYWORDS),
        "modes": ["agent", "rag", "talent", "auto"],
        "routes": ["unified_agent"],
        "reply_modes": ["rag", "no_hit"],
        "user_tags": ["A", "B", "C"],
        "tools": ["search_knowledge_base"],
        "flow": "rag_retrieve → history_db → llm_generate",
    }
