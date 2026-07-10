"""
BD 提示词 docx 结构化入库

用法:
  python scripts/ingest_bd_docx.py
  python scripts/ingest_bd_docx.py --file "path/to/BD筛选提示词.docx"
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pipeline import IngestPipeline
from settings import DATA_PATH
from vectorstore import check_milvus_connection

DEFAULT_DOCX = r"d:\xwechat_files\wxid_i3hlr9ja1jug22_804f\msg\file\2026-07\BD筛选提示词.docx"


def main():
    parser = argparse.ArgumentParser(description="BD 提示词 docx 结构化入库")
    parser.add_argument("--file", default=DEFAULT_DOCX, help="docx 文件路径")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        raise FileNotFoundError(f"找不到文档: {args.file}")

    os.makedirs(DATA_PATH, exist_ok=True)
    target = os.path.join(DATA_PATH, "BD筛选提示词.docx")
    if os.path.abspath(args.file) != os.path.abspath(target):
        shutil.copy2(args.file, target)
        print(f"已复制文档到: {target}")

    check_milvus_connection()
    pipeline = IngestPipeline()
    result = pipeline.run(
        file_paths=[target],
        structured=True,
        rebuild=True,
        clear_all=False,
    )

    print("\n=== 入库摘要 ===")
    print(f"Collection: {result.collection_name}")
    print(f"Chunks: {result.chunk_count}")
    print(f"Embedding: {result.embedding_model}")


if __name__ == "__main__":
    main()
