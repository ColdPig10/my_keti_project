# mcp_mirrorlake_resource_wrapper.py
# MCP 리소스를 LangGraph에서도 사용할 수 있도록 wrapping

#이 코드는 MirrorLake 원본 데이터를 “사람이 바로 읽기 좋은 자연어 요약”으로 변환해서,
# 네트워크 기반 LLM 파이프라인(예: LangGraph, 챗봇, 대시보드 등)에서 곧바로 쓸 수 있게
# “중간 API 서버” 역할을 한다!

# 복잡한 원시 데이터를
# → “한눈에 이해되는 설명문”으로 바꿔주는 서버

# 이 서버에 붙는 LangGraph/챗봇/LLM은
# → 별도의 파싱·정리 없이 바로 “자연어 요약 결과”를 받아 사용 가능

from mcp_mirrorlake_server_sse import all_digital_twins, all_sensors, all_digital_objects, get_sensor_data_resource, get_do_data_resource, all_simulations, all_subscriptions, get_sensor_data_by_time, get_do_data_by_time, get_simulation_data_resource, get_simulation_data_by_time
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Settings

mcp = FastMCP("MirrorLakeResourceWrapped") #MCP서버 인스턴스 생성

#내가 한거 시작
from self_rag import rag_query, check_answer_provenance

@mcp.tool(description='Self-Rag 검색/요약+근거 판별 답변 도구')
def self_rag_tool(query: str) -> str:
    answer, context = rag_query(query, return_context=True)
    provenance = check_answer_provenance(answer, context)
    print("[DEBUG] self_rag_tool called!", query)
    return f"[AI 답변]\n{answer}\n\n[출처 판별 결과]\n{provenance}"
#내가 한거 끝

#디지털 트윈 전체를 불러온 뒤, 각 항목을 사람이 읽기 쉬운 문장(자연어)로 요약
@mcp.tool(description="등록된 모든 디지털 트윈 정보를 요약해 반환합니다.")
def list_digital_twins() -> str:
    try:
        twins = all_digital_twins()
        if not isinstance(twins, list):
            return "[오류] 디지털 트윈 데이터를 불러올 수 없습니다."
        if not twins:
            return "등록된 디지털 트윈이 없습니다."

        result = "📦 등록된 디지털 트윈 목록:\n"
        for tw in twins:
            result += (
                f"\n ID: `{tw.get('digital_twin_id', '-')}`\n"
                f" 이름: **{tw.get('digital_twin_name', '-') }**\n"
                f" 위치: 위도 {tw.get('location', {}).get('lat', '-')}, 경도 {tw.get('location', {}).get('lng', '-')}\n"
                f" 설명: {tw.get('description', '-')[:100]}{'...' if len(tw.get('description', '')) > 100 else ''}\n"
                f" 센서: {tw.get('number_of_sensors', 0)}개, DO: {tw.get('number_of_digital_objects', 0)}개, 시뮬레이션: {tw.get('number_of_simulations', 0)}개\n"
                f" 태그: {', '.join(tw.get('tags', [])[:5])} {'...더 있음' if len(tw.get('tags', [])) > 5 else ''}\n"
                f" 생성자: {tw.get('creator_id', '-')}, 생성일: {tw.get('creation_time', '-')[:10]}\n"
                "─────────────────────────────"
            )
        return result

    except Exception as e:
        return f"[예외 발생] {str(e)}"

#센서 목록 요약
@mcp.tool(description="등록된 모든 센서 정보를 요약해 보기 좋게 반환합니다.")
def list_sensors() -> str:
    try:
        sensors = all_sensors()
        if not isinstance(sensors, list):
            return "[오류] 센서 데이터를 불러오지 못했습니다."
        if not sensors:
            return "등록된 센서가 없습니다."

        result = "🛰️ 등록된 센서 목록:\n" # 각 센서 정보를 문장으로 가공
        for s in sensors:
            result += (
                f"\n ID: `{s.get('sensor_id', '-')}` / 이름: **{s.get('sensor_name', '-') }**\n"
                f" 설명: {s.get('description', '-')[:100]}{'...' if len(s.get('description', '')) > 100 else ''}\n"
                f" 소속 DT: `{s.get('digital_twin_id', '-')}` / 생성자: `{s.get('creator_id', '-')}`\n"
                f" 전달 방식: `{s.get('internal_delivery_mode', '-')}` / 포맷: `{s.get('data_source_format', '-')}` / 타입: `{s.get('data_source_type', '-')}`\n"
                f" 태그: {', '.join(s.get('tags', [])[:5])} {'...더 있음' if len(s.get('tags', [])) > 5 else ''}\n"
                f" 생성일: {s.get('creation_time', '-')[:10]}\n"
                "─────────────────────────────"
            )
        return result

    except Exception as e:
        return f"[예외 발생] {str(e)}"

