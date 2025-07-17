from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage

from langgraph.graph import StateGraph, START, END

# 1. LLM 인스턴스 챗봇 모델 준비
llm = ChatOpenAI(model="gpt-4o-mini") 

# 2. State 정의 (상태 관리 구조체) -> LangGraph에서 데이터가 흐르는 방식은 '상태'라는 딕셔너리로 주고받는 구조이다.
class AgentState(TypedDict): 
    messages: list[Annotated[AnyMessage, add_messages]] #Annotated로 메세지 타입 관리

# 3. 그래프 빌더 준비
graph_builder = StateGraph(AgentState) #노드와 엣지로 구성된 그래프형 워크플로우 생성

# 4. 노드(작업 단위 함수) 정의
def generate(state: AgentState) -> AgentState:
    """
    'generate' 노드는 사용자의 질문(messages)을 받아서
    챗봇 LLM(OpenAI)로부터 답변을 받고,
    그 답변 메시지만을 담은 새로운 상태로 반환하는 함수입니다.
    (LangGraph에서 모든 논리는 이런 식의 함수 단위 노드로 나눕니다)
    """
    messages = state["messages"]      #입력 -> 현재 상태에서 messages(질문 리스트)만 추출
    ai_message = llm.invoke(messages) #처리 -> LLM에게 메시지 리스트를 통째로 전달해 답변 생성
    return {"messages": [ai_message]} #출력 -> 답변 메시지만 포함한 새 상태로 반환

# 5. 노드 등록
graph_builder.add_node("generate", generate) #generate함수를 노드로 등록해서 그래프에 추가

# 6. 엣지(연결) 정의
graph_builder.add_edge(START, "generate") # START → generate: 그래프가 시작되면 generate 노드로 간다
graph_builder.add_edge("generate", END) # generate → END: generate가 끝나면 그래프도 종료

# 7. 그래프 완성 - 실행 가능한 상태로 변환
graph = graph_builder.compile() # 지금까지 노드와 엣지로 설계한 '빌더'를 실제 실행가능한 그래프 객체로 변환

# 8. 실제 질의 처리
query = "잠만보가 뭐야?" # 사용자가 입력한 질문 텍스트
initial_state = {"messages": [HumanMessage(query)]} # HumanMessage(query): LangChain이 요구하는 포맷으로 메시지 객체 생성
result = graph.invoke(initial_state) # initial_state: 이 메시지 객체를 messages 리스트에 담아 AgentState 딕셔너리 구성
# graph.invoke(initial_state): 그래프의 시작점에 initial_state를 넣어서 실행

# 9. 결과 출력
print("💬 LangGraph 결과:")
for msg in result["messages"]:
    print(msg.content)