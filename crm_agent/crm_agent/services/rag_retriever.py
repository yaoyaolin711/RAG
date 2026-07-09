"""RAG 知识库检索封装。"""

from __future__ import annotations

import re

from langchain_core.documents import Document

from settings import RAG_RELEVANCE_THRESHOLD, TOP_K
from services.models import RetrievedChunk
from vectorstore import get_rag_vector_store

# 仅供内部分流/升级，不能作为回答依据喂给 LLM
INTERNAL_CHUNK_TYPES = frozenset({"upgrade_keyword", "section_header"})

_SYSTEM_HINT_RE = re.compile(r"[（(]\s*系统提示[：:][^）)]*[）)]")


def retrieve_with_scores(query: str, k: int = TOP_K) -> list[RetrievedChunk]:
    """向量检索并返回带 relevance score 的结果。"""
    store = get_rag_vector_store()
    results = store.similarity_search_with_relevance_scores(query, k=k)
    chunks: list[RetrievedChunk] = []
    for doc, score in results:
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                source=str(doc.metadata.get("source", "unknown")),
                chunk_id=str(doc.metadata.get("chunk_id", "")),
                page=int(doc.metadata.get("page", 0)),
                score=float(score),
                section=str(doc.metadata.get("section", "")),
                chunk_type=str(doc.metadata.get("chunk_type", "")),
                question=str(doc.metadata.get("question", "")),
            )
        )
    return chunks


def filter_relevant_chunks(
    chunks: list[RetrievedChunk],
    threshold: float | None = None,
) -> list[RetrievedChunk]:
    """按相关性阈值过滤，仅保留有效命中。"""
    min_score = threshold if threshold is not None else RAG_RELEVANCE_THRESHOLD
    return [c for c in chunks if c.score >= min_score]


def filter_answer_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """去掉内部元数据 chunk，只保留可对外回答的 FAQ/政策内容。"""
    return [c for c in chunks if c.chunk_type not in INTERNAL_CHUNK_TYPES]


def sanitize_user_reply(text: str) -> str:
    """去掉误生成的括号说明、Markdown、句末波浪号等，保证用户只看到真人话术。"""
    cleaned = _SYSTEM_HINT_RE.sub("", text)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\d+[.、)]\s*", "", cleaned, flags=re.MULTILINE)
    # 真人很少每句末尾带～，模型爱滥用，统一去掉
    cleaned = re.sub(r"[～~]+(?=\s*$)", "", cleaned)
    cleaned = re.sub(r"[～~]+(?=[。！？，,.])", "", cleaned)
    cleaned = re.sub(r"([。！？，,.])\s*[～~]+", r"\1", cleaned)
    return cleaned.strip()


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[{i}] 来源={c.source}, 相关度={c.score:.2f}\n{c.content}"
        )
    return "\n\n".join(parts)


def doc_to_retrieved(doc: Document, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        content=doc.page_content,
        source=str(doc.metadata.get("source", "unknown")),
        chunk_id=str(doc.metadata.get("chunk_id", "")),
        page=int(doc.metadata.get("page", 0)),
        score=score,
    )