#디지털 객체 목록 요약
@mcp.tool(description="등록된 모든 디지털 객체(DO) 정보를 요약해 보기 좋게 반환합니다.")
def list_digital_objects() -> str:
    try:
        dos = all_digital_objects()
        if not isinstance(dos, list):
            return "[오류] 디지털 객체 데이터를 불러오지 못했습니다."
        if not dos:
            return "등록된 디지털 객체(DO)가 없습니다."

        result = "🧱 등록된 디지털 객체 목록:\n"
        for do in dos:
            result += (
                f"\n ID: `{do.get('digital_object_id', '-')}` / 이름: **{do.get('digital_object_name', '-') }**\n"
                f" 설명: {do.get('description', '-')[:80]}{'...' if len(do.get('description', '')) > 80 else ''}\n"
                f" 소속 DT: `{do.get('digital_twin_id', '-')}` / 생성자: `{do.get('creator_id', '-')}`\n"
                f" 접근 방식: `{do.get('access_protocol', '-')}` / 센서 수: `{do.get('member_sensor_count', 0)}`\n"
                f" 연결 센서: {', '.join(do.get('member_sensor_ids', [])[:3])} {'...더 있음' if len(do.get('member_sensor_ids', [])) > 3 else ''}\n"
                f" 태그: {', '.join(do.get('tags', [])[:5])} {'...더 있음' if len(do.get('tags', [])) > 5 else ''}\n"
                f" 생성일: {do.get('creation_time', '-')[:10]}\n"
                "─────────────────────────────"
            )
        return result

    except Exception as e:
        return f"[예외 발생] {str(e)}"

#특정 센서의 최신 데이터 요약
@mcp.tool(description="특정 디지털 트윈 내 센서의 최신 데이터를 조회합니다. 입력: dt_id, sensor_id, count (기본값 1)")
def get_sensor_data(dt_id: str, sensor_id: str, count: int = 1) -> str:
    try:
        data = get_sensor_data_resource(dt_id, sensor_id, count)
        if isinstance(data, dict) and "error" in data:
            return f"[{data['error']}] 센서 데이터 조회 실패"

        if not data:
            return f"센서 '{sensor_id}' (DT: {dt_id})에 대한 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"센서 '{sensor_id}' (DT: {dt_id})의 최신 데이터 {count}개:\n\n{summary}"

    except Exception as e:
        return f"[예외 발생] {str(e)}"

#특성 DO의 최신 데이터 요약
@mcp.tool(description="특정 디지털 트윈 내 디지털 객체(DO)의 최신 데이터를 조회합니다. 입력: dt_id, do_id, count (기본값 1)")
def get_do_data(dt_id: str, do_id: str, count: int = 1) -> str:
    try:
        data = get_do_data_resource(dt_id, do_id, count)
        if isinstance(data, dict) and "error" in data:
            return f"[{data['error']}] 디지털 객체 데이터 조회 실패"

        if not data:
            return f"디지털 객체 '{do_id}' (DT: {dt_id})에 대한 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"디지털 객체 '{do_id}' (DT: {dt_id})의 최신 데이터 {count}개:\n\n{summary}"

    except Exception as e:
        return f"[예외 발생] {str(e)}"

#특성 센서 기간별 데이터 요약
@mcp.tool(description="시간 기준으로 특정 센서 데이터를 조회하여 기간 내 데이터를 제공합니다. 입력: dt_id, sensor_id, from_time, to_time")
def get_sensor_data_time(dt_id: str, sensor_id: str, from_time: str, to_time: str) -> str:
    try:
        data = get_sensor_data_by_time(dt_id, sensor_id, from_time, to_time)
        if isinstance(data, dict) and "error" in data:
            return f"[{data['error']}] 센서 시간 조회 실패"
        if not data:
            return f"센서 '{sensor_id}' (DT: {dt_id})의 해당 기간 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"센서 '{sensor_id}' (DT: {dt_id})의 {from_time} ~ {to_time} 데이터:\n\n{summary}"
    except Exception as e:
        return f"[예외 발생] {str(e)}"

#특정 DO 기간별 데이터 요약
@mcp.tool(description="시간 기준으로 특정 디지털 객체 데이터를 조회합니다. 입력: dt_id, do_id, from_time, to_time")
def get_do_data_time(dt_id: str, do_id: str, from_time: str, to_time: str) -> str:
    try:
        data = get_do_data_by_time(dt_id, do_id, from_time, to_time)
        if isinstance(data, dict) and "error" in data:
            return f"[{data['error']}] DO 시간 조회 실패"
        if not data:
            return f"디지털 객체 '{do_id}' (DT: {dt_id})의 해당 기간 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"디지털 객체 '{do_id}' (DT: {dt_id})의 {from_time} ~ {to_time} 데이터:\n\n{summary}"
    except Exception as e:
        return f"[예외 발생] {str(e)}"



