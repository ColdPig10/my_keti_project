# gradio_langgraph_mcp_sse_client.py
import os
from dotenv import load_dotenv
import gradio as gr
import asyncio
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

class AgentState(MessagesState):
    pass

async def main():
    # 1. MCP 클라이언트 연결
    client = MultiServerMCPClient({
        "mirrorlake": {"url": "", "transport": "sse"},
        "mirrorlake-resource-wrapper": {"url": "", "transport": "sse"},
    })

    # 2. 도구 로딩 및 LLM 설정
    tools = await client.get_tools()
    for tool in tools:
        print(tool, type(tool), "\n")

    llm = ChatOpenAI(temperature=1.0, model='gpt-4o-mini')
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    # 3. 에이전트 정의
    async def agent(state: AgentState) -> AgentState:
        messages = state["messages"]
        response = await llm_with_tools.ainvoke(messages) # 사용자의 대화를 받아 LLM에 전송
        return {"messages": [response]} # LLM이 대답을 생성 후 반환

    # 4. LangGraph 구성
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent) #사용자의 메세지 처리(질문 분석, 답변 생성)
    builder.add_node("tools", tool_node) # 필요한 도구(서버) 호출

    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    builder.add_edge("agent", END)
    graph = builder.compile()

    #대화 시작 -> agent노드 -> (필요한 도구 있을 시)tools노드 이동 -> 작업 끝나면 다시 agent노드 -> 처리할 내용 없으면 END
    
    # 5. Gradio UI 정의
    async def query_agent(user_input, chat_history, system_prompt):
        messages = [SystemMessage(content=system_prompt)]
        for i in range(0, len(chat_history), 2):
            messages.append(HumanMessage(content=chat_history[i]["content"]))
            if i + 1 < len(chat_history):
                messages.append(AIMessage(content=chat_history[i + 1]["content"]))
        messages.append(HumanMessage(content=user_input))
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 사용자 질문: {user_input}")
        try:
            result = await graph.ainvoke({"messages": messages}, config=RunnableConfig(configurable={"recursion_limit": 50}))
            reply = result["messages"][-1].content
        except Exception as e:
            reply = f"[에러] {str(e)}"
            print(f"[{timestamp}] 에러 응답: {reply}")
        else:
            print(f"[{timestamp}] 챗봇 응답: {reply}")

        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": reply})
        return chat_history, ""

    #Gradio UI 실제 레이아웃
    with gr.Blocks() as demo:
        gr.Markdown("# 🌐 MirrorLake SSE Chatbot")
        with gr.Row():
            system_prompt = gr.Textbox(
                label="System Prompt",
                lines=20,
                value=(
                    "당신은 MirrorLake 플랫폼의 전문 어시스턴트입니다.\n"
                    "MirrorLake는 디지털 트윈(DT), 디지털 객체(DO), 센서(Sensor)를 연합 구성하고 데이터를 실시간으로 처리하는 플랫폼입니다.\n"
                    "MirrorLake 플랫폼에서는 디지털 트윈(Digital Twin) 하위에 센서를 등록하며,\n"
                    "등록된 센서 중 하나 이상을 조합하여 디지털 객체(Digital Object)를 생성할 수 있습니다.\n"
                    "이때 디지털 객체는 연결된 센서들의 데이터를 조합하여 새로운 데이터를 생성합니다.\n\n"
                    "[사용 가능한 도구]\n"
                    "- list_digital_twins(): 등록된 모든 DT 목록을 조회합니다.\n"
                    "- list_all_digital_objects(): 등록된 모든 DO 목록을 조회합니다.\n"
                    "- list_all_sensors(): 등록된 모든 센서 목록을 조회합니다.\n"
                    "- get_sensor_data(dt_id, sensor_id): 특정 센서의 최신 데이터를 조회합니다.\n"
                    "- get_do_data(dt_id, do_id): 특정 디지털 객체(DO)의 최신 데이터를 조회합니다.\n"
                    "- list_all_simulations(): 등록된 모든 시뮬레이션(simulation) 목록을 조회합니다.\n"
                    "- list_all_subscriptions(): 등록된 모든 구독(subscription)  목록을 조회합니다.\n"
                    "- get_simulation_data(dt_id, sim_id): 특정 시뮬레이션(simulation) 최신 결과 데이터를 조회합니다\n"
                    "[도구 사용 우선순위 및 답변 출처 지침]\n"
                    "- 질문이 주차장, 주차장법 등과 관련되어 있다면, 반드시 self_rag_tool을 먼저 사용하세요.\n"
                    "- self_rag_tool 답변이 충분하지 않거나, PDF에서 관련 내용을 찾지 못하면 그때만 GPT의 자체 지식으로 보완하세요.\n"
                    "- 답변마다 출처(예: PDF 기반, GPT 기반, 둘 다 등)를 반드시 표시하세요.\n"
                    "- 예시: '아래 답변은 PDF 기반으로 작성되었습니다.'\n"
                    "        '아래 답변은 PDF의 일부 내용과 GPT의 일반 지식을 함께 참고했습니다.'\n"
                    "        'PDF에 정보가 없어 GPT 자체 지식으로 답변합니다.'\n"
                    "\n"
                    " 다음과 같은 질문에 적절히 도구를 사용하세요:\n"                    
                    "- '모든 DT 정보를 알려줘'\n"                
                    "- '모든 DO 정보를 알려줘'\n"                
                    "- '모든 센서 정보를 알려줘'\n"
                    "- '센서 S001의 최근 데이터를 알려줘'\n"
                    "- 'KR-02 트윈의 DO do-line-01 상태 알려줘'\n"
                    "- 'KR-02의 S_Temp_02 센서값 보여줘'"
                    "- 한시간 전부터 지금까지의 S_cotlab_TpHm_010 센서데이터를 조회해줘"
                    "- SIM-water-predict의 2025-02-18 8시 부터 30분 동안의 데이터를 조회해줘"
                ),
            )
        chatbot = gr.Chatbot(height=500, type="messages")
        user_input = gr.Textbox(show_label=False, placeholder="MirrorLake 관련 질문을 입력하세요...")
        send_btn = gr.Button("전송")
        state = gr.State([])

        send_btn.click(query_agent, inputs=[user_input, state, system_prompt], outputs=[chatbot, user_input])
        user_input.submit(query_agent, inputs=[user_input, state, system_prompt], outputs=[chatbot, user_input])

    #Gradio 서버 실행
    demo.launch(server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    asyncio.run(main())

#논리 흐름
# MCP 서버(원본, 요약)에서 Tool 정보를 가져와 준비

# LLM + Tool 조합으로 대화 Agent와 Tool 노드 연결

# LangGraph로 전체 대화흐름/Tool 호출/재귀 처리 등 워크플로우 완성

# Gradio로 웹챗봇 UI 생성, 사용자가 질문/대화 가능

# LLM이 자연어 질문을 이해해서, 필요한 Tool(MCP 서버 API)을 자동 호출, 결과를 읽기 쉽게 대답

# 모든 처리가 비동기로 빠르게 수행

print("Working Dir:", os.getcwd())
print("Persist DB exists?:", os.path.exists('./pdf_test_chroma_db'))