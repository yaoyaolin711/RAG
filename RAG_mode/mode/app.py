import html
import os
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import streamlit as st

from settings import (
    ALIYUN_API_KEY_ENV,
    CHROMA_CLIENT_MODE,
    CHROMA_PATH,
    KB_DOC_NAME,
    LLM_MODEL_NAME,
    RAG_COLLECTION_NAME,
    RAG_RELEVANCE_THRESHOLD,
    UPGRADE_KEYWORD_GROUPS,
    UPGRADE_TO_A_KEYWORDS,
    get_aliyun_api_key,
)
from services.models import ReplyMode, RouteType, UserTag
from services.wechat_handler import WeChatMessageHandler
from vectorstore import check_chroma_connection

st.set_page_config(
    page_title="BD 微信智能客服 · 模拟台",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💬",
)

CUSTOM_CSS = """
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1rem; padding-bottom: 1.5rem; max-width: 1180px; }

    .jc-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #2563eb 100%);
        border-radius: 14px; padding: 18px 24px; color: #f8fafc;
        margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
    }
    .jc-hero h1 { font-size: 1.45rem; font-weight: 700; margin: 0 0 6px 0; }
    .jc-hero p { margin: 0; color: #cbd5e1; font-size: 0.9rem; }
    .jc-badge {
        display: inline-block; background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.18); border-radius: 999px;
        padding: 3px 10px; font-size: 0.72rem; margin-right: 6px; margin-top: 10px;
    }

    .jc-tag {
        display: inline-flex; align-items: center; gap: 4px;
        border-radius: 8px; padding: 4px 10px; font-size: 0.78rem; font-weight: 700;
    }
    .jc-tag-a { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    .jc-tag-b { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
    .jc-tag-c { background: #e0e7ff; color: #3730a3; border: 1px solid #a5b4fc; }

    .jc-pipeline {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 14px;
        padding: 14px 16px; margin-bottom: 12px;
    }
    .jc-pipeline-title {
        font-size: 0.88rem; font-weight: 700; color: #334155;
        margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
    }
    .jc-step {
        display: flex; gap: 10px; align-items: flex-start;
        padding: 8px 0; border-bottom: 1px dashed #e2e8f0;
        font-size: 0.82rem; color: #475569;
    }
    .jc-step:last-child { border-bottom: none; }
    .jc-step-num {
        width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
        background: #f1f5f9; color: #64748b; font-size: 0.72rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
    }
    .jc-step-active .jc-step-num { background: #2563eb; color: #fff; }
    .jc-step-warn .jc-step-num { background: #f59e0b; color: #fff; }
    .jc-step-success .jc-step-num { background: #10b981; color: #fff; }
    .jc-step-upgrade .jc-step-num { background: #8b5cf6; color: #fff; }

    .jc-mode-pill {
        display: inline-block; border-radius: 999px; padding: 2px 10px;
        font-size: 0.75rem; font-weight: 600;
    }
    .jc-mode-rag { background: #dcfce7; color: #166534; }
    .jc-mode-casual { background: #ffedd5; color: #9a3412; }
    .jc-mode-sales { background: #fef3c7; color: #92400e; }

    .jc-upgrade-banner {
        background: linear-gradient(90deg, #f5f3ff, #ede9fe);
        border: 1px solid #c4b5fd; border-radius: 10px;
        padding: 10px 12px; margin: 8px 0; font-size: 0.82rem; color: #5b21b6;
    }

    .jc-chat-header {
        background: #f1f5f9; border-bottom: 1px solid #e2e8f0;
        padding: 12px 16px; margin: -16px -16px 14px -16px;
        font-weight: 600; color: #334155; font-size: 0.95rem;
    }
    .jc-msg-user, .jc-msg-bot {
        display: flex; gap: 10px; margin-bottom: 14px; align-items: flex-start;
    }
    .jc-msg-user { flex-direction: row-reverse; }
    .jc-avatar {
        width: 36px; height: 36px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0;
    }
    .jc-avatar-user { background: #dbeafe; }
    .jc-avatar-bot { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
    .jc-bubble {
        max-width: 75%; padding: 11px 14px; border-radius: 14px;
        line-height: 1.6; font-size: 0.93rem; white-space: pre-wrap; word-break: break-word;
    }
    .jc-bubble-user { background: #2563eb; color: white; border-bottom-right-radius: 4px; }
    .jc-bubble-bot {
        background: white; color: #1e293b; border: 1px solid #e2e8f0;
        border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .jc-stream-cursor {
        display: inline-block; width: 2px; height: 1em;
        background: #2563eb; margin-left: 2px; vertical-align: text-bottom;
        animation: jc-blink 0.75s step-end infinite;
    }
    @keyframes jc-blink { 50% { opacity: 0; } }
    .jc-source-card {
        background: #fff; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb;
        border-radius: 10px; padding: 10px 12px; margin-top: 8px;
        font-size: 0.82rem; color: #475569;
    }
    .jc-source-low { border-left-color: #f59e0b; opacity: 0.85; }
    .jc-source-title { font-weight: 600; color: #1e293b; margin-bottom: 4px; font-size: 0.85rem; }

    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%); }
    .jc-tip {
        background: white; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 10px 12px; margin-bottom: 8px; font-size: 0.86rem; color: #475569;
    }
    .jc-kw { display: inline-block; background: #f1f5f9; border-radius: 6px;
        padding: 2px 7px; margin: 2px; font-size: 0.72rem; color: #64748b; }
    .jc-kw-cat { font-size: 0.75rem; font-weight: 700; color: #475569; margin: 8px 0 4px 0; }
    .jc-kw-cat:first-child { margin-top: 0; }
    .jc-kb-card {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 12px 14px; margin-bottom: 12px; font-size: 0.82rem; color: #475569;
    }
    .jc-kb-title { font-weight: 700; color: #1e293b; margin-bottom: 8px; font-size: 0.88rem; }
    .jc-chunk-tag {
        display: inline-block; border-radius: 4px; padding: 1px 6px;
        font-size: 0.68rem; font-weight: 600; margin-right: 4px;
    }
    .jc-chunk-faq { background: #dcfce7; color: #166534; }
    .jc-chunk-upgrade { background: #fef3c7; color: #92400e; }
    .jc-chunk-reject { background: #fee2e2; color: #991b1b; }
    .jc-chunk-section { background: #e0e7ff; color: #3730a3; }
    .jc-flow-legend {
        display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;
        font-size: 0.78rem; color: #cbd5e1;
    }
    .jc-flow-item { display: flex; align-items: center; gap: 4px; }
</style>
"""

