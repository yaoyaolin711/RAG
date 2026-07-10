import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from settings import TOP_K, LLM_MODEL_NAME, LLM_MODEL_BASE_URL, get_aliyun_api_key
from vectorstore import get_vector_store, check_milvus_connection

check_milvus_connection()
vector_store = get_vector_store()


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    docs = vector_store.similarity_search(query, k=TOP_K)
    serialized = "\n".join(f"{d.metadata.get('source')}: {d.page_content[:100]}" for d in docs)
    return serialized, docs


model = init_chat_model(
    model=LLM_MODEL_NAME, model_provider="openai", api_key=get_aliyun_api_key(), base_url=LLM_MODEL_BASE_URL
)
agent = create_agent(model, tools=[retrieve_context], system_prompt="你是锦小丞，简洁回答。")

question = "满多少免运费？"
print(f"问题: {question}")
resp = agent.invoke({"messages": [{"role": "user", "content": question}]})
print(f"回答: {resp['messages'][-1].content}")
