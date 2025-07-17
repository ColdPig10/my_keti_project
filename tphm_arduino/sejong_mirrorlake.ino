#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <IoT_Sensor_Library.h>
#include <IoT_Neopixel_Library.h>
#include <IoT_Create_MirrorLake_Data_Library.h>

#define MAX_CONNECTION_TRY_CNT 30

// 실험실 MirrorLake에 센서 데이터 전송

/* WiFi SETUP */
char wifi_ssid[200] = ""; //와이파이 ID
char wifi_pass[200] = ""; //와이파이 비밀번호

int status = WL_IDLE_STATUS; //와이파이 연결 상태 저장 변수
WiFiClient client; //TCP클라이언트를 위한 객체 생성


struct HttpResponse {
  String message;
  int statusCode;
};


/* Mirrorlake - 고정값 */
String mirrorlake_host = ""; //mirrorlake서버 ip주소
int mirrorlake_port = ; //서버의 포트 번호 - http통신에 사용
String mirrorlake_dt_id = ""; //디지털트윈id - 서버에서 장치 식별용
String mirrorlake_sensor_id = ""; //센서 고유id


unsigned long mirrorlake_interval = 10; //데이터 전송 주기수
unsigned long prev_ms_mirrorlake = 0; // 마지막 전송 시간
int responseCode = 0; // 마지막 http 응답 코드 저장용 변수

//reboot (SW reset)
void (*resetFunc)(void) = 0;

// 함수 프로토타입 선언 (setup() 위에 추가)
void connectWiFi();
HttpResponse httpPostRequestWithLED(String host, int port, String url, String body, String color);
HttpResponse httpPostRequest(String host, int port, String url, String body);

////////////////////////////////////////////////////////////////////////
///////////////////////////// SETUP ////////////////////////////////////
////////////////////////////////////////////////////////////////////////

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial.println("Device turned on");
  delay(200);

  wireSHT31(); //IoT_Sensor_Library 초기화 함수
  
  Serial.print("> Attempting to connect to SSID: ");
  Serial.print(wifi_ssid);
  Serial.print(", pass: ");
  Serial.println(wifi_pass);
  WiFi.begin(wifi_ssid, wifi_pass);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    
  }
  Serial.println("");
  Serial.println("> Connected to WiFi");

  Serial.print("> Connected to WiFi\n");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  Serial.print("> My mirrorlake sensor ID: ");
  Serial.println(mirrorlake_sensor_id);
  Serial.println("> Code ver: DeviceSoftware_TpHm_ver4");
  Serial.println("End of Setup...");
}


////////////////////////////////////////////////////////////////////////
///////////////////////////// LOOP /////////////////////////////////////
////////////////////////////////////////////////////////////////////////

void loop() {
  // put your main code here, to run repeatedly:
  if (WiFi.status() != WL_CONNECTED) //WIFI Reconnect
  {
    connectWiFi();
  }
  
  // mirrorlake로 sensor data 전송
  if ((unsigned long)(millis() - prev_ms_mirrorlake) > (mirrorlake_interval * 1000L)) {
    prev_ms_mirrorlake = millis();

    float temperature = getTemperature();
    float humidity = getHumidity();

    String mirrorlake_data = create_mirrorlake_data_TpHm(temperature, humidity);
    String url = "/mirrorlake/v1/digital-twins/" + mirrorlake_dt_id + "/sensors/" + mirrorlake_sensor_id + "/data";
    //결과 성공 시 녹색 led
    HttpResponse resp = httpPostRequestWithLED(mirrorlake_host, mirrorlake_port, url, mirrorlake_data, "green");
    Serial.print("mirrorlake response code: ");
    Serial.println(resp.statusCode);
    Serial.println(mirrorlake_data);
  }
}

////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////

//HTTP POST REQUEST
HttpResponse httpPostRequest(String host, int port, String url, String body) {
  HTTPClient httpClient;
  HttpResponse resp;
  unsigned long setTime = 0;
  unsigned long timeout = 3000L;
  String downmsg = "";  // return할 string

  //begin 성공 여부 확
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

  //실패 이유 분석 출
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

  
  
//  httpClient.begin(serverUrl);
//  httpClient.addHeader("Accept", "application/json");
//  httpClient.addHeader("Content-Type", "application/json");
//  
//  setTime = millis();
//  int httpResponseCode = httpClient.POST(body);
//  if (httpResponseCode < 0) {
//    Serial.printf("> Http error!, response code: %d, time: %d second\n", httpResponseCode, millis() - setTime);
//    httpResponseCode = 408;  //Time out code
//  } else {
//    if (httpResponseCode == 201) {
//      downmsg = httpClient.getString();
//    } else if (httpResponseCode == 400) {  //ERROR
//      downmsg = httpClient.getString();
//    }
//  }
//  // Close the connection
//  httpClient.end();
//  resp.message = downmsg;
//  resp.statusCode = httpResponseCode;
//  return resp;
//}

//POST HTTP WITH LED
//   - color: 'blue', or 'green', or "yellow"
//   - if http request success --> designated LED blink / fail --> Red LED blink
HttpResponse httpPostRequestWithLED(String host, int port, String url, String body, String color) {
  HttpResponse resp;
  resp = httpPostRequest(host, port, url, body);
  //Serial.printf("responseCode: %d\n", responseCode);
  if (resp.statusCode == 201) {
    for (int i = 0; i < 2; i++) {
      if (color == "blue") blink_b(500);
      if (color == "green") blink_g(500);
      if (color == "yellow") blink_y(500);
    }
  } else {
    // failed
    for (int i = 0; i < 2; i++) {
      blink_o(500);
    }
  }
  return resp;
}

long getWifiRSSI() {
  long val = 0;
  val = WiFi.RSSI();
  return val;
}

void connectWiFi() {
  Serial.println("**** connectWiFi() ****");
  int connect_try_cnt = 0;
  while (WiFi.status() != WL_CONNECTED) {
    blink_p(500);
    Serial.print("Attempting to connect to SSID: ");
    Serial.print(wifi_ssid);
    Serial.print(", pass: ");
    Serial.println(wifi_pass);
    status = WiFi.begin(wifi_ssid, wifi_pass);
    connect_try_cnt++;
    Serial.print("WiFi connection try count: ");
    Serial.println(connect_try_cnt);
    delay(random(500, 5000));
    if (connect_try_cnt > MAX_CONNECTION_TRY_CNT) {
      Serial.println("REBOOT");
      resetFunc();
    }
  }
}
