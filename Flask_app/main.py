import serial
import time
from flask import Flask, render_template
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

# Arduinoからデータを読み取ってリアルタイムで送信
def read_from_arduino():
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                # データをクライアントに送信
                socketio.emit('sensor_data', {'data': line})
        except serial.SerialException as e:
            print(f"シリアル通信エラー: {e}")
        time.sleep(1)

# スレッドを起動してArduinoからデータをリアルタイムで読み取る
@app.before_first_request
def before_first_request():
    thread = Thread(target=read_from_arduino)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    return render_template('index_v1.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
