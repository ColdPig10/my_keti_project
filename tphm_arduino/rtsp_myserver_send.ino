#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <IoT_Sensor_Library.h>
#include <IoT_Neopixel_Library.h>
#include <Adafruit_NeoPixel.h>
#include <IoT_Create_MirrorLake_Data_Library.h>

#define MAX_CONNECTION_TRY_CNT 30
#define NEOPIXEL_PIN 0         // Feather V2 내장 NeoPixel 데이터핀(0번)
#define NEOPIXEL_I2C_POWER 2   // Feather V2 내장 NeoPixel 파워 핀(2번)



/* WiFi SETUP */
char wifi_ssid[200] = ""; //와이파이 ID
char wifi_pass[200] = ""; //와이파이 비밀번호

int status = WL_IDLE_STATUS; //와이파이 연결 상태 저장 변수
WiFiClient client; //TCP클라이언트를 위한 객체 생성

// ===== FastAPI 서버 정보 (★ 여기만 본인 서버 IP로 변경!) =====
String fastapi_host = ""; // PC IP
int fastapi_port = ; //PC PORT
String fastapi_url = ""; //fastapi url

// 데이터 전송 주기(초)
unsigned long mirrorlake_interval = 10; // 10초마다 전송
unsigned long prev_ms_mirrorlake = 0;
int responseCode = 0;

struct HttpResponse {
  String message;
  int statusCode;
};

//reboot (SW reset)
void (*resetFunc)(void) = 0;

// 함수 프로토타입 선언
void connectWiFi();
HttpResponse httpPostRequest(String host, int port, String url, String body);

// -----------------------------------------------------------------
// WiFi 재연결 함수
void connectWiFi() {
  Serial.println("**** connectWiFi() ****");
  int connect_try_cnt = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    WiFi.begin(wifi_ssid, wifi_pass);
    connect_try_cnt++;
    if (connect_try_cnt > MAX_CONNECTION_TRY_CNT) {
      Serial.println("REBOOT");
      resetFunc();
    }
  }
  Serial.println("");
  Serial.println("> Connected to WiFi (from connectWiFi)");
}

// -----------------------------------------------------------------
// HTTP POST 함수
HttpResponse httpPostRequest(String host, int port, String url, String body) {
  HTTPClient httpClient;
  HttpResponse resp;
  unsigned long setTime = 0;
  unsigned long timeout = 3000L;
  String downmsg = "";

  String serverUrl = "http://" + host + ":" + String(port) + url;
  Serial.print("serverUrl: ");
  Serial.println(serverUrl);

  bool ok = httpClient.begin(serverUrl);
  if (!ok) {
    Serial.println("❌ httpClient.begin 실패!");
    resp.statusCode = -101;
    resp.message = "begin() failed";
    return resp;
  }

  httpClient.addHeader("Accept", "application/json");
  httpClient.addHeader("Content-Type", "application/json");

  setTime = millis();
  int httpResponseCode = httpClient.POST(body);

  if (httpResponseCode < 0) {
    Serial.printf("> Http error!, response code: %d, time: %d ms\n", httpResponseCode, millis() - setTime);
    Serial.printf("> Error string: %s\n", httpClient.errorToString(httpResponseCode).c_str());
    httpResponseCode = 408;  //Time out code
  } else {
    if (httpResponseCode == 201 || httpResponseCode == 400) {
      downmsg = httpClient.getString();
    }
  }

  httpClient.end();
  resp.message = downmsg;
  resp.statusCode = httpResponseCode;
  return resp;
}

// -----------------------------------------------------------------
// SETUP
void setup() {
  Serial.begin(115200);
  Serial.println("Device turned on");
  delay(200);

  Serial.println("before wireSHT31()");
  wireSHT31(); //IoT_Sensor_Library 초기화 함수
  Serial.println("after wireSHT31()");

  Serial.print("> Attempting to connect to SSID: ");
  Serial.print(wifi_ssid);
  Serial.print(", pass: ");
  Serial.println(wifi_pass);
  WiFi.begin(wifi_ssid, wifi_pass);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("");
  Serial.println("> Connected to WiFi");

  Serial.print("> ESP32 IP: ");
  Serial.println(WiFi.localIP());

  Serial.println("> Code ver: DeviceSoftware_TpHm_ver4");
  Serial.println("End of Setup...");
}

// -----------------------------------------------------------------
// LOOP
void loop() {
  Serial.println("Loop start");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Try reconnect WiFi");
    connectWiFi();
  }

  Serial.println("Before millis check");

  if ((unsigned long)(millis() - prev_ms_mirrorlake) > (mirrorlake_interval * 1000L)) {
    prev_ms_mirrorlake = millis();

    Serial.println("Before getTemperature");
    // 실제 센서 테스트 시 아래 주석 해제!
    // float temperature = getTemperature();
    // float humidity = getHumidity();
    // 임시값(센서 연결 전용)
    float temperature = 23.0;
    float humidity = 50.0;
    Serial.print("Temperature: ");
    Serial.println(temperature);
    Serial.print("Humidity: ");
    Serial.println(humidity);
    Serial.println("After getTemperature/humidity");

    // FastAPI용 JSON 데이터 생성
    String fastapi_data = "{\"sensor_id\":\"esp32_01\",\"value\":";
    fastapi_data += String(temperature, 2);
    fastapi_data += "}";

    Serial.print("Sending data to FastAPI: ");
    Serial.println(fastapi_data);

    Serial.println("Before httpPostRequest");
    HttpResponse fastapi_resp = httpPostRequest(fastapi_host, fastapi_port, fastapi_url, fastapi_data);
    Serial.print("FastAPI response code: ");
    Serial.println(fastapi_resp.statusCode);
    Serial.print("FastAPI response message: ");
    Serial.println(fastapi_resp.message);

    if (fastapi_resp.statusCode == 200 || fastapi_resp.statusCode == 201) {
      Serial.println("Blink green");
      blink_g(500);
    } else {
      Serial.println("Blink orange");
      blink_o(500);
    }
  }
  delay(100); // loop 무한재부팅 방지용
}