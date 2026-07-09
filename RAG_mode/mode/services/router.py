"""根据用户标签与消息进行分流。"""

from __future__ import annotations

from dataclasses import dataclass

from services.models import RouteType, UserTag


@dataclass
class RouteDecision:
    route: RouteType
    reason: str


def route_by_user_tag(user_tag: UserTag) -> RouteDecision:
    """
    微信消息入口分流：
    - B / C → RAG Agent 自动问答
    - A → 高意向跟进（预留，不走普通 RAG 闲聊）
    """
    if user_tag in (UserTag.B, UserTag.C):
        return RouteDecision(
            route=RouteType.RAG_AGENT,
            reason=f"用户标签 {user_tag.value} 类，进入 RAG 知识库问答",
        )
    if user_tag == UserTag.A:
        return RouteDecision(
            route=RouteType.PRIORITY_SALES,
            reason="用户标签 A 类（高意向），进入优先跟进流程",
        )
    return RouteDecision(route=RouteType.UNSUPPORTED, reason=f"未知标签: {user_tag}")
