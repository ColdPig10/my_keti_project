import serial
import sqlite3
import time

# ESP32 연결된 시리얼 포트 확인 후 수정 (예: COM3, /dev/ttyUSB0 등)
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

# DB 파일 및 테이블 초기화
conn = sqlite3.connect('sensor_data.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS sensor_data (timestamp TEXT, temperature REAL, humidity REAL)')
conn.commit()

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
print(f"Listening on {SERIAL_PORT}...")

temperature = None
humidity = None

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            continue

        if line.startswith("temperature:"):
            temperature = float(line.split(":")[1])
        elif line.startswith("humidity:"):
            humidity = float(line.split(":")[1])

        # 둘 다 값이 들어오면 저장
        if temperature is not None and humidity is not None:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO sensor_data (timestamp, temperature, humidity) VALUES (?, ?, ?)',
                           (timestamp, temperature, humidity))
            conn.commit()
            print(f"[{timestamp}] Saved → Temp: {temperature}°C, Humidity: {humidity}%")
            temperature = None
            humidity = None

    except Exception as e:
        print("Error:", e)
        break

conn.close()
