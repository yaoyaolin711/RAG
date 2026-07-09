"""统一 API 请求/响应模型（OpenAPI 文档用）。"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    """保留兼容；当前所有取值均走 UnifiedReplyAgent，不触发分流。"""

    RAG = "rag"
    TALENT = "talent"
    AUTO = "auto"


class ApiState(BaseModel):
    code: int = Field(0, description="0=成功，非0=失败")
    message: str = Field("ok", description="状态描述")


class SourceItem(BaseModel):
    content: str = Field(..., description="召回片段内容")
    source: str = Field(..., description="来源文档")
    score: float = Field(..., description="相关度分数 0~1")
    section: str = Field("", description="所属章节")
    chunk_type: str = Field("", description="片段类型：faq_qa / upgrade_keyword 等")
    question: str = Field("", description="FAQ 对应问题（如有）")


class ToolUsedItem(BaseModel):
    tool: str = Field(..., description="工具名称")
    input: dict[str, Any] = Field(default_factory=dict, description="工具入参")
    success: bool = Field(True, description="是否调用成功")
    result: dict[str, Any] = Field(default_factory=dict, description="工具返回摘要")


class MessageEnvelope(BaseModel):
    direction: str = Field(..., description="receive 或 send")
    message: str = Field(..., description="消息正文")
    intent: str | None = Field(None, description="simulate 接口专用")


class TagUpgrade(BaseModel):
    from_tag: str = Field(..., alias="from", description="原标签")
    to_tag: str = Field(..., alias="to", description="新标签")
    keywords: list[str] = Field(default_factory=list, description="触发关键词")
    applied: bool = Field(False, description="是否已写入数据库（当前为 stub）")

    model_config = {"populate_by_name": True}


class ChatData(BaseModel):
    count: int = Field(0, description="sources 条数")
    mode: str = Field("agent", description="固定 agent")
    route: str = Field("unified_agent", description="固定 unified_agent")
    answer: str = Field(..., description="生成的回复文本")
    reply_mode: str = Field("", description="rag / no_hit")
    rag_hit: bool = Field(False, description="知识库是否有效命中")
    user_id: str = Field("", description="用户/会话 ID")
    user_tag: str = Field("", description="有效标签 A/B/C")
    talent_id: str | None = Field(None, description="达人 ID")
    history_count: int = Field(0, description="读到的历史对话条数")
    sources: list[SourceItem] = Field(default_factory=list, description="RAG 召回片段")
    tools_used: list[ToolUsedItem] = Field(default_factory=list, description="工具调用记录")
    tag_upgrade: TagUpgrade | None = Field(None, description="标签升级事件")
    received: MessageEnvelope = Field(..., description="收到的用户消息")
    reply: MessageEnvelope = Field(..., description="发送的回复")
    success: bool = Field(True, description="Agent 是否成功")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户/达人消息内容")
    mode: ChatMode = Field(
        ChatMode.AUTO,
        description="保留兼容，当前均走 UnifiedReplyAgent，传 rag/talent/auto 效果相同",
    )
    user_id: str = Field("wx_demo_user_001", description="微信 openid 或会话 ID")
    user_tag: str = Field("B", description="用户标签 A/B/C，用于高意向升级检测")
    talent_id: str = Field("", description="达人昵称/ID，写入用户画像")
    contact_username: str = Field("", description="微信联系人 username，用于读取历史对话")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "佣金能给到多少？",
                    "user_id": "wx_demo_user_001",
                    "user_tag": "B",
                    "contact_username": "wx_contact_001",
                },
                {
                    "message": "你好，想了解一下合作",
                    "talent_id": "达人小明",
                },
            ]
        }
    }


class ChatResponse(BaseModel):
    data: ChatData
    state: ApiState


class HealthData(BaseModel):
    count: int = 0
    status: str = Field("ok", description="ok / degraded")
    chroma: str = Field("unknown", description="connected 或 error: ...")
    llm: str = "configured"
    agent: str = Field("unified_reply", description="当前 Agent 名称")


class HealthResponse(BaseModel):
    data: HealthData
    state: ApiState


class MetaData(BaseModel):
    count: int = 0
    version: str = "2.1.0"
    agent: str = "unified_reply"
    llm_model: str = ""
    collection: str = ""
    relevance_threshold: float = 0.45
    kb_doc: str = ""
    upgrade_keywords_count: int = 0
    modes: list[str] = Field(default_factory=lambda: ["agent", "rag", "talent", "auto"])
    routes: list[str] = Field(default_factory=lambda: ["unified_agent"])
    reply_modes: list[str] = Field(default_factory=lambda: ["rag", "no_hit"])
    user_tags: list[str] = Field(default_factory=lambda: ["A", "B", "C"])
    tools: list[str] = Field(default_factory=lambda: ["search_knowledge_base"])
    flow: str = "rag_retrieve → history_db → llm_generate"


class MetaResponse(BaseModel):
    data: MetaData
    state: ApiState


class TalentSimulateRequest(BaseModel):
    message: str = Field(..., min_length=1, description="达人消息")
    contact_username: str = Field("", description="联系人 ID，为空则用 talent_id")


class TalentSimulateData(BaseModel):
    count: int = 1
    mode: str = "agent"
    received: MessageEnvelope
    reply: MessageEnvelope
    sources: list[SourceItem] = Field(default_factory=list)
    reply_mode: str = ""
    history_count: int = 0


class TalentSimulateResponse(BaseModel):
    data: TalentSimulateData
    state: ApiState


class UnifiedResponse(BaseModel):
    data: dict[str, Any]
    state: ApiState
