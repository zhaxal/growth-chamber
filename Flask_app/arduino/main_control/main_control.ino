#include <DHT.h>

// ピン設定（変更なし）
const int DHTPIN = A2;
const int DHTTYPE = DHT22;
const int FAN_RELAY = 6;
const int PELTIER1 = 5;
const int PELTIER2 = 7;
const int LED_RELAY = 8;

// 設定値
const float TEMP_THRESHOLD = 25.0;
const float TEMP_HYSTERESIS = 1.0; // ヒステリシスを追加
const float HUMID_HIGH = 70.0;
const float HUMID_LOW = 50.0;

// 状態管理
DHT dht(DHTPIN, DHTTYPE);
unsigned long lastLightToggle = 0;
unsigned long lastSensorRead = 0;
bool lightState = true;  // 初期状態を"点灯"に修正
bool fanState = false;
bool peltierState = false;

void setup() {
    Serial.begin(9600);
    delay(2000);      // シリアル通信が安定するまで待機
    if (Serial) {
        Serial.println("シリアル通信開始");
    }


    dht.begin();
    
    pinMode(FAN_RELAY, OUTPUT);
    pinMode(PELTIER1, OUTPUT);
    pinMode(PELTIER2, OUTPUT);
    pinMode(LED_RELAY, OUTPUT);
    
    digitalWrite(FAN_RELAY, LOW);
    digitalWrite(PELTIER1, LOW);
    digitalWrite(PELTIER2, LOW);
    digitalWrite(LED_RELAY, HIGH);  // 初期状態を点灯（HIGH）に修正
    
    lastLightToggle = millis();
}

void loop() {
    unsigned long currentMillis = millis();

    // LEDライトのスケジュール制御（16時間点灯、8時間消灯）
    unsigned long lightInterval = lightState ? 16UL * 3600 * 1000 : 8UL * 3600 * 1000;
    if (currentMillis - lastLightToggle >= lightInterval) {
        lightState = !lightState;
        digitalWrite(LED_RELAY, lightState ? HIGH : LOW);
        lastLightToggle = currentMillis;
    }

    // 温湿度センサの読み取り（10秒ごと）
    if (currentMillis - lastSensorRead >= 10000) {
        lastSensorRead = currentMillis;
        float humidity = dht.readHumidity();
        float temperature = dht.readTemperature();

        if (isnan(humidity) || isnan(temperature)) {
            Serial.println("センサ読み取りエラー");
            return;
        }

        // 湿度制御（換気ファン）
        if (humidity >= HUMID_HIGH) {
            fanState = true;
        } 
        if (humidity <= HUMID_LOW) {
            fanState = false;
        }
        digitalWrite(FAN_RELAY, fanState ? HIGH : LOW);

        // 温度制御（ペルチェ素子）
        if (temperature >= TEMP_THRESHOLD + TEMP_HYSTERESIS) {
            peltierState = true;
        }
        if (temperature <= TEMP_THRESHOLD - TEMP_HYSTERESIS) {
            peltierState = false;
        }
        digitalWrite(PELTIER1, peltierState ? HIGH : LOW);
        digitalWrite(PELTIER2, peltierState ? HIGH : LOW);

        // データをシリアル送信
        Serial.print("温度:"); Serial.print(temperature); Serial.print("℃, ");
        Serial.print("湿度:"); Serial.print(humidity); Serial.print("%, ");
        Serial.print("換気ファン:"); Serial.print(fanState ? "ON" : "OFF"); Serial.print(", ");
        Serial.print("ペルチェ:"); Serial.println(peltierState ? "ON" : "OFF");
    }
}
