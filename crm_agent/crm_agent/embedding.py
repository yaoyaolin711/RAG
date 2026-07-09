"""本地 BGE-M3 Embedding，兼容 LangChain 与 Chroma。"""

from __future__ import annotations

from typing import List

from chromadb.api.types import EmbeddingFunction as ChromaEmbeddingFunction
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from settings import BGE_M3_DEVICE, BGE_M3_PATH, EMBEDDING_MODEL_ID, RAG_EMBEDDING_BATCH_SIZE

_model_instance: SentenceTransformer | None = None


def get_sentence_transformer(model_path: str | None = None) -> SentenceTransformer:
    global _model_instance
    path = model_path or BGE_M3_PATH
    if _model_instance is None:
        _model_instance = SentenceTransformer(path, device=BGE_M3_DEVICE)
    return _model_instance


def _encode(texts: List[str], model_path: str | None = None) -> List[List[float]]:
    model = get_sentence_transformer(model_path)
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_tensor=False,
    )
    return embeddings.tolist()


class BgeM3Embeddings(Embeddings):
    """LangChain Embeddings 接口，供 langchain-chroma 检索时使用。"""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or BGE_M3_PATH

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return _encode(texts, self.model_path)

    def embed_query(self, text: str) -> List[float]:
        return _encode([text], self.model_path)[0]


class BgeM3ChromaEmbeddingFunction(ChromaEmbeddingFunction):
    """Chroma EmbeddingFunction 接口，供写入向量库时使用。"""

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or BGE_M3_PATH

    def __call__(self, input: List[str]) -> List[List[float]]:
        return _encode(list(input), self.model_path)

    @property
    def dim(self) -> int:
        return 1024


def get_embedding_model() -> BgeM3Embeddings:
    return BgeM3Embeddings()


def embed_documents_batch(
    texts: List[str],
    batch_size: int | None = None,
    model_path: str | None = None,
) -> List[List[float]]:
    """批量 dense embedding，禁止逐条 encode。"""
    if not texts:
        return []
    size = batch_size or RAG_EMBEDDING_BATCH_SIZE
    model = get_sentence_transformer(model_path)
    all_embeddings: List[List[float]] = []
    for start in range(0, len(texts), size):
        batch = texts[start : start + size]
        vectors = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > size,
            convert_to_tensor=False,
            batch_size=size,
        )
        all_embeddings.extend(vectors.tolist())
    return all_embeddings


def get_embedding_model_fingerprint() -> dict:
    """返回 embedding 模型指纹，用于 index 一致性校验。"""
    return {
        "model_id": EMBEDDING_MODEL_ID,
        "model_path": BGE_M3_PATH,
        "normalize_embeddings": True,
        "embedding_type": "dense",
    }
