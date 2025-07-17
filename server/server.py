from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pydantic import BaseModel
from typing import List

#pydantic 모델 추가

class SensorInfoIn(BaseModel):
    sensor_identifier: str
    sensor_name: str
    owner: str
    description: str
    data_source_type: str
    internal_delivery_mode: str
    creator_id: str
    data_source_format: str
    tags: List[str]
    
#pydantic 입력 모델 rtsp

class DetectionItem(BaseModel):
    label: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]

class RTSPDetectionIn(BaseModel):
    sensor_id: str
    detections: List[DetectionItem]


# PostgreSQL 연결 문자열
DB_URL = "" #DB URL

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

#메타데이터 저장용 테이블
class SensorInfo(Base):
    __tablename__ = "sensor_info"
    id = Column(Integer, primary_key=True, index=True)
    sensor_identifier = Column(String(100), unique=True, nullable=False)
    sensor_name = Column(String(100), nullable=False)
    owner = Column(String(50), nullable=False)
    description = Column(String(255))
    data_source_type = Column(String(50))
    internal_delivery_mode = Column(String(50))
    creator_id = Column(String(50))
    data_source_format = Column(String(50))
    tags = Column(String(255))  # 간단하게 문자열 리스트를 쉼표로 저장

# ORM 모델 정의
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(100), nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

# pydantic 모델 (입력용)
class SensorDataIn(BaseModel):
    data: dict  # 이 안에 "temperature", "humidity"가 들어 있음
    
# 출력용 Pydantic 모델
class SensorDataOut(BaseModel):
    sensor_id: str
    temperature: float
    humidity: float
    created_at: datetime

    class Config:
        orm_mode = True  # SQLAlchemy 모델을 Pydantic으로 변환 허용

# RTSP DB 테이블 추가
class RTSPDetection(Base):
    __tablename__ = "rtsp_detections"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(100), nullable=False)
    label = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

# FastAPI 인스턴스 생성
app = FastAPI()

# 이 한 줄이 테이블을 실제 DB에 만듭니다!
Base.metadata.create_all(bind=engine)

