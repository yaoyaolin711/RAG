"""用户标签检测与升级（数据库写入预留 stub）。"""

from __future__ import annotations

import logging
from typing import Protocol

from settings import UPGRADE_KEYWORD_GROUPS, UPGRADE_TO_A_KEYWORDS
from services.models import TagUpgradeEvent, UserTag

# 含具体问题时优先 RAG 作答，不因升 A 被挡
_RAG_QUESTION_CUES = (
    "?", "？",
    "有没有", "多少", "怎么", "哪个", "哪款", "能否", "可以吗",
    "可不可以", "推荐", "案例", "素材", "跟拍", "爆品", "佣金", "寄样",
    "投流", "样品", "参考",
)
_RAG_PREFER_GROUPS = frozenset({
    "素材 / 案例 / 跟拍",
    "产品咨询 / 爆品",
    "佣金 / 寄样 / 投流",
})

logger = logging.getLogger(__name__)


class UserTagRepository(Protocol):
    """用户标签持久化接口，对接微信侧用户数据库。"""

    def update_tag(self, user_id: str, tag: UserTag) -> bool:
        """更新用户标签等级，成功返回 True。"""


class StubUserTagRepository:
    """
    占位实现：记录升级意图，暂不请求真实数据库。
    对接时替换为 HTTP/ORM 调用即可。
    """

    def update_tag(self, user_id: str, tag: UserTag) -> bool:
        logger.info(
            "[STUB] 待写入数据库: user_id=%s, new_tag=%s "
            "(请对接 POST /api/users/{user_id}/tag)",
            user_id,
            tag.value,
        )
        return False


def detect_upgrade_keywords(message: str) -> list[str]:
    """检测消息中是否包含 A 类升级关键词（长词优先，避免重复子串）。"""
    text = message.strip()
    if not text:
        return []
    text_lower = text.lower()
    matched: list[str] = []
    seen: set[str] = set()
    for kw in sorted(UPGRADE_TO_A_KEYWORDS, key=len, reverse=True):
        if kw.lower() in text_lower or kw in text:
            if kw not in seen:
                matched.append(kw)
                seen.add(kw)
    return matched


def extract_mentioned_products(message: str) -> list[str]:
    """从消息中提取已提及的品类词（长词优先）。"""
    text = message.strip()
    if not text:
        return []
    products: list[str] = []
    seen: set[str] = set()
    for kw in sorted(UPGRADE_KEYWORD_GROUPS.get("品类词", []), key=len, reverse=True):
        if kw in text and kw not in seen:
            products.append(kw)
            seen.add(kw)
    return products


def extract_intent_topics(message: str) -> list[str]:
    """提取用户关心的商务话题（素材/佣金/寄样等）。"""
    text = message.strip()
    if not text:
        return []
    topics: list[str] = []
    topic_map = {
        "素材 / 案例 / 跟拍": ["素材", "案例", "跟拍", "参考案例", "发图片"],
        "佣金 / 寄样 / 投流": ["佣金", "寄样", "样品", "投流", "双佣金"],
        "商务合作": ["合作", "代理", "加盟", "分销", "招商"],
    }
    for label, kws in topic_map.items():
        if any(kw in text for kw in kws):
            topics.append(label)
    return topics


def should_use_rag_for_message(message: str, trigger_keywords: list[str] | None = None) -> bool:
    """
    是否应走 RAG 回答本条消息（A 类或本轮升 A 均适用）。
    用户问了具体问题（素材/佣金/品类等）时，标签升级不挡知识库作答。
    """
    text = message.strip()
    if not text:
        return False
    if any(cue in text for cue in _RAG_QUESTION_CUES):
        return True
    if trigger_keywords:
        for group_name in _RAG_PREFER_GROUPS:
            group_kws = UPGRADE_KEYWORD_GROUPS.get(group_name, [])
            if any(kw in trigger_keywords for kw in group_kws):
                return True
    return False


def should_upgrade_to_a(user_tag: UserTag, message: str) -> tuple[bool, list[str]]:
    """仅 B/C 类用户可升级为 A。"""
    if user_tag not in (UserTag.B, UserTag.C):
        return False, []
    keywords = detect_upgrade_keywords(message)
    return bool(keywords), keywords


def try_upgrade_user_tag(
    user_id: str,
    user_tag: UserTag,
    message: str,
    repo: UserTagRepository | None = None,
) -> tuple[UserTag, TagUpgradeEvent | None]:
    """
    检测升级意图并尝试更新标签。
    返回 (当前有效标签, 升级事件或 None)。
    """
    should_upgrade, keywords = should_upgrade_to_a(user_tag, message)
    if not should_upgrade:
        return user_tag, None

    repository = repo or StubUserTagRepository()
    applied = repository.update_tag(user_id, UserTag.A)

    event = TagUpgradeEvent(
        user_id=user_id,
        from_tag=user_tag,
        to_tag=UserTag.A,
        trigger_keywords=keywords,
        applied=applied,
        message="检测到合作/佣金等高意向关键词，标签已标记升级为 A（待数据库对接）",
    )
    # 逻辑上视为 A，即使 stub 未真正写入 DB
    effective_tag = UserTag.A
    return effective_tag, event