@mcp.tool(description="등록된 모든 시뮬레이션(simulation) 정보를 요약해 보기 좋게 반환합니다.")
def list_simulations() -> str:
    try:
        sims = all_simulations()
        if not isinstance(sims, list):
            return "[오류] 시뮬레이션 데이터를 불러오지 못했습니다."
        if not sims:
            return "등록된 시뮬레이션이 없습니다."

        result = "🧪 등록된 시뮬레이션 목록:\n"
        for s in sims:
            result += (
                f"\n ID: `{s.get('simulation_id', '-')}` / 이름: **{s.get('simulation_name', '-') }**\n"
                f" 설명: {s.get('description', '-')[:80]}{'...' if len(s.get('description', '')) > 80 else ''}\n"
                f" 소속 DT: `{s.get('dt_id', '-')}` / 생성자: `{s.get('creator_id', '-')}`\n"
                f" 접근 URL: `{s.get('simulation_access_url', '-')}` / 상태: `{s.get('simulation_state', '-')}`\n"
                f" 주제: {', '.join(s.get('simulation_subject', []))}\n"
                f" 생성일: {s.get('creation_time', '-')[:10]}\n"
                "─────────────────────────────"
            )
        return result

    except Exception as e:
        return f"[예외 발생] {str(e)}"

@mcp.tool(description="특정 디지털 트윈 내 시뮬레이션(simulation)의 최신 데이터를 조회합니다. 입력: dt_id, simulation_id, count (기본값 1)")
def get_simulation_data(dt_id: str, simulation_id: str, count: int = 1) -> str:
    """
    특정 디지털 트윈(dt_id) 내 지정된 시뮬레이션(simulation_id)의 최신 데이터를 조회합니다.
    
    count 인자를 통해 반환할 데이터 개수를 조절할 수 있으며, 실패 시 status code를 포함한 에러 dict를 반환합니다.
    """
    try:
        data = get_simulation_data_resource(dt_id, simulation_id, count)
        if isinstance(data, dict):
            if "error" in data:
                return f"[{data['error']}] 시뮬레이션 데이터 조회 실패 - {data.get('message', '')}"
            elif not data:
                return f"📭 시뮬레이션 '{simulation_id}' (DT: {dt_id})에 대한 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"시뮬레이션 '{simulation_id}' (DT: {dt_id})의 최신 데이터 {count}개:\n\n{summary}"

    except Exception as e:
        return f"[예외 발생] {str(e)}"


@mcp.tool(description="시간 기준으로 특정 시뮬레이션 데이터를 조회합니다. 입력: dt_id, simulation_id, from_time, to_time")
def get_simulation_data_time(dt_id: str, simulation_id: str, from_time: str, to_time: str) -> str:
    try:
        data = get_simulation_data_by_time(dt_id, simulation_id, from_time, to_time)
        if isinstance(data, dict) and "error" in data:
            return f"[{data['error']}] 시뮬레이션 시간 조회 실패"
        if not data:
            return f"시뮬레이션 '{simulation_id}' (DT: {dt_id})의 해당 기간 데이터가 없습니다."

        summary = "\n".join([f"{i+1}. {d}" for i, d in enumerate(data)])
        return f"시뮬레이션 '{simulation_id}' (DT: {dt_id})의 {from_time} ~ {to_time} 데이터:\n\n{summary}"
    except Exception as e:
        return f"[예외 발생] {str(e)}"



@mcp.tool(description="등록된 모든 구독(subscription) 정보를 요약해 보기 좋게 반환합니다.")
def list_subscriptions() -> str:
    try:
        subs = all_subscriptions()
        if not isinstance(subs, list):
            return "[오류] 구독 데이터를 불러오지 못했습니다."
        if not subs:
            return "등록된 구독 정보가 없습니다."

        result = "📡 등록된 구독 목록:\n"
        for s in subs:
            result += (
                f"\n ID: `{s.get('subscription_id', '-')}` / 이름: **{s.get('subscription_name', '-') }**\n"
                f" 설명: {s.get('description', '-')[:80]}{'...' if len(s.get('description', '')) > 80 else ''}\n"
                f" 소속 DT: `{s.get('dt_id', '-')}` / 생성자: `{s.get('creator_id', '-')}`\n"
                f" 프로토콜: `{s.get('subscription_protocol', '-')}`\n"
                f" 알림 URL: {', '.join(s.get('notification_url', []))[:100]}\n"
                f" 주제: {', '.join(s.get('subscription_subject', [])[:3])} {'...더 있음' if len(s.get('subscription_subject', [])) > 3 else ''}\n"
                f" 만료일: {s.get('expiration_time', '-')[:10]} / 실패 횟수: {s.get('fail_count', 0)}회\n"
                "─────────────────────────────"
            )
        return result

    except Exception as e:
        return f"[예외 발생] {str(e)}"



#서버 실행 (엔트리 포인트)
if __name__ == "__main__":
    mcp.settings = Settings(port=8010)
    mcp.run(transport="sse")
# MCP 서버 인스턴스가 포트 8010에서 SSE 프로토콜로 구동됨
# @mcp.tool함수를 외부에서 네트워크로 직접 호출할 수 있게 된다.

print("Working Dir:", os.getcwd())
print("Persist DB exists?:", os.path.exists('./pdf_test_chroma_db'))