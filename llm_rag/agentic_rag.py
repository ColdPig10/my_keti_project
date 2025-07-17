import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from typing import List, TypedDict
from langgraph.graph import StateGraph, START, END

# 1. .env 로드
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# 2. 벡터스토어/임베딩 준비
embedding_function = OpenAIEmbeddings(model='text-embedding-3-large')
vector_store = Chroma(
    embedding_function=embedding_function,
    collection_name="pdf_test_collection",
    persist_directory="./pdf_test_chroma_db"
)
retriever = vector_store.as_retriever(search_kwargs={"k": 3}) #최상위 k개 문서 검색

# 3. LangGraph State 정의
class AgentState(TypedDict):
    query: str
    context: List[Document]
    answer: str

# 4. 각 노드 함수 정의

# (1) Retrieve 노드
def retrieve(state: AgentState) -> AgentState:
    query = state['query']
    docs = retriever.invoke(query) #query로 벡터스토어에서 문서 검색 -> invoke(유사도검색)
    print(f"\n[retrieve] 검색된 문서 {len(docs)}개") #디버깅 - 검색 결과 출력
    for i, doc in enumerate(docs):
        print(f"[{i+1}] {doc.page_content[:80]} ...") #각 문서의 앞부분 80글자 미리보기
    return {'query': query, 'context': docs, 'answer': ""} 

# (2) Generate(답변생성) 노드
llm = ChatOpenAI(model="gpt-4o-mini", max_completion_tokens=400)

def generate(state: AgentState) -> AgentState:
    context = state['context']
    query = state['query']
    context_str = "\n\n".join([doc.page_content for doc in context])
    prompt = f"""너는 아래 문서 발췌 내용을 바탕으로 질문에 답해야 하는 어시스턴트야.

문서 발췌:
{context_str}

질문: {query}
답변:"""
    response = llm.invoke(prompt)
    print(f"\n[generate] 답변: {response.content[:80]} ...")
    return {'query': query, 'context': context, 'answer': response.content}

# (3) AnswerCheck(종료 조건) 노드
def answer_check(state: AgentState) -> str:
    # 예시: 답변 길이가 10자 이상이면 END
    if len(state["answer"]) > 10:
        return "sufficient"
    else:
        return "insufficient"

# (4) Fallback(추가 검색/생성) 노드
def fallback(state: AgentState) -> AgentState:
    # 간단 예시: 다시 검색해보기 (여기서는 사실상 retrieve와 동일)
    print("\n[fallback] 추가 검색/재시도 ...")
    return retrieve(state)

# 5. LangGraph Graph 빌더
graph_builder = StateGraph(AgentState)
graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("generate", generate)
graph_builder.add_node("fallback", fallback)

# 6. Graph 엣지(흐름) 연결
graph_builder.add_edge(START, "retrieve")
graph_builder.add_edge("retrieve", "generate")
graph_builder.add_conditional_edges(
    "generate", answer_check,
    {
        "sufficient": END,
        "insufficient": "fallback"
    }
)
graph_builder.add_edge("fallback", "retrieve")

graph = graph_builder.compile()

# 7. 실제 질문 넣고 실행
if __name__ == "__main__":
    query = "PDF에서 주요 논점은 무엇인가요?"   # 원하는 질문으로 교체
    initial_state = {'query': query, 'context': [], 'answer': ''}
    result = graph.invoke(initial_state)
    print("\n[최종 답변]")
    print(result['answer'])