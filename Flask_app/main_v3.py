import serial
import time
import csv
import cv2
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread

# Flaskアプリケーションの設定
app = Flask(__name__)
socketio = SocketIO(app)

# シリアル通信設定
SERIAL_PORT = '/dev/ttyACM0'  # Arduinoのシリアルポート
BAUD_RATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
ser.setDTR(False)
time.sleep(2)
ser.flushInput()

# USBカメラの設定
camera = cv2.VideoCapture(0)  

# センサーデータをCSVに記録
LOG_FILE = "sensor_log.csv"

def log_data_to_csv(timestamp, temperature, humidity):
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature, humidity])

# Arduinoからのデータ読み取り
def read_from_arduino():
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"受信: {line}")  # デバッグ用
                    data_parts = line.split(',')
                    if len(data_parts) == 2:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        temperature = float(data_parts[0])
                        humidity = float(data_parts[1])
                        log_data_to_csv(timestamp, temperature, humidity)
                        socketio.emit('sensor_data', {'time': timestamp, 'temp': temperature, 'humidity': humidity})
        except (serial.SerialException, ValueError, UnicodeDecodeError) as e:
            print(f"シリアル通信エラー: {e}")
        time.sleep(1)

# カメラ映像を取得
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            print("カメラ映像を取得できませんでした。")
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.before_first_request
def before_first_request():
    thread = Thread(target=read_from_arduino)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    return render_template('index_v3.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_logs')
def get_logs():
    """ ログデータをJSON形式で取得 """
    logs = []
    try:
        with open(LOG_FILE, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 3:
                    logs.append({"time": row[0], "temp": float(row[1]), "humidity": float(row[2])})
    except FileNotFoundError:
        print("ログファイルが見つかりませんでした。")
    
    return jsonify(logs)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
