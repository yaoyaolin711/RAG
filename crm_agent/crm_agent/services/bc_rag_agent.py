"""
B/C 类用户 RAG Agent

流程:
  用户提问 → 知识库检索 → 有相关命中 → 基于检索内容生成答案
                        → 无相关命中 → 闲聊/转移话题
  高意向关键词检测与升 A 转人工，由 WeChatMessageHandler 在路由层处理。
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from settings import LLM_MODEL_BASE_URL, LLM_MODEL_NAME, get_aliyun_api_key
from services.models import ReplyMode, RetrievedChunk, RouteType, UserTag, WeChatMessageResponse
from services.rag_retriever import (
    filter_answer_chunks,
    filter_relevant_chunks,
    format_chunks_for_prompt,
    retrieve_with_scores,
    sanitize_user_reply,
)
from services.user_tags import UserTagRepository

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """你是带货团队的商务同事，正在微信里跟达人/商家聊天——就是一个真人在回消息。
用户提问后，你手头有一些内部参考材料，请基于材料回答寄样、佣金、投流、产品推荐等问题。

【怎么说】
- 像真人发微信：口语化、短句、自然，不要书面腔
- 可以用「宝子」「亲」等，语气亲切但不油
- 禁止套话：不要「首先/其次/综上所述/希望以上内容对您有帮助」
- 不要 Markdown、不要编号列表，除非用户明确要对比多个选项
- 回复就是发给用户的话，不要加括号备注，不要暴露任何内部逻辑或文件名

【说多少】
- 优先 1～3 句话讲清楚，整体尽量控制在 80 字以内
- 简单问题 1 句即可；稍复杂也尽量不超过 120 字
- 只答用户问的点，不主动扩写背景、不重复用户原话

【说什么】
- 仅使用参考材料中的事实，不编造佣金比例、政策细节
- 为缩短字数时，只能删冗余修饰和套话，不能删或改关键事实（数字、条件、流程、限制必须保留）
- 若参考材料不够，口语化说「这块我得问下同事/帮你确认下」，别装懂

参考材料：
{context}
"""

CASUAL_SYSTEM_PROMPT = """你是带货团队的商务同事，正在微信里跟达人/商家聊天——就是一个真人在回消息。
当前问题在参考材料里没查到直接相关的内容。

【怎么说】
- 像真人发微信：口语化、短句、自然
- 可以用「宝子」「亲」等，语气亲切
- 禁止套话、Markdown，不要假装已经查到了资料
- 回复就是发给用户的话，不要加括号备注

【说多少】
- 1～2 句话，尽量 60 字以内
- 简单回应后可自然带一句（样品/佣金/爆品相关），别硬推销

【说什么】
- 不编造具体佣金数字、投流政策
- 对方若提到寄样、佣金、爆品、素材、跟拍，口语化表示「我帮你对接一下」即可"""


@dataclass
class BCRagStreamPrepare:
    """RAG 检索完成后，待流式生成的 LLM 上下文。"""

    user_id: str
    user_tag: UserTag
    reply_mode: ReplyMode
    relevant_chunks: list[RetrievedChunk]
    llm_messages: list


class BCRagAgentService:
    """B/C 类用户 RAG + 闲聊 Agent。"""

    def __init__(self, tag_repo: UserTagRepository | None = None):
        self._tag_repo = tag_repo
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = init_chat_model(
                model=LLM_MODEL_NAME,
                model_provider="openai",
                api_key=get_aliyun_api_key(),
                base_url=LLM_MODEL_BASE_URL,
                temperature=0.3,
            )
        return self._llm

    def prepare_stream(
        self,
        user_id: str,
        user_tag: UserTag,
        message: str,
    ) -> BCRagStreamPrepare:
        all_chunks = retrieve_with_scores(message)
        relevant_chunks = filter_answer_chunks(filter_relevant_chunks(all_chunks))

        if relevant_chunks:
            context = format_chunks_for_prompt(relevant_chunks)
            llm_messages = [
                SystemMessage(content=RAG_SYSTEM_PROMPT.format(context=context)),
                HumanMessage(content=message),
            ]
            reply_mode = ReplyMode.RAG
        else:
            llm_messages = [
                SystemMessage(content=CASUAL_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
            reply_mode = ReplyMode.CASUAL
            relevant_chunks = []

        return BCRagStreamPrepare(
            user_id=user_id,
            user_tag=user_tag,
            reply_mode=reply_mode,
            relevant_chunks=relevant_chunks,
            llm_messages=llm_messages,
        )

    def stream_answer(self, prepared: BCRagStreamPrepare) -> Iterator[str]:
        for chunk in self._get_llm().stream(prepared.llm_messages):
            if chunk.content:
                yield chunk.content

    def finalize_stream(
        self,
        prepared: BCRagStreamPrepare,
        full_text: str,
    ) -> WeChatMessageResponse:
        answer = sanitize_user_reply(full_text.strip())
        return WeChatMessageResponse(
            user_id=prepared.user_id,
            user_tag=prepared.user_tag,
            route=RouteType.RAG_AGENT,
            reply_mode=prepared.reply_mode,
            answer=answer,
            sources=prepared.relevant_chunks,
            tag_upgrade=None,
        )

    def handle(
        self,
        user_id: str,
        user_tag: UserTag,
        message: str,
    ) -> WeChatMessageResponse:
        prepared = self.prepare_stream(user_id, user_tag, message)
        parts: list[str] = []
        for piece in self.stream_answer(prepared):
            parts.append(piece)
        return self.finalize_stream(prepared, "".join(parts))