QUICK_BY_SCENARIO = {
    "📗 RAG · BD 知识库": [
        ("最近什么品比较好出单？", "rag"),
        ("什么佣金机制？这款佣金多少？", "rag"),
        ("有样品寄吗？做直播没有样品怎么播？", "rag"),
        ("可以做专属链接吗？", "rag"),
    ],
    "💬 闲聊 · 未命中": [
        ("今天天气怎么样？", "casual"),
        ("你吃饭了吗？", "casual"),
    ],
    "🔥 升级 A 类": [
        ("能否寄样？佣金能给到多少？", "upgrade"),
        ("护膝按摩器，推荐哪个爆品？", "upgrade"),
        ("有没有素材？跟拍有参考案例吗", "upgrade"),
        ("能不能投流？会不会有双佣金？", "upgrade"),
    ],
}

WELCOME_MESSAGE = (
    "在吗～我这边主要对接带货合作的，"
    "样品、佣金、选品、投流这些有不懂的直接问我就行哈。"
)

CHUNK_TYPE_LABELS = {
    "faq_qa": ("FAQ 问答", "jc-chunk-faq"),
    "upgrade_keyword": ("合作关键词", "jc-chunk-upgrade"),
    "reject_reason": ("不合作原因", "jc-chunk-reject"),
    "section_header": ("章节", "jc-chunk-section"),
}

TAG_LABELS = {
    UserTag.A: ("A 类 · 高意向", "jc-tag-a", "🔥"),
    UserTag.B: ("B 类 · RAG 问答", "jc-tag-b", "📘"),
    UserTag.C: ("C 类 · RAG 问答", "jc-tag-c", "📗"),
}


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def tag_badge(tag: UserTag) -> str:
    label, css, icon = TAG_LABELS[tag]
    return f'<span class="jc-tag {css}">{icon} {label}</span>'


