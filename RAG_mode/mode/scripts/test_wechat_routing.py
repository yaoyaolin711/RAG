"""分流与标签升级单元测试（不依赖 LLM）。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.models import RouteType, UserTag
from services.priority_sales import PrioritySalesService
from services.router import route_by_user_tag
from services.user_tags import (
    StubUserTagRepository,
    detect_upgrade_keywords,
    should_upgrade_to_a,
    should_use_rag_for_message,
    try_upgrade_user_tag,
)
from services.wechat_handler import WeChatMessageHandler


class TestRouter:
    def test_bc_route_to_rag(self):
        for tag in (UserTag.B, UserTag.C):
            d = route_by_user_tag(tag)
            assert d.route == RouteType.RAG_AGENT

    def test_a_route_to_priority(self):
        d = route_by_user_tag(UserTag.A)
        assert d.route == RouteType.PRIORITY_SALES


class TestTagUpgrade:
    def test_detect_keywords(self):
        kws = detect_upgrade_keywords("想跟你们谈合作，佣金怎么算？")
        assert "合作" in kws
        assert "佣金" in kws

    def test_bc_can_upgrade(self):
        ok, kws = should_upgrade_to_a(UserTag.B, "有意向代理你们的产品")
        assert ok is True
        assert "有意向" in kws

    def test_a_cannot_upgrade_again(self):
        ok, _ = should_upgrade_to_a(UserTag.A, "谈合作")
        assert ok is False

    def test_stub_upgrade_not_applied(self):
        tag, event = try_upgrade_user_tag("u1", UserTag.C, "想了解佣金政策")
        assert tag == UserTag.A
        assert event is not None
        assert event.applied is False
        assert "佣金" in event.trigger_keywords

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("能否寄样？佣金能给到多少？", "能否寄样"),
            ("有没有素材？跟拍有参考案例吗", "有没有素材"),
            ("推荐哪个？拖鞋有爆品吗", "拖鞋"),
            ("护膝按摩器什么佣金拉满多少", "护膝"),
        ],
    )
    def test_image_keyword_list(self, message, expected):
        kws = detect_upgrade_keywords(message)
        assert expected in kws
        ok, _ = should_upgrade_to_a(UserTag.B, message)
        assert ok is True


class TestHandlerUpgradeRouting:
    def test_bc_keyword_immediately_routes_to_priority_sales(self):
        handler = WeChatMessageHandler()
        session = handler.prepare_message_stream("u1", UserTag.B, "想跟你们谈合作")
        assert session.instant is not None
        assert session.text_stream is None
        assert session.instant.route == RouteType.PRIORITY_SALES
        assert session.instant.user_tag == UserTag.A
        assert session.instant.tag_upgrade is not None
        assert session.instant.tag_upgrade.from_tag == UserTag.B

    def test_bc_material_question_upgrades_but_uses_rag(self):
        handler = WeChatMessageHandler()
        message = "有没有护膝的素材，跟拍有参考案例吗"
        session = handler.prepare_message_stream("u1", UserTag.B, message)
        assert session.instant is None
        assert session.text_stream is not None
        assert session.finalize is not None
        assert should_use_rag_for_message(message, detect_upgrade_keywords(message))

    def test_bc_normal_message_still_routes_to_rag(self):
        handler = WeChatMessageHandler()
        session = handler.prepare_message_stream("u1", UserTag.B, "今天天气不错")
        assert session.instant is None
        assert session.text_stream is not None
        assert session.finalize is not None


class TestPrioritySalesReply:
    def test_knee_pad_material_mentions_product(self):
        svc = PrioritySalesService()
        resp = svc.handle("u1", "有没有护膝的素材，跟拍有参考案例吗")
        assert "护膝" in resp.answer
        assert "素材" in resp.answer or "跟拍" in resp.answer
        assert "想带什么品" not in resp.answer

    def test_generic_cooperation_asks_product(self):
        svc = PrioritySalesService()
        resp = svc.handle("u1", "想跟你们谈合作")
        assert "想带什么品" in resp.answer or "称呼" in resp.answer
