# main.py

import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# 1. 환경 변수 로드
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# 2. 임베딩 모델 및 벡터스토어 불러오기
embedding_function = OpenAIEmbeddings(model='text-embedding-3-large')  # build_chroma_db.py와 동일
vector_store = Chroma(
    embedding_function=embedding_function,
    collection_name="pdf_test_collection",
    persist_directory="./pdf_test_chroma_db"
)
retriever = vector_store.as_retriever(search_kwargs={"k": 3})  # top3 검색

# 3. LLM 준비 (gpt-4o-mini, gpt-3.5-turbo 등 본인 계정에 맞게)
llm = ChatOpenAI(model="gpt-4o-mini", max_completion_tokens=300)

# 4. 사용자 질문 입력
query = "PDF의 주요 내용은 무엇인가요?"  # 예시 질문, 원하는 질문으로 교체 가능

# 5. 문서 검색
docs = retriever.invoke(query)
print(f"[검색 결과] {len(docs)}개 chunk 반환됨")
for i, doc in enumerate(docs):
    print(f"[{i+1}] {doc.page_content[:100]} ...")

# 6. RAG 프롬프트 구성
context = "\n\n".join([doc.page_content for doc in docs])
prompt = f"""
너는 PDF 문서에 근거해 답변하는 비서야.
아래 '문서 발췌' 내용을 잘 읽고, 사용자 질문에 최대한 정확하게 근거를 들어서 답해줘.

문서 발췌:
{context}

질문: {query}
답변:"""

# 7. LLM에 프롬프트 입력하여 답변 생성
response = llm.invoke(prompt)
print("\n[최종 답변]\n", response.content)