# METHOD - POST - 센서 메타데이터 등록
@app.post("/sensor-info/")
def register_sensor(info: SensorInfoIn):
    db = SessionLocal()
    try:
        sensor = SensorInfo(
            sensor_identifier=info.sensor_identifier,
            sensor_name=info.sensor_name,
            owner=info.owner,
            description=info.description,
            data_source_type=info.data_source_type,
            internal_delivery_mode=info.internal_delivery_mode,
            creator_id=info.creator_id,
            data_source_format=info.data_source_format,
            tags=",".join(info.tags)  # List[str] → str
        )
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        return {"message": "Sensor metadata 등록 완료!", "id": sensor.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

from typing import List

# METHOD - POST - 센서 측정 데이터 주기적 저장
@app.post("/sensor-data/{sensor_id}")
def create_sensor_data(sensor_id: str, data: SensorDataIn):
    db = SessionLocal()
    try:
        sensor_entry = SensorData(
            sensor_id=sensor_id,
            temperature=data.data["temperature"],
            humidity=data.data["humidity"],
        )
        db.add(sensor_entry)
        db.commit()
        db.refresh(sensor_entry)
        return {"message": "센서 데이터 저장 완료!", "id": sensor_entry.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# METHOD - GET - 전체 센서 정보 조회
@app.get("/sensor-info/")
def get_sensor_info():
    db = SessionLocal()
    try:
        sensors = db.query(SensorInfo).all()
        result = []
        for s in sensors:
            result.append({
                "sensor_identifier": s.sensor_identifier,
                "sensor_name": s.sensor_name,
                "owner": s.owner,
                "description": s.description,
                "tags": s.tags.split(",")  # 문자열을 다시 리스트로 변환
            })
        return result
    finally:
        db.close()

# METHOD - GET - 전체 센서 측정 값 조회
@app.get("/sensor-data/", response_model=List[SensorDataOut])
def read_all_data():
    db = SessionLocal()
    try:
        return db.query(SensorData).order_by(SensorData.created_at.desc()).all()
    finally:
        db.close()

# METHOD - GET - 특정 센서 측정 값 조회
@app.get("/sensor-data/{sensor_id}", response_model=List[SensorDataOut])
def read_sensor_data(sensor_id: str):
    db = SessionLocal()
    try:
        return db.query(SensorData)\
                 .filter(SensorData.sensor_id == sensor_id)\
                 .order_by(SensorData.created_at.desc())\
                 .all()
    finally:
        db.close()

# METHOD - GET - 특정 센서 측정 값 조회 (TIME)
@app.get("/sensor-data/{sensor_id}/range", response_model=List[SensorDataOut])
def get_sensor_data_in_range(
    sensor_id: str,
    start_time: datetime = Query(..., description="시작 시간 (예: 2025-07-11T10:00:00)"),
    end_time: datetime = Query(..., description="끝 시간 (예: 2025-07-11T12:00:00)")
):
    db = SessionLocal()
    try:
        result = db.query(SensorData)\
                   .filter(SensorData.sensor_id == sensor_id)\
                   .filter(SensorData.created_at >= start_time)\
                   .filter(SensorData.created_at <= end_time)\
                   .order_by(SensorData.created_at)\
                   .all()
        return result
    finally:
        db.close()

# METHOD - GET - 특정 센서 측정 값 조회 (COUNT)
@app.get("/sensor-data/{sensor_id}/recent", response_model=List[SensorDataOut])
def get_recent_sensor_data(sensor_id: str, count: int = Query(5, gt=0)):
    db = SessionLocal()
    try:
        data = (
            db.query(SensorData)
            .filter(SensorData.sensor_id == sensor_id)
            .order_by(SensorData.created_at.desc())
            .limit(count)
            .all()
        )
        return data
    finally:
        db.close()
        
# METHOD - POST 엔드포인트 추가
@app.post("/rtsp-detections/")
def receive_rtsp_detections(payload: RTSPDetectionIn):
    db = SessionLocal()
    try:
        for det in payload.detections:
            entry = RTSPDetection(
                sensor_id=payload.sensor_id,
                label=det.label,
                confidence=det.confidence,
                x1=det.bbox[0],
                y1=det.bbox[1],
                x2=det.bbox[2],
                y2=det.bbox[3],
            )
            db.add(entry)
        db.commit()
        return {"message": "YOLO 추론 결과 저장 완료!", "count": len(payload.detections)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# METHOD - POST
@app.post("/rtsp-detections/rtsp-object")
def post_object(data: dict):
    db = SessionLocal()
    try:
        for k, v in data['data'].items():
            entry = ObjectDetection(
                sensor_id="rtsp-car",
                label=v['label_data'],
                score=v['score'],
                box_data=json.dumps(v['box_data']),
                mid_point=json.dumps(v['mid_point']),
                grid_index=v['grid_index']
            )
            db.add(entry)
        db.commit()
        return {"message": "객체 데이터 저장 완료!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# METHOD - GET 최근 탐지 결과
@app.get("/rtsp-detections/{sensor_id}")
def get_rtsp_detections(sensor_id: str, count: int = Query(10, gt=0)):
    db = SessionLocal()
    try:
        result = (
            db.query(RTSPDetection)
            .filter(RTSPDetection.sensor_id == sensor_id)
            .order_by(RTSPDetection.created_at.desc())
            .limit(count)
            .all()
        )
        return [
            {
                "label": r.label,
                "confidence": r.confidence,
                "bbox": [r.x1, r.y1, r.x2, r.y2],
                "timestamp": r.created_at
            }
            for r in result
        ]
    finally:
        db.close()

# RTSP 차량 객체 저장용 (Post)
@app.post("/rtsp-detections/rtsp-car")
def save_rtsp_car_data(data: dict):
    print("[RTSP POST] 받은 데이터:")
    print(data)
    return {"message": "RTSP 차량 객체 POST 성공!"}