"""微信客服分流与 RAG 服务层数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UserTag(str, Enum):
    A = "A"  # 高意向，合作/佣金等
    B = "B"  # RAG 自动问答
    C = "C"  # RAG 自动问答


class RouteType(str, Enum):
    RAG_AGENT = "rag_agent"  # B/C 类：知识库检索 + Agent
    PRIORITY_SALES = "priority_sales"  # A 类：高优先级跟进（预留）
    UNSUPPORTED = "unsupported"


class ReplyMode(str, Enum):
    RAG = "rag"  # 命中知识库，基于检索内容回答
    CASUAL = "casual"  # 未命中知识库，闲聊/转移话题


@dataclass
class WeChatMessageRequest:
    user_id: str
    user_tag: UserTag
    message: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    content: str
    source: str
    chunk_id: str
    page: int
    score: float
    section: str = ""
    chunk_type: str = ""
    question: str = ""


@dataclass
class TagUpgradeEvent:
    user_id: str
    from_tag: UserTag
    to_tag: UserTag
    trigger_keywords: list[str]
    applied: bool  # 是否已写入数据库（stub 阶段为 False）
    message: str = ""


@dataclass
class WeChatMessageResponse:
    user_id: str
    user_tag: UserTag
    route: RouteType
    reply_mode: ReplyMode
    answer: str
    sources: list[RetrievedChunk] = field(default_factory=list)
    tag_upgrade: TagUpgradeEvent | None = None

    @property
    def tag_changed(self) -> bool:
        return self.tag_upgrade is not None
