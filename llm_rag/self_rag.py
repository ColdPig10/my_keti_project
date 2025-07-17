import os
from dotenv import load_dotenv

# 1. 환경변수(.env)에서 OpenAI API 키 불러오기
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# 2. 벡터스토어(Chroma) + 임베딩 함수 세팅
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

embedding_function = OpenAIEmbeddings(model='text-embedding-3-large')
vector_store = Chroma(
    embedding_function=embedding_function,
    collection_name='pdf_test_collection',
    persist_directory='./pdf_test_chroma_db'
)
retriever = vector_store.as_retriever(search_kwargs={'k': 3})

# 3. 상태 정의 (LangGraph에서 관리하는 state 구조)
from typing import List, TypedDict
from langchain_core.documents import Document

class AgentState(TypedDict): # -> query, 검색 결과, answer을 하나의 dict에 담아 state로 계속 전달
    query: str
    context: List[Document]
    answer: str

# 4. LangGraph 그래프 빌더 준비
from langgraph.graph import StateGraph

graph_builder = StateGraph(AgentState)

# 5. [노드] 문서 검색 노드 (retrieve)
def retrieve(state: AgentState) -> AgentState:
    query = state['query']  # - 현재 질문 꺼내기
    docs = retriever.invoke(query)  # - 유사chunk 3개 검색
    
    # 디버깅 - 결과 확인
    print("\n[retrieve] Query:", query)
    print("[retrieve] Retrieved docs count:", len(docs))
    for i, doc in enumerate(docs):
        print(f"Doc {i}: {getattr(doc, 'page_content', str(doc))[:100]}...")
    
    # state에 검색 결과 저장해서 반환
    return {'query': query, 'context': docs, 'answer': ''}

graph_builder.add_node('retrieve', retrieve) # -> query embedding -> vector db -> chunk invoke -> 상위 3개

# 6. [노드] 답변 생성 노드 (generate)
from langchain_openai import ChatOpenAI
from langchain import hub

llm = ChatOpenAI(model='gpt-4o-mini', max_completion_tokens=100)
generate_prompt = hub.pull("rlm/rag-prompt") # -> rag 프롬포트 가져오기

def generate(state: AgentState) -> AgentState: # input : 현재 상태 state -> {"query": 질문, "context": 검색된 문서들, "answer": ""}
    context = state['context']  
    query = state['query']
    rag_chain = generate_prompt | llm # -파이프라인: 질문/문서 context -> prompt변환 -> LLM전달
    response = rag_chain.invoke({'question': query, 'context': context}) # - 질문/문서 context를 prompt에 채워서 LLM에 보낸다.
    return {'query': query, 'context': context, 'answer': response.content} # state dic형태로 결과 return, answer키에 LLM이 생성한 답변을 담아 다음 노드로 전달

graph_builder.add_node('generate', generate) # LangGraph에 generate라는 이름으로 답변 생성 노드를 등록
                                             # 파이프라인 흐름 안에서 이 노드 실행되면, [벡터 검색 결과 + 질문 -> LLM -> 답변] 자동 처리

# 7. [노드] 문서 관련성 평가 (check_doc_relevance)
# doc_relevance_prompt = hub.pull("langchain-ai/rag-document-relevance")

# def check_doc_relevance(state: AgentState) -> str:
#     query = state['query']
#     context = state['context']
#     doc_relevance_chain = doc_relevance_prompt | llm
#     response = doc_relevance_chain.invoke({'question': query, 'documents': context})
#     if response['Score'] == 1:
#         return 'relevant'
#     return 'irrelevant'

#프롬프트 커스텀 -> 질문-문서 관련성 1~10 세분화 평가 
from langchain_core.prompts import PromptTemplate 

doc_relevance_prompt = PromptTemplate.from_template("""
You are a teacher grading a quiz.

You will be given a QUESTION and a set of FACTS provided by the student.

Here is the grade criteria to follow:
(1) Your goal is to identify how relevant the FACTS are to the QUESTION on a scale of 1 to 10.
(2) If the facts contain keywords, direct answers, or semantic meaning strongly related to the question, give a high score (close to 10).
(3) If there is only a weak or tangential relation, give a mid score (e.g., 4~6).
(4) If the facts are only minimally or indirectly related, give a low score (1~3).
(5) If the facts are completely unrelated, give a score of 1.

Score:
- A score of 10 means the facts are highly relevant and specific to the question.
- A score of 1 means the facts are completely unrelated to the question.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct.
Avoid simply stating the correct answer at the outset.

Output format:
{{
  "Score": [1-10],
  "Explanation": "your reasoning step-by-step"
}}

QUESTION: {question}
FACTS: {documents}
""")

# 유사도 10~7 : relevant, 유사도 6~1 : irrelevant
import re

doc_relevance_chain = doc_relevance_prompt | llm

