# scripts/build_vectorstore.py
"""
此脚本负责：
1. 加载 data/ 目录下的锦丞商城知识库文档（TXT）
2. 使用本地 BGE-M3 向量化
3. 写入 Chroma 向量数据库（需先启动 chroma run --port 8001）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from settings import (
    CHROMA_CLIENT_MODE,
    CHROMA_COLLECTION_NAME,
    CHROMA_HOST,
    CHROMA_PATH,
    CHROMA_PORT,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_PATH,
)
from embedding import BgeM3ChromaEmbeddingFunction
from vectorstore import get_chroma_client, check_chroma_connection

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
    check_chroma_connection()
    client = get_chroma_client()
    ef = BgeM3ChromaEmbeddingFunction()

    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        print(f"已删除旧集合: {CHROMA_COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "锦丞商城知识库"},
    )

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

    batch_size = 16
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        collection.add(
            ids=[f"doc_{start + i}" for i in range(len(batch))],
            documents=[d.page_content for d in batch],
            metadatas=[d.metadata for d in batch],
        )
        print(f"已写入 {min(start + batch_size, len(docs))}/{len(docs)}")

    print(f"向量库构建完成: mode={CHROMA_CLIENT_MODE}, path={CHROMA_PATH}, collection={CHROMA_COLLECTION_NAME}")


if __name__ == "__main__":
    main()
