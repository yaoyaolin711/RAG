# settings.py
# 锦丞商城 RAG Demo 配置文件

import os

# LLM 配置（阿里云 DashScope 兼容 OpenAI 接口）
LLM_MODEL_NAME = "qwen3.7-plus"
LLM_MODEL_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ALIYUN_API_KEY_ENV = "ALIYUN_API_KEY"


def get_aliyun_api_key() -> str:
    api_key = os.getenv(ALIYUN_API_KEY_ENV)
    if not api_key:
        raise ValueError(f"未设置环境变量 {ALIYUN_API_KEY_ENV}，请先配置阿里云 API Key")
    return api_key


# 本地 Embedding 模型（BGE-M3）
BGE_M3_PATH = r"D:\EmbeddingModel\BAAI\bge-m3"
BGE_M3_DEVICE = "cpu"  # 有 GPU 可改为 "cuda"

# Chroma 向量数据库
CHROMA_PATH = r"D:\Chroma"
CHROMA_HOST = "127.0.0.1"
CHROMA_PORT = 8001
CHROMA_COLLECTION_NAME = "jincheng_mall"
# persistent: 直连 D:\Chroma 本地文件（推荐，无需启动服务）
# http: 通过 chroma run --path D:\Chroma --port 8001 连接
CHROMA_CLIENT_MODE = "persistent"

# 知识库路径
DATA_PATH = "data"

# 文本分割参数（锦丞 Demo 旧配置，build_vectorstore.py 仍使用）
CHUNK_SIZE = 150
CHUNK_OVERLAP = 20

# RAG 入库专用配置
RAG_COLLECTION_NAME = "rag_collection"
RAG_CHUNK_SIZE = 600  # tokens，范围 500~800
RAG_CHUNK_OVERLAP = 80  # tokens
RAG_EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MODEL_ID = "BAAI/bge-m3"
RAG_INDEX_MANIFEST_PATH = os.path.join(CHROMA_PATH, "rag_index_manifest.json")
RAG_DATA_PATH = DATA_PATH  # 默认文档目录，可通过 CLI 覆盖

# 检索参数
TOP_K = 3
RAG_RELEVANCE_THRESHOLD = 0.45  # similarity_search_with_relevance_scores 阈值，低于视为未命中

# 用户标签与分流 — A 类升级关键词（分组维护，命中任一即升级）
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

# 知识库文档
KB_DOC_NAME = "BD筛选提示词.docx"
