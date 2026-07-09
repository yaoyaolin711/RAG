"""
微信消息统一入口

用法（后续对接微信 webhook）:
    from services.wechat_handler import WeChatMessageHandler

    handler = WeChatMessageHandler()
    response = handler.handle_message(
        user_id="wx_openid_123",
        user_tag="B",
        message="你们产品怎么收费？",
    )
    reply_text = response.answer
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from services.bc_rag_agent import BCRagAgentService
from services.models import ReplyMode, RouteType, TagUpgradeEvent, UserTag, WeChatMessageRequest, WeChatMessageResponse
from services.priority_sales import PrioritySalesService
from services.router import route_by_user_tag
from services.user_tags import (
    StubUserTagRepository,
    UserTagRepository,
    should_use_rag_for_message,
    try_upgrade_user_tag,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageStreamSession:
    """消息处理会话：即时回复或流式生成。"""

    instant: WeChatMessageResponse | None = None
    text_stream: Iterator[str] | None = None
    finalize: Callable[[str], WeChatMessageResponse] | None = None


class WeChatMessageHandler:
    """微信用户消息 → 标签分流 → RAG Agent / 高意向跟进。"""

    def __init__(self, tag_repo: UserTagRepository | None = None):
        self._tag_repo = tag_repo or StubUserTagRepository()
        self._bc_agent = BCRagAgentService(tag_repo=self._tag_repo)
        self._priority_sales = PrioritySalesService()

    def _resolve_effective_tag(
        self,
        user_id: str,
        tag: UserTag,
        message: str,
    ) -> tuple[UserTag, TagUpgradeEvent | None]:
        """B/C 命中高意向关键词时，本轮即升级为 A。"""
        if tag not in (UserTag.B, UserTag.C):
            return tag, None
        return try_upgrade_user_tag(user_id, tag, message, self._tag_repo)

    def _route_message(
        self,
        user_id: str,
        tag: UserTag,
        message: str,
    ) -> tuple[UserTag, TagUpgradeEvent | None, RouteType]:
        effective_tag, upgrade_event = self._resolve_effective_tag(user_id, tag, message)
        decision = route_by_user_tag(effective_tag)
        logger.info(
            "分流 user=%s tag=%s effective=%s route=%s reason=%s",
            user_id,
            tag.value,
            effective_tag.value,
            decision.route.value,
            decision.reason,
        )
        return effective_tag, upgrade_event, decision.route

    def handle_message(
        self,
        user_id: str,
        user_tag: str | UserTag,
        message: str,
        **extra,
    ) -> WeChatMessageResponse:
        tag = UserTag(user_tag) if isinstance(user_tag, str) else user_tag
        request = WeChatMessageRequest(
            user_id=user_id,
            user_tag=tag,
            message=message.strip(),
            extra=extra,
        )

        if not request.message:
            return WeChatMessageResponse(
                user_id=user_id,
                user_tag=tag,
                route=RouteType.UNSUPPORTED,
                reply_mode=ReplyMode.CASUAL,
                answer="您好，请问有什么可以帮您？",
                sources=[],
            )

        effective_tag, upgrade_event, route = self._route_message(
            user_id, tag, request.message
        )

        trigger_kws = upgrade_event.trigger_keywords if upgrade_event else []
        if route == RouteType.PRIORITY_SALES and should_use_rag_for_message(
            request.message, trigger_kws
        ):
            route = RouteType.RAG_AGENT
            logger.info(
                "分流 override user=%s → RAG（具体问题，升A不挡答）",
                user_id,
            )

        if route == RouteType.RAG_AGENT:
            response = self._bc_agent.handle(user_id, effective_tag, request.message)
            if upgrade_event:
                return WeChatMessageResponse(
                    user_id=response.user_id,
                    user_tag=effective_tag,
                    route=response.route,
                    reply_mode=response.reply_mode,
                    answer=response.answer,
                    sources=response.sources,
                    tag_upgrade=upgrade_event,
                )
            return response

        if route == RouteType.PRIORITY_SALES:
            return self._priority_sales.handle(
                user_id, request.message, tag_upgrade=upgrade_event
            )

        return WeChatMessageResponse(
            user_id=user_id,
            user_tag=effective_tag,
            route=RouteType.UNSUPPORTED,
            reply_mode=ReplyMode.CASUAL,
            answer="抱歉，暂无法处理您的请求，请联系商务同事。",
            sources=[],
        )

    def prepare_message_stream(
        self,
        user_id: str,
        user_tag: str | UserTag,
        message: str,
        **extra,
    ) -> MessageStreamSession:
        tag = UserTag(user_tag) if isinstance(user_tag, str) else user_tag
        request = WeChatMessageRequest(
            user_id=user_id,
            user_tag=tag,
            message=message.strip(),
            extra=extra,
        )

        if not request.message:
            return MessageStreamSession(
                instant=WeChatMessageResponse(
                    user_id=user_id,
                    user_tag=tag,
                    route=RouteType.UNSUPPORTED,
                    reply_mode=ReplyMode.CASUAL,
                    answer="您好，请问有什么可以帮您？",
                    sources=[],
                )
            )

        effective_tag, upgrade_event, route = self._route_message(
            user_id, tag, request.message
        )

        trigger_kws = upgrade_event.trigger_keywords if upgrade_event else []
        if route == RouteType.PRIORITY_SALES and should_use_rag_for_message(
            request.message, trigger_kws
        ):
            route = RouteType.RAG_AGENT

        if route == RouteType.RAG_AGENT:
            prepared = self._bc_agent.prepare_stream(user_id, effective_tag, request.message)

            def finalize(text: str) -> WeChatMessageResponse:
                response = self._bc_agent.finalize_stream(prepared, text)
                if upgrade_event:
                    return WeChatMessageResponse(
                        user_id=response.user_id,
                        user_tag=effective_tag,
                        route=response.route,
                        reply_mode=response.reply_mode,
                        answer=response.answer,
                        sources=response.sources,
                        tag_upgrade=upgrade_event,
                    )
                return response

            return MessageStreamSession(
                text_stream=self._bc_agent.stream_answer(prepared),
                finalize=finalize,
            )

        if route == RouteType.PRIORITY_SALES:
            return MessageStreamSession(
                instant=self._priority_sales.handle(
                    user_id, request.message, tag_upgrade=upgrade_event
                )
            )

        return MessageStreamSession(
            instant=WeChatMessageResponse(
                user_id=user_id,
                user_tag=effective_tag,
                route=RouteType.UNSUPPORTED,
                reply_mode=ReplyMode.CASUAL,
                answer="抱歉，暂无法处理您的请求，请联系商务同事。",
                sources=[],
            )
        )
