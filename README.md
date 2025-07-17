# 세종 KETI 실습/프로젝트 정리

이 저장소는 아두이노 센서, RTSP 기반 객체 검출, FastAPI 서버, MirrorLake MCP, LLM RAG 등
세종대학교 AI융합전자공학과 실습/프로젝트 코드와 핵심 자료를 정리한 공간입니다.

---

## 📂 폴더 구조 및 설명

### 1. `tphm_arduino/`
- **아두이노 기반 환경 센서(TPHM) 및 데이터 전송 실습 폴더**
- 주요 파일:
  - `rtsp_myserver_send.ino`, `sejong_mirrorlake.ino`, `sejong_mirrorlake_SQL.ino`
  - `create_db.py`, `sql.py` : (DB연동/센서 데이터 저장 관련)
- 예제/실습 코드와 MirrorLake 연동 코드 포함

---

### 2. `rtsp_dectection/`
- **RTSP 센서 기반 객체 검출 및 영상 처리 실습 폴더**
- 주요 파일:
  - `rtsp_detection.py` : RTSP 스트림에서 객체(차량 등) 탐지
  - `rtsp_car_embedding.py`, `protoEmbeddingTest.py` : 임베딩, 후처리 실험
  - `capture.py`, `sample1.py` : 실험/테스트 코드

---

### 3. `server/`
- **FastAPI 등 서버 구동, 데이터 처리 실습 폴더**
- 주요 파일:
  - `server.py` : 센서 데이터 수신 및 API 처리 메인 코드

---

### 4. `mcp_server/`
- **MirrorLake MCP 서버, 리소스 래핑, 챗봇 연동 실습 폴더**
- 주요 파일:
  - `mcp_mirrorlake_resource_wrapper.py`, `mcp_mirrorlake_server_sse.py` : MirrorLake MCP 연동/서버 코드
  - `gradio_langgraph_mcp_sse_client.py` : Gradio 기반 LangGraph-챗봇 클라이언트
  - `self_rag.py`, `parkinglot_law.pdf` : RAG 도구/데이터 예시

---

### 5. `llm_rag/`
- **LLM 기반 RAG, LangGraph, 문서 검색/질의응답 실습 폴더**
- 주요 파일:
  - `llm_langgraph.py`, `llm.py`, `self_rag.py`, `build_chroma_db.py`, `agentic_rag.py`, `langchain_pdf.py`
  - `parkinglot_law.pdf` : 문서 질의응답용 데이터 파일

---