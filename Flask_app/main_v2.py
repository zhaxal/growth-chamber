import serial
import time
import cv2
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from threading import Thread

# Flaskアプリケーションの設定
app = Flask(__name__)
socketio = SocketIO(app)

# シリアル通信設定
SERIAL_PORT = '/dev/ttyACM0'  # Arduinoのシリアルポート
BAUD_RATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
ser.setDTR(False) # Arduinoがリセットされるのを防ぐ
time.sleep(2) # Arduinoがリセットされるのを待つ
ser.flushInput() # バッファをクリア

# USBカメラの設定
camera = cv2.VideoCapture(0)  # USBカメラの取得

def read_from_arduino():
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                socketio.emit('sensor_data', {'data': line})
        except serial.SerialException as e:
            print(f"シリアル通信エラー: {e}")
        time.sleep(1)

# カメラ映像を取得してストリーミング
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.before_first_request
def before_first_request():
    thread = Thread(target=read_from_arduino)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    return render_template('index_v2.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
