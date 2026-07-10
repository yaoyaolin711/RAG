# scripts/build_vectorstore.py
"""
此脚本负责：
1. 加载 data/ 目录下的锦丞商城知识库文档（TXT）
2. 使用本地 BGE-M3 向量化（稠密 + 稀疏）
3. 写入 Milvus 向量数据库
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_PATH,
    MILVUS_COLLECTION_NAME,
    MILVUS_URI,
)
from embedding import embed_documents_hybrid_batch
from vectorstore import check_milvus_connection, delete_collection, ensure_hybrid_collection, upsert_chunks

KNOWLEDGE_FILES = [
    "product_guide.txt",
    "after_sales_policy.txt",
    "promotion_member.txt",
]


def load_txt(filename: str) -> dict:
    file_path = os.path.join(DATA_PATH, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"page_content": content, "metadata": {"source": filename}}


def main():
    check_milvus_connection()

    try:
        delete_collection(MILVUS_COLLECTION_NAME)
        print(f"已删除旧集合: {MILVUS_COLLECTION_NAME}")
    except Exception:
        pass

    ensure_hybrid_collection(MILVUS_COLLECTION_NAME)

    raw_documents = [load_txt(name) for name in KNOWLEDGE_FILES]
    print(f"共加载了 {len(raw_documents)} 个文档。")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    docs: list[Document] = []
    for item in raw_documents:
        for split in text_splitter.split_text(item["page_content"]):
            docs.append(Document(page_content=split, metadata=item["metadata"]))
    print(f"共分块了 {len(docs)} 个文档。")

    ids = [f"doc_{i}" for i in range(len(docs))]
    texts = [d.page_content for d in docs]
    metadatas = [
        {
            "source": d.metadata.get("source", ""),
            "chunk_id": ids[i],
            "chunk_index": i,
            "page": 0,
            "section": "",
            "chunk_type": "",
        }
        for i, d in enumerate(docs)
    ]

    print("开始 BGE-M3 稠密+稀疏向量化...")
    dense_vectors, sparse_vectors = embed_documents_hybrid_batch(texts)
    upsert_chunks(MILVUS_COLLECTION_NAME, ids, texts, dense_vectors, sparse_vectors, metadatas)

    print(f"向量库构建完成: uri={MILVUS_URI}, collection={MILVUS_COLLECTION_NAME}")


if __name__ == "__main__":
    main()
