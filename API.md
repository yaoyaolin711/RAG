# RAG Agent API 接口文档

> 版本：v2.1.0  
> 基础地址：`http://localhost:7120`  
> 在线文档：[/docs](http://localhost:7120/docs) · [/redoc](http://localhost:7120/redoc)

---

## 统一响应格式

所有接口（成功、业务错误、参数校验失败、404、未捕获异常）均返回：

```json
{
  "data": { "count": 0 },
  "state": {
    "code": 0,
    "message": "ok"
  }
}
```

| state.code | 含义 |
|------------|------|
| `0` | 成功 |
| `400` | 请求参数错误（含 Pydantic 校验失败、消息为空） |
| `404` | 路径不存在 |
| `500` | 服务内部错误 |

> HTTP 状态码统一为 `200`，通过 `state.code` 判断成败。  
> 失败时 `data` 至少包含 `"count": 0`。

---

## 1. 统一聊天接口（主入口）

**`POST /api/v1/chat`**

由 **UnifiedReplyAgent** 处理。`mode` 参数保留兼容，**当前所有消息均走同一流水线，不区分 rag / talent**。

固定流程：

```
RAG 向量检索(Chroma + BGE-M3) → 读历史对话(SQLite) → 拼接上下文 → 大模型生成
```

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 用户/达人消息 |
| `user_id` | string | 否 | 会话 ID，默认 `wx_demo_user_001` |
| `user_tag` | string | 否 | A/B/C，用于高意向关键词升级检测，默认 `B` |
| `talent_id` | string | 否 | 达人昵称/ID，写入用户画像；为空则用 `user_id` |
| `contact_username` | string | 否 | 微信联系人 ID，用于读历史对话库；为空则用 `user_id` |
| `mode` | string | 否 | **已废弃语义**，保留字段兼容；传 `rag`/`talent`/`auto` 效果相同 |

### 响应字段（`data`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `count` | int | `sources` 条数 |
| `mode` | string | 固定 `"agent"` |
| `route` | string | 固定 `"unified_agent"` |
| `answer` | string | 生成的回复文本 |
| `reply_mode` | string | `rag`（知识库命中）/ `no_hit`（未命中兜底） |
| `rag_hit` | bool | 是否有有效知识库命中 |
| `user_id` | string | 请求中的会话 ID |
| `user_tag` | string | 升级后的有效标签 A/B/C |
| `talent_id` | string \| null | 达人 ID |
| `history_count` | int | 读到的历史对话条数 |
| `sources` | array | RAG 召回片段 |
| `tools_used` | array | 工具调用记录（含 `search_knowledge_base`） |
| `tag_upgrade` | object \| null | B/C 命中高意向词时的升级事件 |
| `received` | object | `{ direction: "receive", message }` |
| `reply` | object | `{ direction: "send", message }` |
| `success` | bool | Agent 是否成功 |

**`reply_mode` 说明：**
- `rag` — 知识库有有效命中（score ≥ 阈值，默认 0.45）
- `no_hit` — 未命中，按提示词「问问运营同事」兜底，不编造政策细节

### 请求示例

```bash
curl -X POST http://localhost:7120/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "佣金能给到多少？",
    "user_id": "wx_demo_user_001",
    "user_tag": "B",
    "contact_username": "wx_contact_001"
  }'
```

### 响应示例 — 知识库命中

```json
{
  "data": {
    "count": 2,
    "mode": "agent",
    "route": "unified_agent",
    "answer": "定向佣金大概 30-40%，具体看类目，我帮你查一下",
    "reply_mode": "rag",
    "rag_hit": true,
    "user_id": "wx_demo_user_001",
    "user_tag": "A",
    "talent_id": null,
    "history_count": 12,
    "sources": [
      {
        "content": "问题：什么佣金机制？...",
        "source": "BD筛选提示词.docx",
        "score": 0.70,
        "section": "一、常见问题（回复）",
        "chunk_type": "faq_qa",
        "question": "什么佣金机制"
      }
    ],
    "tools_used": [
      {
        "tool": "search_knowledge_base",
        "input": { "query": "佣金能给到多少？" },
        "success": true,
        "result": { "hit": true, "count": 2, "threshold": 0.45 }
      }
    ],
    "tag_upgrade": {
      "from": "B",
      "to": "A",
      "keywords": ["佣金能给到多少", "佣金"],
      "applied": false
    },
    "received": {
      "direction": "receive",
      "message": "佣金能给到多少？"
    },
    "reply": {
      "direction": "send",
      "message": "定向佣金大概 30-40%，具体看类目，我帮你查一下"
    },
    "success": true
  },
  "state": { "code": 0, "message": "ok" }
}
```

### 响应示例 — 未命中知识库

```json
{
  "data": {
    "count": 0,
    "mode": "agent",
    "route": "unified_agent",
    "answer": "这个我不太确定，我问下运营同事再回你",
    "reply_mode": "no_hit",
    "rag_hit": false,
    "user_id": "wx_demo_user_001",
    "user_tag": "B",
    "talent_id": null,
    "history_count": 0,
    "sources": [],
    "tools_used": [
      {
        "tool": "search_knowledge_base",
        "input": { "query": "你们公司上市了吗" },
        "success": true,
        "result": { "hit": false, "count": 0, "threshold": 0.45 }
      }
    ],
    "tag_upgrade": null,
    "received": { "direction": "receive", "message": "你们公司上市了吗" },
    "reply": { "direction": "send", "message": "这个我不太确定，我问下运营同事再回你" },
    "success": true
  },
  "state": { "code": 0, "message": "ok" }
}
```

### 处理流程

```
用户消息
  → 检测高意向关键词（B/C 可升级为 A，仅作 tag_upgrade 元数据返回，不写库）
  → Chroma 向量检索（BGE-M3，基于当前 message）
  → 读历史对话（SQLite，contact_username，最多 50 条）
  → 拼接【检索结果 + 历史 + 用户画像 + 当前消息】
  → 有相关命中 → reply_mode=rag
  → 无命中       → reply_mode=no_hit
  → 大模型生成口语化回复
  → 将本轮「对方消息 + 我方回复」写回 SQLite（供下次读取；`contact_username` ≠ `user_id` 时生效）
```

> `talent_id`、`tag_upgrade` 为 `null` 时，响应中可能省略对应字段（`response_model_exclude_none`）。

**历史对话库：**
- 默认路径：`crm_agent/crm_agent/data/wechat_messages/chat_export/exported_chats.db`
- 可通过环境变量 `EXPORT_DB_PATH` 覆盖
- 会话键为 `contact_username`（微信联系人唯一 ID，勿用昵称）

---

## 2. 健康检查

**`GET /api/v1/health`**

```bash
curl http://localhost:7120/api/v1/health
```

```json
{
  "data": {
    "count": 0,
    "status": "ok",
    "chroma": "connected",
    "llm": "configured",
    "agent": "unified_reply"
  },
  "state": { "code": 0, "message": "ok" }
}
```

| 字段 | 说明 |
|------|------|
| `status` | `ok`（Chroma 正常）/ `degraded`（Chroma 异常） |
| `chroma` | `connected` 或 `error: ...` |
| `agent` | 当前 Agent 名称 |

---

## 3. 服务元信息

**`GET /api/v1/meta`**

```bash
curl http://localhost:7120/api/v1/meta
```

```json
{
  "data": {
    "count": 42,
    "version": "2.1.0",
    "agent": "unified_reply",
    "llm_model": "deepseek-chat",
    "collection": "rag_collection",
    "relevance_threshold": 0.45,
    "kb_doc": "BD筛选提示词.docx",
    "upgrade_keywords_count": 42,
    "modes": ["agent", "rag", "talent", "auto"],
    "routes": ["unified_agent"],
    "reply_modes": ["rag", "no_hit"],
    "user_tags": ["A", "B", "C"],
    "tools": ["search_knowledge_base"],
    "flow": "rag_retrieve → history_db → llm_generate"
  },
  "state": { "code": 0, "message": "ok" }
}
```

> `modes` 中 `rag`/`talent`/`auto` 为历史兼容枚举；实际路由固定为 `unified_agent`。

---

## 4. 服务首页

### `GET /`

```json
{
  "data": {
    "count": 3,
    "service": "RAG Agent",
    "version": "2.1.0",
    "docs": "/docs",
    "redoc": "/redoc",
    "openapi": "/openapi.json",
    "api": "/api/v1",
    "endpoints": {
      "chat": "POST /api/v1/chat",
      "health": "GET /api/v1/health",
      "meta": "GET /api/v1/meta"
    }
  },
  "state": { "code": 0, "message": "ok" }
}
```

---

## 5. 兼容接口

### `POST /api/wechat/chat`

与 `POST /api/v1/chat` 相同，均调用 `handle_chat()` → `UnifiedReplyAgent`。请求体字段：

| 字段 | 说明 |
|------|------|
| `message` | 必填 |
| `user_id` | 默认 `wx_demo_user_001` |
| `user_tag` | 默认 `B` |
| `contact_username` | 为空则用 `user_id` |

响应格式与 `/api/v1/chat` 完全一致。

### `GET /api/wechat/health` / `GET /api/wechat/meta`

分别等同 `/api/v1/health`、`/api/v1/meta`。

### `POST /api/talents/{talent_id}/simulate`

达人消息模拟，内部走 `UnifiedReplyAgent`，但**不经过** `handle_chat()`，响应字段与 v1/chat 略有不同：

- 不触发 `tag_upgrade` 检测
- **不会**将对话写入 SQLite 历史库
- 响应中无 `answer`、`route`、`rag_hit`、`tools_used`、`user_id` 等字段

**请求体：**

```json
{
  "message": "你好，想了解一下合作",
  "contact_username": ""
}
```

**响应示例：**

```json
{
  "data": {
    "count": 1,
    "mode": "agent",
    "received": {
      "direction": "receive",
      "message": "你好，想了解一下合作",
      "intent": "simulate"
    },
    "reply": {
      "direction": "send",
      "message": "你好！欢迎来了解合作～...",
      "intent": "simulate_reply"
    },
    "sources": [],
    "reply_mode": "no_hit",
    "history_count": 0
  },
  "state": { "code": 0, "message": "ok" }
}
```

---

## 错误响应

所有错误均使用统一格式，HTTP 状态码为 `200`：

```json
{
  "data": { "count": 0 },
  "state": {
    "code": 400,
    "message": "message: Field required"
  }
}
```

### 参数错误（state.code = 400）

```json
{
  "data": { "count": 0 },
  "state": {
    "code": 400,
    "message": "消息不能为空"
  }
}
```

缺少 `message` 等 Pydantic 校验失败时同样返回上述格式，例如：

```json
{
  "data": { "count": 0 },
  "state": {
    "code": 400,
    "message": "message: Field required"
  }
}
```

### 服务错误（state.code = 500）

```json
{
  "data": { "count": 0 },
  "state": {
    "code": 500,
    "message": "Agent 处理失败"
  }
}
```

---

## 启动服务

```bash
cd crm_agent/crm_agent
venv\Scripts\activate
python main.py
```

或双击根目录 `start_api.bat`，然后访问 http://localhost:7120/docs 查看交互式文档。
