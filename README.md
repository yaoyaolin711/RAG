# RAG Agent

融合 **crm_agent**（达人回复 Agent）与 **RAG_mode**（微信 BD 智能客服 + 知识库检索）。

## 快速开始

```bash
cd crm_agent/crm_agent
venv\Scripts\activate
python main.py
```

- 交互式文档：http://localhost:7120/docs
- 接口文档：[API.md](./API.md)

## 统一 API（推荐）

所有能力通过 **`POST /api/v1/chat`** 统一 Agent 调用：

```bash
curl -X POST http://localhost:7120/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "佣金能给到多少？",
    "user_id": "wx_openid_xxx",
    "contact_username": "微信联系人ID",
    "user_tag": "B"
  }'
```

流程：**RAG 检索 → 读历史对话 → 拼接上下文 → 大模型生成**（`reply_mode`: `rag` / `no_hit`；`mode` 参数已废弃语义，均走统一 Agent）

### 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | **主入口** — 统一聊天 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/meta` | 服务元信息 |
| GET | `/docs` | Swagger 交互文档 |
| GET | `/redoc` | ReDoc 文档 |

### 响应格式

```json
{
  "data": {
    "mode": "agent",
    "route": "unified_agent",
    "answer": "...",
    "reply_mode": "rag",
    "rag_hit": true,
    "sources": [],
    "history_count": 0,
    "tag_upgrade": null
  },
  "state": {"code": 0, "message": "ok"}
}
```

完整字段说明见 [API.md](./API.md)（v2.1.0）。

## 项目结构

```
RAG_Agent/
├── API.md                   # 接口文档
├── crm_agent/crm_agent/
│   ├── main.py              # API 入口 :7120
│   ├── app/api/v1.py        # 统一接口
│   ├── app/agents/          # UnifiedReplyAgent
│   ├── app/services/        # 聊天编排、历史对话
│   ├── services/            # RAG 检索、标签升级
│   └── data/                # 知识库文档、历史对话库
└── start_api.bat
```

对外仅通过 **`POST /api/v1/chat`** 完成全流程，无需额外前端。

## Streamlit 模拟台（RAG_mode）

```bash
cd RAG_mode/mode
streamlit run app.py
```

- 访问地址：http://localhost:7121

## 环境依赖

- `D:\Milvus` — 向量库 Milvus Lite（`rag_collection`，稠密+稀疏混合检索）
- `D:\BGE-M3` — BGE-M3 本地 Embedding 模型
- `D:\EmbeddingModel\BAAI\bge-m3` — Embedding 模型
- API Key：设置环境变量 `DEEPSEEK_KEY`（见各子项目 `.env.example`）

## 知识库入库

```bash
cd crm_agent/crm_agent
python scripts/ingest_bd_docx.py --file "path/to/BD筛选提示词.docx"
```
