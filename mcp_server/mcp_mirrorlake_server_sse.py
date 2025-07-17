# mcp_mirrorlake_server_sse.py

# MirrorLake REST API의 다양한 자원을 “통합적으로 쉽게” 접근 가능하게 MCP 서버 리소스로 등록하고,
# 실시간으로 데이터를 받아볼 수 있게 해주는 중계 서버(Adaptor/Gateway) 역할.

# 여러 REST API를 한 곳에서 “리소스명”으로 관리

# 실제 사용자는 복잡한 REST 호출/파라미터 관리 없이
# → MCP 리소스 명만으로 데이터를 조회 가능

import requests
from mcp.server.fastmcp import FastMCP
import sys
from datetime import datetime

mcp = FastMCP("MirrorLakeResourceInfo") #FastMCP 서버 인스턴스 생성 -> 중계서버
BASE_URL = ""

#MIRRORLAKE에서 DATA가져오는 함수

#Digital Twin 정보 전체 조회
@mcp.resource("mirrorlake://digital_twins")
def all_digital_twins() -> list[dict]:
    """등록된 모든 디지털 트윈(Digital Twin) 정보를 조회합니다."""
    res = requests.get(f"{BASE_URL}/digital-twins")
    return res.json() if res.ok else {"error": res.status_code}

#모든 센서 정보 조회
@mcp.resource("mirrorlake://sensors")
def all_sensors() -> list[dict]:
    """
    all_sensors에서는 all_digital_twins에서 얻은 digital_twin리소스를 이용하여 등록된 모든 sensor 리소스를 조회하여 리스트로 반환한다.
    """
    twins = all_digital_twins()
    if not isinstance(twins, list):
        return {"error": "Invalid twins data"}
    sensors = []
    for dt in twins:
        dt_id = dt.get("digital_twin_id")
        try:
            res = requests.get(f"{BASE_URL}/digital-twins/{dt_id}/sensors")
            if res.ok:
                s_list = res.json()
                for s in s_list:
                    s["dt_id"] = dt_id
                    sensors.append(s)
        except:
            continue
    return sensors

#모든 digital object 조회
@mcp.resource("mirrorlake://digital_objects")
def all_digital_objects() -> list[dict]:
    """
    all_digital_objects에서는 all_digital_twins에서 얻은 digital_twin리소스를 이용하여 등록된 모든 digital_object 리소스를 조회하여 리스트로 반환한다.
    """
    twins = all_digital_twins()
    if not isinstance(twins, list):
        return {"error": "Invalid twins data"}
    dos = []
    for dt in twins:
        dt_id = dt.get("digital_twin_id")
        try:
            res = requests.get(f"{BASE_URL}/digital-twins/{dt_id}/digital-objects")
            if res.ok:
                d_list = res.json()
                for d in d_list:
                    d["dt_id"] = dt_id
                    dos.append(d)
        except:
            continue
    return dos

#특정 센서 데이터 n건 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/sensors/{sensor_id}/data/{count}")
def get_sensor_data_resource(dt_id: str, sensor_id: str, count: int = 1) -> list[dict] | dict:
    """
    특정 디지털 트윈(dt_id) 내 지정된 센서(sensor_id)의 최신 데이터를 조회합니다.
    
    count 인자를 통해 반환할 데이터 개수를 조절할 수 있으며, 실패 시 status code를 포함한 에러 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/sensors/{sensor_id}/data?count={count}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#특정 digital object 데이터 n건 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/digital-objects/{do_id}/data/{count}")
def get_do_data_resource(dt_id: str, do_id: str, count: int = 1) -> list[dict] | dict:
    """
    특정 디지털 트윈(dt_id) 내 지정된 디지털 객체(do_id)의 최신 데이터를 조회합니다.
    
    count 인자를 통해 반환할 데이터 개수를 조절할 수 있으며, 실패 시 status code를 포함한 에러 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/digital-objects/{do_id}/data?count={count}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#특정 센서의 시간 구간 데이터 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/sensors/{sensor_id}/data/{from_time}/{to_time}")
