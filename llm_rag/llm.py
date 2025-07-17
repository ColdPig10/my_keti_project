import os
from dotenv import load_dotenv
load_dotenv()  # .env에서 OPENAI_API_KEY 읽어 환경 변수에 세팅

#langchain_communicty
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQAWithSourcesChain

#Streamlit 연동
import sqlite3
import sys
import streamlit as st

#챗봇 설정
st.set_page_config(
    page_title="질의응답챗봇",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# OPENAI API 키 불러오기
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# PDF 문서 로드
loader = PyPDFLoader('parkinglot_law.pdf')  # 파일 확장자 확인
documents = loader.load()

# 문서 분할
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# 임베딩 및 벡터스토어 생성
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vector_store = Chroma.from_documents(texts, embeddings)

# 검색기 생성
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

#프롬프트 개선
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

system_template="""
Use the following pieces of context to answer the user's question.
If you don't know the answer, just say "I don't know", don't try to make up an answer.
----------------
{context}

You MUST answer in Korean and in Markdown format. Also include source information as "SOURCES".
"""

messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}")
]

prompt = ChatPromptTemplate.from_messages(messages)

#ChatGPT 모델 사용하여 학습
chain_type_kwargs = {
    "prompt": prompt,
    "document_variable_name": "context"  # 이 줄 추가!
}

llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)  # Modify model_name if you have access to GPT-4

chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever = retriever,
    return_source_documents=True,
    chain_type_kwargs=chain_type_kwargs
)

#streamlit 전용 챗봇 코드
st.subheader('질문을 적어 주세요')

#응답 생성 코드
def generate_response(input_text):
    result = chain({"question": input_text})
    return result["answer"]

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "질문을 적어 주세요 무엇을 도와 드릴까요?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    msg =  generate_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)