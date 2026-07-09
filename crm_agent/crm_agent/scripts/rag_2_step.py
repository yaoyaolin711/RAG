import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage

from settings import TOP_K, LLM_MODEL_NAME, LLM_MODEL_BASE_URL, get_aliyun_api_key
from vectorstore import get_vector_store, check_chroma_connection

check_chroma_connection()
vector_store = get_vector_store()


@dynamic_prompt
def dynamic_prompt_fn(request: ModelRequest) -> str:
    query = request.messages[-1].content
    retrieved_docs = vector_store.similarity_search(query, k=TOP_K)

    prompt = """你是锦丞商城的智能客服助手，名字叫锦小丞。请根据以下从知识库检索到的内容回答用户问题。
            回答时语气亲切、简洁专业。如果信息不足以回答，请说"抱歉，我暂时无法根据现有信息回答该问题。"
            检索到的内容：
            """
    for doc in retrieved_docs:
        prompt += f"{doc.metadata.get('source', '未知')}：{doc.page_content}\n"

    return prompt


model = init_chat_model(
    model=LLM_MODEL_NAME,
    model_provider="openai",
    base_url=LLM_MODEL_BASE_URL,
    api_key=get_aliyun_api_key(),
)
agent = create_agent(model, middleware=[dynamic_prompt_fn])

response = agent.invoke({"messages": [
    {"role": "user", "content": "金卡会员有什么权益？"}
]})

for msg in response["messages"]:
    if isinstance(msg, AIMessage) and msg.content.strip() != "":
        print(msg.content)
