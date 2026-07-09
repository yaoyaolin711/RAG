"""
RAG Agent 统一 API v1

所有消息由 UnifiedReplyAgent 处理：
  RAG 检索 → 读历史对话(DB) → 拼接上下文 → 大模型生成回复
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.response import api_ok
from app.api.schemas import ChatRequest, ChatResponse, HealthResponse, MetaResponse
from app.services.chat_service import get_health, get_meta, handle_chat

router = APIRouter()


@router.post(
    "/chat",
    summary="统一聊天接口（Unified Agent）",
    description="""
**处理流程（每条消息固定执行）：**

1. **强制**检索 RAG 知识库（`search_knowledge_base` 工具，基于当前 `message`）
2. 从 SQLite 导出库读取 `contact_username` 对应的历史对话（最多 50 条）
3. 将【检索结果 + 历史对话 + 当前消息】拼接后交给大模型生成回复
4. 有命中 → `reply_mode=rag`；无命中 → `reply_mode=no_hit`（提示问问运营同事）

**参数说明：**
- `contact_username`：微信联系人 ID，用于读历史（为空则用 `user_id`）
- `talent_id`：达人昵称/ID，写入用户画像
- `mode`：保留兼容，传 rag/talent/auto 效果相同，均走 UnifiedReplyAgent
""",
    response_model=ChatResponse,
    response_model_exclude_none=True,
)
def unified_chat(body: ChatRequest):
    try:
        data = handle_chat(
            message=body.message,
            mode=body.mode,
            user_id=body.user_id,
            user_tag=body.user_tag,
            talent_id=body.talent_id,
            contact_username=body.contact_username,
        )
        return api_ok(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="健康检查", response_model=HealthResponse)
def unified_health():
    return api_ok(get_health())


@router.get("/meta", summary="服务元信息", response_model=MetaResponse)
def unified_meta():
    return api_ok(get_meta())
