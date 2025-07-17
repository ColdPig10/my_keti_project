import serial
import psycopg2
import json
from datetime import datetime

# PostgreSQL 연결 설정
conn = psycopg2.connect(
    dbname='sensor_db',
    user='sensor_user',
    password='',  # 실제 설정한 비밀번호 입력
    host='localhost',
    port=''
)
cursor = conn.cursor()

# 시리얼 포트 설정
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
print("Listening on /dev/ttyACM0...")

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            continue

        # 예: {"data":{"temperature":27.66,"humidity":52.95}}
        if line.startswith("{") and "temperature" in line and "humidity" in line:
            data = json.loads(line)
            temperature = data["data"]["temperature"]
            humidity = data["data"]["humidity"]

            cursor.execute(
                "INSERT INTO sensor_data (temperature, humidity) VALUES (%s, %s)",
                (temperature, humidity)
            )
            conn.commit()
            print(f"[{datetime.now()}] Inserted: Temp={temperature}, Hum={humidity}")
    except Exception as e:
        print("Error:", e)
        continue