"""向量库清理工具。"""

from __future__ import annotations

from pathlib import Path

from settings import RAG_INDEX_MANIFEST_PATH
from vectorstore import delete_collection, list_collections


def clear_all_collections() -> list[str]:
    """删除 Milvus 中所有 collection，返回已删除名称列表。"""
    deleted: list[str] = []
    for name in list_collections():
        delete_collection(name)
        deleted.append(name)
        print(f"已删除 collection: {name}")
    return deleted


def clear_index_manifest() -> None:
    manifest = Path(RAG_INDEX_MANIFEST_PATH)
    if manifest.exists():
        manifest.unlink()
        print(f"已删除 index manifest: {manifest}")
