"""Chroma 向量库连接与检索封装。"""

import chromadb
from langchain_chroma import Chroma

from settings import (
    CHROMA_CLIENT_MODE,
    CHROMA_COLLECTION_NAME,
    CHROMA_HOST,
    CHROMA_PATH,
    CHROMA_PORT,
    RAG_COLLECTION_NAME,
)
from embedding import get_embedding_model


def get_chroma_client():
    """获取 Chroma 客户端。默认直连本地 D:\\Chroma 持久化目录。"""
    if CHROMA_CLIENT_MODE == "http":
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_vector_store(collection_name: str | None = None) -> Chroma:
    """获取 Chroma 集合，用于 RAG 检索。默认锦丞 Demo 集合。"""
    return Chroma(
        client=get_chroma_client(),
        collection_name=collection_name or CHROMA_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
    )


def get_rag_vector_store() -> Chroma:
    """获取 RAG 入库 pipeline 使用的 rag_collection 集合。"""
    return get_vector_store(RAG_COLLECTION_NAME)


def check_chroma_connection() -> None:
    """检查 Chroma 是否可用。"""
    client = get_chroma_client()
    client.heartbeat()
