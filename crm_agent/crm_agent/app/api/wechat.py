"""微信 RAG 客服 API（兼容层，转发至统一 Agent）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.response import api_ok
from app.api.schemas import ChatMode
from app.services.chat_service import get_health, get_meta, handle_chat

logger = logging.getLogger(__name__)
router = APIRouter()


class WeChatChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    user_id: str = Field(default="wx_demo_user_001", description="微信 openid")
    user_tag: str = Field(default="B", description="用户标签 A/B/C")
    contact_username: str = Field(default="", description="微信联系人 username")


@router.get("/health")
def wechat_health():
    return api_ok(get_health())


@router.post("/chat")
def wechat_chat(body: WeChatChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    try:
        data = handle_chat(
            message=body.message,
            mode=ChatMode.AUTO,
            user_id=body.user_id,
            user_tag=body.user_tag,
            contact_username=body.contact_username or body.user_id,
        )
        return api_ok(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta")
def wechat_meta():
    return api_ok(get_meta())
