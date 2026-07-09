# settings.py — RAG 微信客服配置（融合项目）

import os
from pathlib import Path

from dotenv import load_dotenv

from keys import API_KEY

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# LLM 配置（统一使用 DeepSeek 兼容 OpenAI 接口）
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
LLM_MODEL_BASE_URL = os.getenv(
    "LLM_MODEL_BASE_URL",
    "https://api.deepseek.com/v1",
)
ALIYUN_API_KEY_ENV = "ALIYUN_API_KEY"


def get_aliyun_api_key() -> str:
    return API_KEY


# 本地 Embedding 模型（BGE-M3）
BGE_M3_PATH = os.getenv("BGE_M3_PATH", r"D:\EmbeddingModel\BAAI\bge-m3")
BGE_M3_DEVICE = os.getenv("BGE_M3_DEVICE", "cpu")

# Chroma 向量数据库
CHROMA_PATH = os.getenv("CHROMA_PATH", r"D:\Chroma")
CHROMA_HOST = os.getenv("CHROMA_HOST", "127.0.0.1")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "jincheng_mall")
CHROMA_CLIENT_MODE = os.getenv("CHROMA_CLIENT_MODE", "persistent")

# 知识库路径
DATA_PATH = os.getenv("DATA_PATH", str(PROJECT_ROOT / "data"))

# 文本分割参数
CHUNK_SIZE = 150
CHUNK_OVERLAP = 20

# RAG 入库专用配置
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "rag_collection")
RAG_CHUNK_SIZE = 600
RAG_CHUNK_OVERLAP = 80
RAG_EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MODEL_ID = "BAAI/bge-m3"
RAG_INDEX_MANIFEST_PATH = os.path.join(CHROMA_PATH, "rag_index_manifest.json")
RAG_DATA_PATH = DATA_PATH

# 检索参数
TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.45"))

# 用户标签与分流 — A 类升级关键词
UPGRADE_KEYWORD_GROUPS: dict[str, list[str]] = {
    "商务合作": [
        "合作", "有意向", "意向", "代理", "加盟", "商务合作", "谈合作",
        "合作方案", "分销", "招商", "入驻", "成为 partner", "partner",
    ],
    "佣金 / 寄样 / 投流": [
        "能否寄样", "可以申请样品吗", "寄样", "样品",
        "佣金能给到多少", "佣金拉满多少", "佣金拉满", "佣金",
        "能不能投流", "投流", "会不会有双佣金", "双佣金",
    ],
    "素材 / 案例 / 跟拍": [
        "有没有素材", "素材", "有没有参考案例", "参考案例", "跟拍", "直接发图片",
    ],
    "产品咨询 / 爆品": [
        "什么产品", "推荐哪个", "有没有哪个销量比较高", "爆品", "销量比较高",
    ],
    "品类词": [
        "拖鞋", "指压板", "拉力器", "弹力带", "沙袋", "护膝", "按摩器",
    ],
}
UPGRADE_TO_A_KEYWORDS = [kw for group in UPGRADE_KEYWORD_GROUPS.values() for kw in group]

KB_DOC_NAME = "BD筛选提示词.docx"
