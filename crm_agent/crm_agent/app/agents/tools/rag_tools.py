"""RAG 知识库检索工具。"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from app.agents.tools.base import BaseTool, ToolOutput, tool
from services.rag_retriever import (
    filter_answer_chunks,
    filter_relevant_chunks,
    format_chunks_for_prompt,
    retrieve_with_scores,
)
from settings import RAG_RELEVANCE_THRESHOLD


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="用户问题，用于在知识库中做向量检索")


def search_knowledge_base(query: str) -> dict[str, Any]:
    """检索知识库，返回结构化结果（供 Agent 与工具共用）。"""
    all_chunks = retrieve_with_scores(query)
    relevant = filter_answer_chunks(filter_relevant_chunks(all_chunks))
    return {
        "query": query,
        "hit": bool(relevant),
        "threshold": RAG_RELEVANCE_THRESHOLD,
        "count": len(relevant),
        "sources": [
            {
                "content": c.content,
                "source": c.source,
                "score": c.score,
                "section": c.section,
                "chunk_type": c.chunk_type,
                "question": c.question,
            }
            for c in relevant
        ],
        "context": format_chunks_for_prompt(relevant),
        "chunks": relevant,
    }


@tool(
    name="search_knowledge_base",
    description="检索 RAG 知识库，查找与用户问题相关的 FAQ、政策、佣金、寄样等文档片段。回复前必须先调用此工具。",
)
class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = (
        "检索 RAG 知识库，查找与用户问题相关的 FAQ、政策、佣金、寄样等文档片段。"
        "回复前必须先调用此工具。"
    )
    input_model = SearchKnowledgeBaseInput

    def execute(self, input_data: Dict) -> ToolOutput:
        query = (input_data.get("query") or "").strip()
        if not query:
            return ToolOutput(success=False, error="query 不能为空")
        try:
            result = search_knowledge_base(query)
            return ToolOutput(success=True, result=result)
        except Exception as e:
            return ToolOutput(success=False, error=f"知识库检索失败: {e}")


SEARCH_KNOWLEDGE_BASE_TOOL = SearchKnowledgeBaseTool()

RAG_TOOL_SCHEMAS: dict[str, dict] = {}
_tool_instance = SEARCH_KNOWLEDGE_BASE_TOOL
RAG_TOOL_SCHEMAS[_tool_instance.name] = {
    "type": "function",
    "function": {
        "name": _tool_instance.name,
        "description": _tool_instance.description,
        "parameters": SearchKnowledgeBaseInput.model_json_schema(),
    },
}
