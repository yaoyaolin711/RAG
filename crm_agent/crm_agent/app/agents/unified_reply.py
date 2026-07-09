"""统一回复 Agent：先检索 RAG，再拼接历史对话，最后调用大模型生成回复。"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.agents.talent_base import TalentBaseAgent
from app.agents.tools.rag_tools import SEARCH_KNOWLEDGE_BASE_TOOL, search_knowledge_base
from app.agents.tools.registry import ToolRegistry
from app.llm import llm
from app.services.chat_history import get_export_messages
from services.rag_retriever import sanitize_user_reply

logger = logging.getLogger(__name__)

_RAG_HIT_APPENDIX = """

【内部参考（勿照搬原文，用自己的口语转述）】
{rag_context}
"""

_RAG_MISS_APPENDIX = """

【内部参考】
没查到足够相关的内容。别编佣金/政策；像同事一样说你会去确认，语气随意简短即可。
"""


class UnifiedReplyAgent(TalentBaseAgent):
    """
    统一 Agent 入口：
    1. 从数据库加载历史对话
    2. 强制先执行 RAG 检索（封装为工具，流水线调用）
    3. 将检索结果 + 历史 + 当前消息一并交给大模型生成回复
    """

    def __init__(self):
        super().__init__("unified_reply")
        self._ensure_tools_registered()

    @staticmethod
    def _ensure_tools_registered():
        if ToolRegistry.get("search_knowledge_base") is None:
            schema = ToolRegistry.get_schema("search_knowledge_base")
            if not schema:
                from app.agents.tools.rag_tools import RAG_TOOL_SCHEMAS
                schema = RAG_TOOL_SCHEMAS.get("search_knowledge_base")
            ToolRegistry.register(SEARCH_KNOWLEDGE_BASE_TOOL, schema)

    def _load_history(self, context: dict) -> list[dict]:
        if context.get("recent_history"):
            return context["recent_history"]
        contact = context.get("contact_username", "")
        limit = context.get("history_limit", 50)
        return get_export_messages(contact, limit)

    def _build_rag_appendix(self, rag_result: dict[str, Any]) -> tuple[str, str]:
        if rag_result.get("hit"):
            return _RAG_HIT_APPENDIX.format(rag_context=rag_result.get("context") or ""), "rag"
        return _RAG_MISS_APPENDIX, "no_hit"

    def build_messages(
        self,
        task: str = "",
        context: Optional[dict] = None,
        *,
        rag_appendix: str = "",
    ) -> list:
        context = context or {}
        system_content = self.system_prompt + rag_appendix

        if context:
            parts = []
            profile = context.get("talent_profile")
            if profile:
                parts.append(f"【用户画像】{profile}")

            history = self._load_history(context)
            if history:
                history_lines = []
                for msg in history[-20:]:
                    role = "我方" if msg.get("role") == "assistant" else "对方"
                    history_lines.append(f"{role}：{msg.get('content', '')}")
                parts.append("【历史对话】\n" + "\n".join(history_lines))

            if parts:
                system_content += "\n\n" + "\n\n".join(parts)

        messages = [{"role": "system", "content": system_content}]

        # 将结构化历史也放入 messages，便于模型理解多轮语境
        for msg in self._load_history(context)[-10:]:
            if msg.get("role") != "tool":
                messages.append(msg)

        user_content = context.get("message") or task
        if user_content:
            if not user_content.startswith("用户新消息") and not user_content.startswith("达人的新消息"):
                user_content = f"对方刚发来：{user_content}\n请直接回复这条微信（口语、简短，像真人打字）："
            messages.append({"role": "user", "content": user_content})
        return messages

    def invoke(self, input_data: dict) -> dict:
        task = input_data.get("task", "")
        context = dict(input_data.get("context") or {})
        message = (context.get("message") or task).strip()
        if message.startswith("达人的新消息："):
            message = message.replace("达人的新消息：", "", 1).strip()
        elif message.startswith("用户新消息："):
            message = message.replace("用户新消息：", "", 1).strip()
        context["message"] = message

        if not message:
            return {
                "agent": self.name,
                "output": {"result": "", "reply_mode": "no_hit", "sources": []},
                "success": False,
                "error": "消息不能为空",
            }

        # Step 1: 强制先检索知识库（工具封装，记录 tools_used）
        rag_result = search_knowledge_base(message)
        tools_used = [{
            "tool": "search_knowledge_base",
            "input": {"query": message},
            "success": True,
            "result": {
                "hit": rag_result["hit"],
                "count": rag_result["count"],
                "threshold": rag_result["threshold"],
            },
        }]

        rag_appendix, reply_mode = self._build_rag_appendix(rag_result)
        messages = self.build_messages(task, context, rag_appendix=rag_appendix)

        try:
            response = llm.invoke(
                messages,
                session_id=context.get("session_id"),
                agent_name=self.name,
            )
        except Exception as e:
            logger.exception("统一 Agent 生成失败")
            return {
                "agent": self.name,
                "output": {},
                "success": False,
                "error": str(e),
            }

        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                answer = response
                response = {}

        if isinstance(response, dict) and response.get("choices"):
            choice = response["choices"][0]
            answer = choice.get("message", {}).get("content", "") or ""
        else:
            answer = str(response) if not isinstance(response, dict) else ""

        answer = sanitize_user_reply(answer.strip())
        sources = rag_result.get("sources", [])
        history = self._load_history(context)

        return {
            "agent": self.name,
            "output": {
                "result": answer,
                "reply_mode": reply_mode,
                "sources": sources,
                "tools_used": tools_used,
                "history_count": len(history),
                "rag_hit": rag_result.get("hit", False),
            },
            "success": True,
            "error": None,
        }
