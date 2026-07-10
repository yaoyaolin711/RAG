# settings.py — RAG 微信客服配置（融合项目）

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

DEEPSEEK_KEY_ENV = "DEEPSEEK_KEY"
DEEPSEEK_KEY_FILE = os.getenv("DEEPSEEK_KEY_FILE", r"D:\DEEPSEEK_KEY.txt")

# LLM 配置（统一使用 DeepSeek 兼容 OpenAI 接口）
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
LLM_MODEL_BASE_URL = os.getenv(
    "LLM_MODEL_BASE_URL",
    "https://api.deepseek.com/v1",
)

# 服务端口（避免 3/5/8 开头）
API_PORT = int(os.getenv("API_PORT", "7120"))


def _read_key_from_file(path: str | Path) -> str | None:
    file_path = Path(path)
    if not file_path.is_file():
        return None
    content = file_path.read_text(encoding="utf-8").strip()
    return content or None


def get_deepseek_key() -> str:
    key = os.getenv(DEEPSEEK_KEY_ENV) or _read_key_from_file(DEEPSEEK_KEY_FILE)
    if not key:
        raise ValueError(
            f"未找到 DeepSeek API Key，请设置环境变量 {DEEPSEEK_KEY_ENV} "
            f"或在 {DEEPSEEK_KEY_FILE} 中写入密钥"
        )
    return key


def get_aliyun_api_key() -> str:
    """兼容旧调用，实际读取 DEEPSEEK_KEY。"""
    return get_deepseek_key()


# 本地 Embedding 模型（BGE-M3，稠密 + 稀疏）
BGE_M3_PATH = os.getenv("BGE_M3_PATH", r"D:\BGE-M3")
BGE_M3_DEVICE = os.getenv("BGE_M3_DEVICE", "cpu")

# Milvus 向量数据库（默认 Milvus Lite 本地文件）
MILVUS_PATH = os.getenv("MILVUS_PATH", r"D:\Milvus")
MILVUS_URI = os.getenv("MILVUS_URI", os.path.join(MILVUS_PATH, "milvus.db"))
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "jincheng_mall")

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
RAG_INDEX_MANIFEST_PATH = os.path.join(MILVUS_PATH, "rag_index_manifest.json")
RAG_DATA_PATH = DATA_PATH

# 混合检索权重（稠密 vs 稀疏）
MILVUS_DENSE_WEIGHT = float(os.getenv("MILVUS_DENSE_WEIGHT", "0.7"))
MILVUS_SPARSE_WEIGHT = float(os.getenv("MILVUS_SPARSE_WEIGHT", "0.3"))

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
