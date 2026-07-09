"""向量库清理工具。"""

from __future__ import annotations

from pathlib import Path

from settings import CHROMA_PATH, RAG_INDEX_MANIFEST_PATH
from vectorstore import get_chroma_client


def clear_all_collections() -> list[str]:
    """删除 Chroma 中所有 collection，返回已删除名称列表。"""
    client = get_chroma_client()
    deleted: list[str] = []
    for col in client.list_collections():
        client.delete_collection(col.name)
        deleted.append(col.name)
        print(f"已删除 collection: {col.name}")
    return deleted


def clear_index_manifest() -> None:
    manifest = Path(RAG_INDEX_MANIFEST_PATH)
    if manifest.exists():
        manifest.unlink()
        print(f"已删除 index manifest: {manifest}")