def get_sensor_data_by_time(dt_id: str, sensor_id: str, from_time: str, to_time: str| None = None) -> list[dict] | dict:
    """
    지정된 디지털 트윈(dt_id)의 센서(sensor_id)로부터 시간 범위(`from_time` ~ `to_time`)를 통해 기간 내 수집된 데이터를 조회합니다.
    - from_time, to_time은 ISO8601 형식의 문자열이어야 합니다. (예: 2025-05-25T00:00:00)
    - count를 지정하지 않으면 기본 최대 100개의 데이터를 반환합니다.
    - 실패 시 에러 status code를 포함한 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/sensors/{sensor_id}/data?from={from_time}&to={to_time}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#특정 digital object의 시간 구간 데이터 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/digital-objects/{do_id}/data/{from_time}/{to_time}")
def get_do_data_by_time(dt_id: str, do_id: str, from_time: str, to_time: str| None = None) -> list[dict] | dict:
    """
    지정된 디지털 트윈(dt_id)의 디지털 객체(do_id)로부터 시간 범위(`from_time` ~ `to_time`) 내 수집된 데이터를 조회합니다.

    - from_time, to_time은 ISO8601 형식의 문자열이어야 합니다. (예: 2025-05-25T00:00:00)
    - count를 지정하지 않으면 기본 최대 100개의 데이터를 반환합니다.
    - 실패 시 에러 status code를 포함한 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/digital-objects/{do_id}/data?from={from_time}&to={to_time}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#모든 시뮬래아숀 정보 조회
@mcp.resource("mirrorlake://simulations")
def all_simulations() -> list[dict]:
    """
    all_digital_twins()를 통해 얻은 모든 디지털 트윈에 연결된 simulation들을 순회하며 전체 시뮬레이션 목록을 반환합니다.
    """
    twins = all_digital_twins()
    if not isinstance(twins, list):
        return {"error": "Invalid twins data"}

    result = []
    for dt in twins:
        dt_id = dt.get("digital_twin_id")
        try:
            res = requests.get(f"{BASE_URL}/digital-twins/{dt_id}/simulations")
            if res.ok:
                sim_list = res.json()
                for sim in sim_list:
                    sim["dt_id"] = dt_id
                    result.append(sim)
        except:
            continue
    return result

#모든 subscription 정보 조회
@mcp.resource("mirrorlake://subscriptions")
def all_subscriptions() -> list[dict]:
    """
    모든 디지털 트윈의 구독(subscription) 정보를 순회하며 수집하여 리스트로 반환합니다.
    """
    twins = all_digital_twins()
    if not isinstance(twins, list):
        return {"error": "Invalid twins data"}

    result = []
    for dt in twins:
        dt_id = dt.get("digital_twin_id")
        try:
            res = requests.get(f"{BASE_URL}/digital-twins/{dt_id}/subscriptions")
            if res.ok:
                sub_list = res.json()
                for sub in sub_list:
                    sub["dt_id"] = dt_id
                    result.append(sub)
        except:
            continue
    return result

#특정 시뮬레이션 데이터 n건 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/simulations/{simulation_id}/data/{count}")
def get_simulation_data_resource(dt_id: str, simulation_id: str, count: int = 1) -> list[dict] | dict:
    """
    특정 디지털 트윈(dt_id) 내 지정된 시뮬레이션(simulation) 결과의 최신 데이터를 조회합니다.
    
    count 인자를 통해 반환할 데이터 개수를 조절할 수 있으며, 실패 시 status code를 포함한 에러 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/simulations/{simulation_id}/data?count={count}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#특정 시뮬레이션 시간 구간 데이터 조회
@mcp.resource("mirrorlake://digital-twins/{dt_id}/simulations/{simulation_id}/data/{from_time}/{to_time}")
def get_simulation_data_by_time(dt_id: str, simulation_id: str, from_time: str, to_time: str| None = None) -> list[dict] | dict:
    """
    지정된 디지털 트윈(dt_id)의 시뮬레이션(simulation)로부터 시간 범위(`from_time` ~ `to_time`) 내 수집된 데이터를 조회합니다.

    - from_time, to_time은 ISO8601 형식의 문자열이어야 합니다. (예: 2025-05-25T00:00:00)
    - count를 지정하지 않으면 기본 최대 100개의 데이터를 반환합니다.
    - 실패 시 에러 status code를 포함한 dict를 반환합니다.
    """
    url = f"{BASE_URL}/digital-twins/{dt_id}/simulations/{simulation_id}/data?from={from_time}&to={to_time}"
    res = requests.get(url)
    return res.json() if res.ok else {"error": res.status_code}

#서버 실행(메인 진입점)
if __name__ == "__main__":
    mcp.run(transport="sse")
#@mcp.resource로 등록한 함수(=리소스)들을 SSE 프로토콜로 MCP 서버로 서비스 시작