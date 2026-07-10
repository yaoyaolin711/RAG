import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool

from settings import TOP_K, LLM_MODEL_NAME, LLM_MODEL_BASE_URL, get_aliyun_api_key
from vectorstore import get_vector_store, check_milvus_connection

check_milvus_connection()
vector_store = get_vector_store()


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """根据用户的电商相关问题检索锦丞商城知识库协助回答"""
    retrieved_docs = vector_store.similarity_search(query, k=TOP_K)
    serialized = ""
    for doc in retrieved_docs:
        serialized += f"文件名：{doc.metadata.get('source', '未知')} \n 内容：{doc.page_content}\n\n"
    return serialized, retrieved_docs


model = init_chat_model(
    model=LLM_MODEL_NAME,
    model_provider="openai",
    api_key=get_aliyun_api_key(),
    base_url=LLM_MODEL_BASE_URL,
)
prompt = """你是锦丞商城的智能客服助手，名字叫锦小丞。请先调用工具从知识库检索与用户问题相关的内容，再根据检索结果回答。
            回答时语气亲切、简洁专业。如果信息不足以回答，请说"抱歉，我暂时无法根据现有信息回答该问题。"
            """
agent = create_agent(model, tools=[retrieve_context], system_prompt=prompt)

for stream_mode, response in agent.stream(
        {"messages": [{"role": "user", "content": "锦丞商城7天无理由退货怎么申请？"}]},
        stream_mode=["messages", "values"]):
    if stream_mode == "messages":
        if isinstance(response[0], AIMessageChunk):
            print(response[0].content, end="", flush=True)
    elif stream_mode == "values":
        if isinstance(response["messages"][-1], AIMessage):
            for msg in response["messages"]:
                if isinstance(msg, ToolMessage):
                    for doc in msg.artifact:
                        print("---" * 10)
                        print(doc.metadata.get("source", "未知"))
                        print(doc.page_content)
                        print("---" * 10)
