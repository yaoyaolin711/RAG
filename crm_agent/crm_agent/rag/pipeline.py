"""
RAG 入库 Pipeline
==================

Document Loader → TextSplitter → BGE-M3 Batch Embedding → Chroma PersistentClient

    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌────────────┐
    │  Documents  │───▶│ TextSplitter │───▶│ BGE-M3 (batch)  │───▶│   Chroma   │
    │ txt/md/pdf  │    │ 600tok/80ov  │    │ dense+normalize │    │ persistent │
    └─────────────┘    └──────────────┘    └─────────────────┘    └────────────┘
                              │
                              ▼
                     metadata: source, page, chunk_id
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document

from embedding import embed_documents_batch, get_embedding_model_fingerprint
from rag.chunking import split_documents
from rag.index_manifest import IndexManifest, check_index_consistency
from rag.loaders import load_documents_from_dir, load_documents_from_paths
from rag.store_utils import clear_all_collections, clear_index_manifest
from rag.structured_docx import load_structured_docx
from settings import RAG_COLLECTION_NAME, RAG_EMBEDDING_BATCH_SIZE
from vectorstore import get_chroma_client


@dataclass
class IngestResult:
    raw_document_count: int
    chunk_count: int
    collection_name: str
    embedding_model: str

    def __str__(self) -> str:
        return (
            f"入库完成: {self.chunk_count} chunks "
            f"({self.raw_document_count} 原始文档页) → "
            f"collection={self.collection_name}, model={self.embedding_model}"
        )


class IngestPipeline:
    """LangChain 编排的 RAG 数据入库工作流。"""

    def __init__(
        self,
        collection_name: str = RAG_COLLECTION_NAME,
        batch_size: int = RAG_EMBEDDING_BATCH_SIZE,
    ):
        self.collection_name = collection_name
        self.batch_size = batch_size

    def run(
        self,
        data_dir: str | None = None,
        file_paths: list[str] | None = None,
        rebuild: bool = False,
        structured: bool = False,
        clear_all: bool = False,
    ) -> IngestResult:
        """
        执行完整入库流程。

        Args:
            data_dir: 文档目录（递归加载 txt/md/pdf）
            file_paths: 指定文件或目录列表（与 data_dir 二选一）
            rebuild: True 时删除旧 collection 并重建
            structured: True 时对 docx 做结构化切分（不再二次 token 切分）
            clear_all: True 时清空 Chroma 全部 collection 与 manifest
        """
        if clear_all:
            clear_all_collections()
            clear_index_manifest()

        consistent, msg = check_index_consistency()
        print(msg)
        if not consistent and not rebuild and not clear_all:
            raise RuntimeError("Index 不一致，请使用 --rebuild 重建索引。")

        if structured and file_paths:
            chunks: list[Document] = []
            for path in file_paths:
                chunks.extend(load_structured_docx(path))
            raw_count = len(chunks)
        elif data_dir:
            raw_docs = load_documents_from_dir(data_dir)
            chunks = split_documents(raw_docs)
            raw_count = len(raw_docs)
        elif file_paths:
            raw_docs = load_documents_from_paths(file_paths)
            chunks = split_documents(raw_docs)
            raw_count = len(raw_docs)
        else:
            raise ValueError("必须指定 data_dir 或 file_paths")

        if not chunks:
            raise ValueError("切分后无有效 chunk，请检查文档内容。")

        client = get_chroma_client()
        if rebuild or clear_all:
            try:
                client.delete_collection(self.collection_name)
                print(f"已删除旧 collection: {self.collection_name}")
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "RAG knowledge base", "hnsw:space": "cosine"},
        )

        self._batch_upsert(collection, chunks)

        manifest = IndexManifest.current()
        manifest.save()

        fp = get_embedding_model_fingerprint()
        result = IngestResult(
            raw_document_count=raw_count,
            chunk_count=len(chunks),
            collection_name=self.collection_name,
            embedding_model=fp["model_id"],
        )
        print(result)
        return result

    def _batch_upsert(self, collection, chunks: list[Document]) -> None:
        """批量 embedding + 写入 Chroma，每个 chunk 含 text / vector / metadata。"""
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for chunk in chunks:
            chunk_id = chunk.metadata["chunk_id"]
            ids.append(chunk_id)
            texts.append(chunk.page_content)
            meta = {
                "source": str(chunk.metadata.get("source", "unknown")),
                "chunk_id": chunk_id,
                "chunk_index": int(chunk.metadata.get("chunk_index", 0)),
                "page": int(chunk.metadata.get("page", 0)),
                "section": str(chunk.metadata.get("section", "")),
                "chunk_type": str(chunk.metadata.get("chunk_type", "")),
            }
            for key in ("question", "keyword", "reason"):
                value = chunk.metadata.get(key)
                if value:
                    meta[key] = str(value)[:500]
            metadatas.append(meta)

        print(f"开始 batch embedding，共 {len(texts)} 条，batch_size={self.batch_size} ...")
        embeddings = embed_documents_batch(texts, batch_size=self.batch_size)

        write_batch = 64
        for start in range(0, len(ids), write_batch):
            end = start + write_batch
            collection.upsert(
                ids=ids[start:end],
                documents=texts[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )
            print(f"  已写入 {min(end, len(ids))}/{len(ids)}")
