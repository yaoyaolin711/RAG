"""A 类高意向用户处理（预留）。"""

from __future__ import annotations

from services.models import ReplyMode, RouteType, TagUpgradeEvent, UserTag, WeChatMessageResponse
from services.user_tags import extract_intent_topics, extract_mentioned_products


class PrioritySalesService:
    """A 类用户：合作/佣金等高意向，优先人工或专属话术跟进。"""

    def _build_answer(self, message: str) -> str:
        products = extract_mentioned_products(message)
        topics = extract_intent_topics(message)
        product_text = "、".join(products) if products else ""

        if product_text and "素材 / 案例 / 跟拍" in topics:
            return (
                f"亲，{product_text}这边素材和跟拍案例我整理下发你～"
                "方便留个称呼吗，方案和佣金也一并帮你对接。"
            )

        if product_text and "佣金 / 寄样 / 投流" in topics:
            return (
                f"亲，{product_text}的佣金和寄样政策我帮你对接一下～"
                "方便说下你的账号情况或留个称呼吗？"
            )

        if product_text:
            return (
                f"亲，{product_text}这边我帮你对接哈～"
                "方便说下你的账号情况或留个称呼，我尽快跟你细聊方案。"
            )

        if "佣金 / 寄样 / 投流" in topics:
            return (
                "亲，佣金和寄样这块我帮你对接一下哈～"
                "方便说下你主要想带什么品，或者留个称呼？"
            )

        if "素材 / 案例 / 跟拍" in topics:
            return (
                "亲，素材和跟拍案例我这边整理下发你～"
                "方便说下你想带哪个品，或者留个称呼？"
            )

        return (
            "亲，合作这块我帮你对接一下哈～方便说下你主要想带什么品，"
            "或者留个称呼，我这边尽快跟你细聊佣金和方案。"
        )

    def handle(
        self,
        user_id: str,
        message: str,
        *,
        tag_upgrade: TagUpgradeEvent | None = None,
    ) -> WeChatMessageResponse:
        return WeChatMessageResponse(
            user_id=user_id,
            user_tag=UserTag.A,
            route=RouteType.PRIORITY_SALES,
            reply_mode=ReplyMode.CASUAL,
            answer=self._build_answer(message),
            sources=[],
            tag_upgrade=tag_upgrade,
        )