def check_doc_relevance(state: AgentState) -> str:
    query = state['query']
    context = state['context']
    response = doc_relevance_chain.invoke({'question': query, 'documents': context})
    # Score가 dict로 오거나 string으로 올 수 있음
    if isinstance(response, dict):
        score = int(response['Score'])
    else:
        match = re.search(r'"Score":\s*(\d+)', str(response))
        score = int(match.group(1)) if match else 1
    print(f"[relevance] Score: {score}/10")
    if score >= 7:
        return 'relevant'
    else:
        return 'irrelevant'

# 8. [노드] 환각(hallucination) 평가 (check_hallucination)
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

hallucination_prompt = PromptTemplate.from_template("""
You are a teacher tasked with evaluating whether a student's answer is based on documents or not,
Given documents, which are excerpts from income tax law, and a student's answer;
If the student's answer is based on documents, respond with "not hallucinated",
If the student's answer is not based on documents, respond with "hallucinated".
documents: {documents}
student_answer: {student_answer}
""")

hallucination_llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

def check_hallucination(state: AgentState) -> str:
    answer = state['answer']
    context = [doc.page_content for doc in state['context']]
    hallucination_chain = hallucination_prompt | hallucination_llm | StrOutputParser() # 파이프라인 : prompt -> LLM -> Parser
    response = hallucination_chain.invoke({'student_answer': answer, 'documents': context})
    return response

# 9. [노드] 답변 유용성 평가 (check_helpfulness)
helpfulness_prompt = hub.pull("langchain-ai/rag-answer-helpfulness")

def check_helpfulness_grader(state: AgentState) -> str:
    query = state['query']
    answer = state['answer']
    helpfulness_chain = helpfulness_prompt | llm # 평가prompt + LLM을 체인으로 연결 -> LLM에 Prompt와 함께 평가 요청
    response = helpfulness_chain.invoke({'question': query, 'student_answer': answer})
    if response['Score'] == 1:
        return 'helpful'
    return 'unhelpful'

def check_helpfulness(state: AgentState) -> AgentState:
    # 상태 변형 없음, 단순 패스용
    return state

graph_builder.add_node('check_helpfulness', check_helpfulness) # LangGraph에 check_helpfulness 라는 이름으로 답변의 질 채점 노드를 등록
                                                               # 파이프라인 흐름 안에서 이 노드 실행되면, [질문, 답변 -> LLM -> 채점 결과] 자동 처리

# 10. [노드] 질문 재작성 (rewrite)
dictionary = ['사람과 관련된 표현 -> 거주자'] #질문 변환에 사용할 사전 정의

# LLM에게 던질 prompt (dic참고)
rewrite_prompt = PromptTemplate.from_template(f"""
사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요 
사전: {dictionary}
질문: {{query}}
""")

def rewrite(state: AgentState) -> AgentState:
    query = state['query']  # state에서 질문 추출
    rewrite_chain = rewrite_prompt | llm | StrOutputParser() # 질문 변경 prompt -> LLM -> LLM응답 문자열 변환 Parser
    response = rewrite_chain.invoke({'query': query}) # LLM이 질문을 사전에 맞게 변환함
    # 답변 초기화
    return {'query': response, 'context': [], 'answer': ''} # 질문에 LLM이 변환한 응답으로 변경, context&answer는 빈칸으로 초기화
                                                            # 이전 검색 결과나 답변이 새로운 질문과 안맞아서 엉뚱한 결과 나올 수 있기 때문

graph_builder.add_node('rewrite', rewrite) # LangGraph에 rewrite 라는 이름으로 유용한 질문 생성기를 등록
                                           # 파이프라인 흐름 안에서 이 노드 실행되면, [질문 -> LLM(dict 참고)-> 새 질문 state들어감 & 초기화 -> retrieve노드로 다시 이동] 자동 처리

# 11. [그래프] 흐름/조건 연결 (edge, conditional edge)
from langgraph.graph import START, END

graph_builder.add_edge(START, 'retrieve')
graph_builder.add_conditional_edges(
    'retrieve',
    check_doc_relevance, 
    {
        'relevant': 'generate',
        'irrelevant': END
    }
)
graph_builder.add_conditional_edges(
    'generate',
    check_hallucination,
    {
        'not hallucinated': 'check_helpfulness',
        'hallucinated': 'generate'
    }
)
graph_builder.add_conditional_edges(
    'check_helpfulness',
    check_helpfulness_grader,
    {
        'helpful': END,
        'unhelpful': 'rewrite'
    }
)
graph_builder.add_edge('rewrite', 'retrieve')

# 12. [그래프] 컴파일
graph = graph_builder.compile()

# 13. [질문 입력 후 실행]  
if __name__ == '__main__':
    # 쿼리 예시
    initial_state = {'query': '기계식 주차장은 어떤 조건일때 철거할 수 있어?', 'context': [], 'answer': ''}
    # 실제 실행
    result = graph.invoke(initial_state)
    print("\n=== 최종 답변 및 상태 ===")
    print(result)
