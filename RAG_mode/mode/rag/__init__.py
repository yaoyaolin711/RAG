"""RAG 入库工作流：文档加载 → 切分 → BGE-M3 向量化 → Chroma 持久化。"""

from rag.pipeline import IngestPipeline, IngestResult

__all__ = ["IngestPipeline", "IngestResult"]
