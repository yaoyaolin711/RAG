"""
RAG 检索测试示例

演示: Milvus 混合向量检索 → 可选 LLM 生成回答

用法:
  python scripts/query_rag.py "锦丞 Pro 无线耳机多少钱？"
  python scripts/query_rag.py "满多少免运费？" --with-llm
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from rag.index_manifest import check_index_consistency
from settings import (
    LLM_MODEL_BASE_URL,
    LLM_MODEL_NAME,
    RAG_COLLECTION_NAME,
    TOP_K,
    get_aliyun_api_key,
)
from vectorstore import check_milvus_connection, get_rag_vector_store


def retrieve(query: str, k: int = TOP_K):
    vector_store = get_rag_vector_store()
    docs = vector_store.similarity_search(query, k=k)
    return docs


def format_context(docs) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "-")
        page = doc.metadata.get("page", "-")
        parts.append(
            f"[{i}] source={source}, page={page}, chunk_id={chunk_id}\n{doc.page_content}"
        )
    return "\n\n".join(parts)


def answer_with_llm(query: str, context: str) -> str:
    llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        api_key=get_aliyun_api_key(),
        base_url=LLM_MODEL_BASE_URL,
        temperature=0.2,
    )
    messages = [
        SystemMessage(
            content="你是知识库问答助手。仅根据提供的检索上下文回答，不足则说明无法回答。"
        ),
        HumanMessage(content=f"上下文:\n{context}\n\n问题: {query}"),
    ]
    return llm.invoke(messages).content


def main():
    parser = argparse.ArgumentParser(description="RAG 检索测试")
    parser.add_argument("query", help="检索问题")
    parser.add_argument("--k", type=int, default=TOP_K, help="返回 top-k 条")
    parser.add_argument("--with-llm", action="store_true", help="检索后调用 LLM 生成回答")
    args = parser.parse_args()

    check_milvus_connection()
    consistent, msg = check_index_consistency()
    print(msg)
    if not consistent:
        print("警告: index 可能过期，检索结果仅供参考。请先 rebuild。")

    print(f"\n查询: {args.query}")
    print(f"Collection: {RAG_COLLECTION_NAME}\n")

    docs = retrieve(args.query, k=args.k)
    if not docs:
        print("未检索到相关文档，请先运行: python scripts/ingest_documents.py --rebuild")
        return

    context = format_context(docs)
    print("=== 检索结果 ===")
    print(context)

    if args.with_llm:
        print("\n=== LLM 回答 ===")
        try:
            answer = answer_with_llm(args.query, context)
            print(answer)
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            print("提示: 请设置环境变量 DEEPSEEK_KEY")


if __name__ == "__main__":
    main()
