# build_chroma_db.py

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain.text_splitter import CharacterTextSplitter
from pypdf import PdfReader  # pypdf==3.x 버전이면 PyPDF2 대신 pypdf 사용

# 1. .env에서 API 키 불러오기
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# 2. PDF 파일 경로 설정
pdf_path = "C:/Users/user/Documents/sejong_keti/llm_rag/parkinglot_law.pdf"   # documents 폴더에 pdf 파일

# 3. PDF 파일 읽기
reader = PdfReader(pdf_path)
raw_text = ""
for page in reader.pages:
    raw_text += page.extract_text() + "\n"

# 4. 텍스트 분할 (chunk 단위, 예: 500자, 겹침 50자)
text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=500,
    chunk_overlap=50
)
texts = text_splitter.split_text(raw_text)
print(f"총 {len(texts)}개 chunk 생성됨.")

# 5. Langchain 문서 객체 변환
documents = [Document(page_content=chunk, metadata={"source": pdf_path}) for chunk in texts]

# 6. 임베딩 모델 준비 (본인 계정에서 사용 가능한 것!)
embedding_function = OpenAIEmbeddings(model='text-embedding-3-large')  # 또는 3-large

# 7. Chroma 벡터스토어에 임베딩 & 저장
vector_store = Chroma.from_documents(
    documents=documents,
    embedding=embedding_function,
    collection_name="pdf_test_collection",       # main.py와 반드시 일치!
    persist_directory="./pdf_test_chroma_db"
)

print("Chroma DB 생성 완료!")