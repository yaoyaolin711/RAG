"""
RAG 文档入库 CLI

用法:
  python scripts/ingest_documents.py                    # 入库 data/ 目录
  python scripts/ingest_documents.py --rebuild          # 重建 index
  python scripts/ingest_documents.py --dir path/to/docs # 指定目录
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pipeline import IngestPipeline
from settings import RAG_DATA_PATH
from vectorstore import check_milvus_connection


def main():
    parser = argparse.ArgumentParser(description="RAG 文档入库：加载 → 切分 → BGE-M3 → Milvus")
    parser.add_argument(
        "--dir",
        default=RAG_DATA_PATH,
        help=f"文档目录，默认 {RAG_DATA_PATH}",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="删除旧 collection 并重建 index（模型变更时必须使用）",
    )
    args = parser.parse_args()

    check_milvus_connection()
    pipeline = IngestPipeline()
    pipeline.run(data_dir=args.dir, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