def mode_badge(mode: ReplyMode | None, route: RouteType | None = None) -> str:
    if route == RouteType.PRIORITY_SALES:
        return '<span class="jc-mode-pill jc-mode-sales">高意向跟进</span>'
    if mode == ReplyMode.RAG:
        return '<span class="jc-mode-pill jc-mode-rag">RAG 知识库回答</span>'
    if mode == ReplyMode.CASUAL:
        return '<span class="jc-mode-pill jc-mode-casual">闲聊 · 转移话题</span>'
    return ""


def init_session_state():
    defaults = {
        "chat_history": [],
        "processing_question": None,
        "user_id": "wx_demo_user_001",
        "user_tag": UserTag.B,
        "last_response": None,
        "handler_ready": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def chunk_type_badge(chunk_type: str) -> str:
    label, css = CHUNK_TYPE_LABELS.get(chunk_type, (chunk_type or "文本", "jc-chunk-section"))
    return f'<span class="jc-chunk-tag {css}">{html.escape(label)}</span>'


def get_kb_stats() -> dict:
    try:
        from vectorstore import get_chroma_client
        from settings import RAG_COLLECTION_NAME
        col = get_chroma_client().get_collection(RAG_COLLECTION_NAME)
        count = col.count()
        peek = col.peek(limit=100)
        types: dict[str, int] = {}
        for meta in peek.get("metadatas") or []:
            t = meta.get("chunk_type", "unknown")
            types[t] = types.get(t, 0) + 1
        return {"count": count, "types": types, "ok": True}
    except Exception:
        return {"count": 0, "types": {}, "ok": False}


def render_hero():
    tag = st.session_state.user_tag
    kb = get_kb_stats()
    kb_line = f"{KB_DOC_NAME} · {kb['count']} chunks" if kb["ok"] else f"{KB_DOC_NAME} · 未入库"
    st.markdown(
        f"""
        <div class="jc-hero">
            <h1>BD 微信智能客服 · 模拟台</h1>
            <p>标签分流 → BGE-M3 检索 → LLM 生成 · 右侧实时展示处理链路</p>
            <span class="jc-badge">知识库 {kb_line}</span>
            <span class="jc-badge">BGE-M3 Dense</span>
            <span class="jc-badge">{RAG_COLLECTION_NAME}</span>
            <span class="jc-badge">A 类关键词 {len(UPGRADE_TO_A_KEYWORDS)} 个</span>
            <div class="jc-flow-legend">
                <span class="jc-flow-item">📘 B/C → RAG</span>
                <span class="jc-flow-item">💬 未命中 → 闲聊</span>
                <span class="jc-flow-item">🔥 关键词 → 升 A</span>
                <span class="jc-flow-item">⭐ A 类 → 高意向</span>
            </div>
            <div style="margin-top:10px">当前模拟用户：{tag_badge(tag)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_message(role: str, content: str):
    safe = html.escape(content).replace("\n", "<br>")
    is_user = role == "user"
    cls = "jc-msg-user" if is_user else "jc-msg-bot"
    av_cls = "jc-avatar-user" if is_user else "jc-avatar-bot"
    bub_cls = "jc-bubble-user" if is_user else "jc-bubble-bot"
    icon = "🧑" if is_user else "✨"
    st.markdown(
        f'<div class="{cls}"><div class="jc-avatar {av_cls}">{icon}</div>'
        f'<div class="jc-bubble {bub_cls}">{safe}</div></div>',
        unsafe_allow_html=True,
    )


def render_streaming_bot(placeholder, content: str, *, show_cursor: bool = True):
    safe = html.escape(content).replace("\n", "<br>")
    cursor = '<span class="jc-stream-cursor"></span>' if show_cursor else ""
    placeholder.markdown(
        f'<div class="jc-msg-bot"><div class="jc-avatar jc-avatar-bot">✨</div>'
        f'<div class="jc-bubble jc-bubble-bot">{safe}{cursor}</div></div>',
        unsafe_allow_html=True,
    )


def append_assistant_message(response):
    meta = {
        "route": response.route,
        "reply_mode": response.reply_mode,
        "sources_count": len(response.sources),
    }
    if response.tag_upgrade:
        u = response.tag_upgrade
        meta["tag_upgrade"] = {
            "from": u.from_tag.value,
            "to": u.to_tag.value,
            "keywords": "、".join(u.trigger_keywords),
            "applied": u.applied,
        }
    st.session_state.chat_history.append(
        {"role": "assistant", "content": response.answer, "meta": meta}
    )
    st.session_state.last_response = response
    if response.tag_upgrade:
        st.session_state.user_tag = response.user_tag


def queue_user_message(question: str):
    q = question.strip()
    if not q:
        return
    st.session_state.chat_history.append({"role": "user", "content": q})
    st.session_state.processing_question = q
    st.rerun()


def process_pending_message(question: str):
    """用户消息已在 chat_history 中，此处流式生成助手回复。"""
    st.session_state.processing_question = None
    try:
        session = st.session_state.wechat_handler.prepare_message_stream(
            user_id=st.session_state.user_id,
            user_tag=st.session_state.user_tag.value,
            message=question,
        )
        if session.instant:
            append_assistant_message(session.instant)
            st.rerun()
            return

        placeholder = st.empty()
        parts: list[str] = []
        for chunk in session.text_stream:
            parts.append(chunk)
            render_streaming_bot(placeholder, "".join(parts))

        response = session.finalize("".join(parts))
        append_assistant_message(response)
        st.rerun()
    except Exception as e:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"抱歉，处理出错了：{e}", "meta": {}}
        )
        st.rerun()


def render_retrieved_chunks(chunks: list, show_filtered: bool = False):
    if not chunks:
        st.info("未召回任何文档片段（score 均低于阈值或未检索到）")
        return
    for i, c in enumerate(chunks, 1):
        low = c.score < RAG_RELEVANCE_THRESHOLD
        card_cls = "jc-source-card jc-source-low" if low and show_filtered else "jc-source-card"
        body = html.escape(c.content).replace("\n", "<br>")
        type_badge = chunk_type_badge(c.chunk_type) if c.chunk_type else ""
        section_line = f" · {html.escape(c.section)}" if c.section else ""
        st.markdown(
            f"""
            <div class="{card_cls}">
                <div class="jc-source-title">
                    {type_badge}
                    📄 片段 {i} · {html.escape(c.source)}{section_line}
                    · score={c.score:.2f}
                    {" · ⚠️ 低于阈值" if low else " · ✅ 有效命中"}
                </div>
                {body}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kb_overview():
    kb = get_kb_stats()
    type_lines = ""
    if kb["types"]:
        for t, n in kb["types"].items():
            label, css = CHUNK_TYPE_LABELS.get(t, (t, "jc-chunk-section"))
            type_lines += f'<span class="jc-chunk-tag {css}">{html.escape(label)} ×{n}</span> '
    st.markdown(
        f"""
        <div class="jc-kb-card">
            <div class="jc-kb-title">📚 当前知识库</div>
            文档：<b>{html.escape(KB_DOC_NAME)}</b><br>
            向量库：<b>{RAG_COLLECTION_NAME}</b> · 共 <b>{kb["count"]}</b> 条 chunk<br>
            切分类型：{type_lines or "暂无数据，请运行 ingest_bd_docx.py"}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_panel(response):
    """右侧：展示本轮完整处理链路。"""
    if response is None:
        render_kb_overview()
        st.markdown(
            """
            <div class="jc-pipeline">
                <div class="jc-pipeline-title">⚙️ 处理链路</div>
                <div style="color:#94a3b8;font-size:0.82rem">
                    发送消息后，此处展示：标签分流 → RAG 检索 → 回复模式 → A 类升级
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    route_label = {
        RouteType.RAG_AGENT: "B/C 类 → RAG Agent",
        RouteType.PRIORITY_SALES: "A 类 → 高意向跟进",
        RouteType.UNSUPPORTED: "未支持",
    }.get(response.route, str(response.route))

    step2_cls = "jc-step-success" if response.sources else "jc-step-warn"
    step2_text = (
        f"召回 {len(response.sources)} 条有效片段（score ≥ {RAG_RELEVANCE_THRESHOLD}）"
        if response.sources
        else f"无有效命中（低于 {RAG_RELEVANCE_THRESHOLD}）→ 切换闲聊模式"
    )
    step3_text = {
        ReplyMode.RAG: "基于知识库内容生成回答",
        ReplyMode.CASUAL: "未命中知识库，友好闲聊并引导了解产品",
    }.get(response.reply_mode, "")

    upgrade_html = ""
    if response.tag_upgrade:
        u = response.tag_upgrade
        kws = "、".join(html.escape(k) for k in u.trigger_keywords)
        db_status = "✅ 已写库" if u.applied else "⏳ 待对接数据库（stub）"
        upgrade_html = f"""
        <div class="jc-step jc-step-upgrade">
            <div class="jc-step-num">↑</div>
            <div>
                <b>标签升级 {u.from_tag.value} → {u.to_tag.value}</b><br>
                触发词：{kws}<br>
                状态：{db_status}
            </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="jc-pipeline">
            <div class="jc-pipeline-title">⚙️ 本轮处理链路</div>
            <div class="jc-step jc-step-active">
                <div class="jc-step-num">1</div>
                <div><b>标签分流</b><br>{tag_badge(response.user_tag)} · {html.escape(route_label)}</div>
            </div>
            <div class="jc-step {step2_cls}">
                <div class="jc-step-num">2</div>
                <div><b>RAG 向量检索</b><br>{html.escape(step2_text)}</div>
            </div>
            <div class="jc-step jc-step-active">
                <div class="jc-step-num">3</div>
                <div><b>回复模式</b><br>{mode_badge(response.reply_mode, response.route)} · {html.escape(step3_text)}</div>
            </div>
            {upgrade_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if response.tag_upgrade:
        u = response.tag_upgrade
        st.markdown(
            f'<div class="jc-upgrade-banner">🏷️ 用户标签已从 <b>{u.from_tag.value}</b> 升级为 <b>{u.to_tag.value}</b>，'
            f'后续消息将走高意向跟进流程（左侧标签已同步更新）</div>',
            unsafe_allow_html=True,
        )

    if response.sources:
        with st.expander(f"📚 有效召回片段（{len(response.sources)} 条）", expanded=True):
            render_retrieved_chunks(response.sources)
    elif response.route == RouteType.RAG_AGENT:
        st.warning("知识库未命中：Agent 已进入闲聊模式，不会编造产品/政策细节。")


def render_sidebar():
    with st.sidebar:
        st.markdown("### 👤 模拟微信用户")
        st.text_input("用户 ID（openid）", key="user_id")
        tag_choice = st.radio(
            "用户标签",
            options=["B", "C", "A"],
            index=["B", "C", "A"].index(st.session_state.user_tag.value),
            key="user_tag_radio",
            help="B/C 走 RAG 问答；A 走高意向跟进；对话中可动态升级为 A",
        )
        st.session_state.user_tag = UserTag(tag_choice)

        label, css, icon = TAG_LABELS[st.session_state.user_tag]
        st.markdown(f'<div style="margin:8px 0">{tag_badge(st.session_state.user_tag)}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💡 快捷提问")
        st.caption("按场景测试：RAG / 闲聊 / 升级 A 类")
        for scenario, questions in QUICK_BY_SCENARIO.items():
            st.markdown(f"**{scenario}**")
            for q, kind in questions:
                if st.button(q, use_container_width=True, key=f"quick_{kind}_{q}"):
                    st.session_state.chat_history.append({"role": "user", "content": q})
                    st.session_state.processing_question = q
                    st.rerun()

        st.markdown("---")
        st.markdown("### 🏷️ A 类升级关键词")
        st.caption(f"共 {len(UPGRADE_TO_A_KEYWORDS)} 个 · 命中任一即 B/C → A")
        with st.expander("按分类查看", expanded=True):
            for cat, keywords in UPGRADE_KEYWORD_GROUPS.items():
                st.markdown(f'<div class="jc-kw-cat">{html.escape(cat)}</div>', unsafe_allow_html=True)
                kw_html = "".join(f'<span class="jc-kw">{html.escape(k)}</span>' for k in keywords)
                st.markdown(kw_html, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⚙️ 系统信息")
        api_ok = "已配置" if os.getenv(ALIYUN_API_KEY_ENV) else "未检测到"
        st.markdown(
            f"""
            <div class="jc-tip">🔑 API Key<br><b>{api_ok}</b></div>
            <div class="jc-tip">🤖 大模型<br><b>{LLM_MODEL_NAME}</b></div>
            <div class="jc-tip">🧠 Embedding<br><b>BGE-M3 本地</b></div>
            <div class="jc-tip">🗄️ 向量库<br><b>{RAG_COLLECTION_NAME}</b><br>{CHROMA_CLIENT_MODE} · {CHROMA_PATH}</div>
            <div class="jc-tip">📄 知识库<br><b>{KB_DOC_NAME}</b></div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.last_response = None
                st.session_state.processing_question = None
                st.rerun()
        with c2:
            if st.button("🔄 重置为 B 类", use_container_width=True):
                st.session_state.user_tag = UserTag.B
                st.rerun()


def render_chat_column():
    """消息区与输入区分开，避免 form 被 CSS overflow 遮挡。"""
    tag = st.session_state.user_tag
    with st.container(border=True):
        st.markdown(
            f'<div class="jc-chat-header">💬 对话 · {tag_badge(tag)} · '
            f'{html.escape(st.session_state.user_id)}</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.chat_history:
            render_message("assistant", WELCOME_MESSAGE)
        else:
            for msg in st.session_state.chat_history:
                render_message(msg["role"], msg["content"])
                meta = msg.get("meta")
                if meta and msg["role"] == "assistant":
                    badge = mode_badge(meta.get("reply_mode"), meta.get("route"))
                    if badge:
                        st.markdown(f'<div style="margin:-8px 0 12px 46px">{badge}</div>', unsafe_allow_html=True)

        if st.session_state.processing_question:
            process_pending_message(st.session_state.processing_question)

    disabled = bool(st.session_state.processing_question)
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([6, 1])
        with c1:
            question = st.text_input(
                "chat_question",
                placeholder="模拟微信消息，如：护膝有爆品吗？佣金能给到多少？",
                label_visibility="collapsed",
                disabled=disabled,
            )
        with c2:
            submitted = st.form_submit_button(
                "发送",
                type="primary",
                use_container_width=True,
                disabled=disabled,
            )
    return submitted, question


def main():
    inject_css()
    init_session_state()
    render_sidebar()

    try:
        if not st.session_state.handler_ready:
            with st.spinner("正在连接 Chroma 并初始化分流服务..."):
                check_chroma_connection()
                get_aliyun_api_key()
                st.session_state.wechat_handler = WeChatMessageHandler()
                st.session_state.handler_ready = True
    except Exception as e:
        render_hero()
        err = str(e)
        hints = []
        if "ALIYUN_API_KEY" in err or ("环境变量" in err and isinstance(e, ValueError)):
            hints.append(f'请设置 $env:ALIYUN_API_KEY="你的Key" 后重启 Streamlit')
        if "Chroma" in err or "chroma" in err.lower():
            hints.append(f"请确认 Chroma 路径存在：{CHROMA_PATH}")
            hints.append("请运行：python scripts/ingest_bd_docx.py")
        if not hints:
            hints = [f"设置 {ALIYUN_API_KEY_ENV}", f"确认 {CHROMA_PATH}", "运行 ingest_bd_docx.py"]
        st.error(f"初始化失败：{err}\n\n" + "\n".join(f"- {h}" for h in hints))
        st.stop()

    render_hero()

    col_chat, col_pipeline = st.columns([3, 2])
    with col_chat:
        submitted, question = render_chat_column()
    with col_pipeline:
        st.markdown("#### 📊 实时链路监控")
        render_pipeline_panel(st.session_state.last_response)

    if submitted and question and question.strip():
        queue_user_message(question)


main()

if __name__ == "__main__":
    import subprocess

    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is None:
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
