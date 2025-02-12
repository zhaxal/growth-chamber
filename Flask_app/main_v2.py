import os
import time
import serial
import cv2
from flask import Flask, render_template, Response, request
from flask_socketio import SocketIO, emit
from threading import Thread

# Set a flag to simulate hardware when running locally.
LOCAL_TESTING = os.getenv("LOCAL_TESTING", "False").lower() in ("true", "1", "t")

# Default threshold values (to match Arduino defaults)
temp_threshold = 25.0
humid_low = 50.0
humid_high = 70.0

# Flask application settings
app = Flask(__name__)
socketio = SocketIO(app)

if not LOCAL_TESTING:
    # Serial communication settings
    SERIAL_PORT = '/dev/ttyACM0'  # Arduino serial port on RPi
    BAUD_RATE = 9600

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.setDTR(False)  # Prevent Arduino reset
    time.sleep(2)  # Wait for Arduino reset
    ser.flushInput()  # Clear buffer

    # USB camera setup
    camera = cv2.VideoCapture(0)  # Get USB camera
else:
    # For local testing, we don’t need to open a real serial device.
    ser = None
    # Optionally, you can load a sample image for streaming
    camera = None

def read_from_arduino():
    while True:
        if not LOCAL_TESTING:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    socketio.emit('sensor_data', {'data': line})
            except serial.SerialException as e:
                print(f"Serial error: {e}")
        else:
            # Simulated sensor data for local testing, including current thresholds.
            dummy_data = (f"Temperature: {temp_threshold}℃, Humidity: {humid_low} - {humid_high}%, "
                          "Fan: OFF, Peltier: OFF")
            socketio.emit('sensor_data', {'data': dummy_data})
        time.sleep(1)

def generate_frames():
    if not LOCAL_TESTING:
        while True:
            success, frame = camera.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    else:
        # For local testing, stream a static image (or a blank image) repeatedly.
        import numpy as np
        # Create a blank gray image
        frame = np.full((480, 640, 3), 200, dtype=np.uint8)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1)

@app.before_request
def before_request():
    thread = Thread(target=read_from_arduino)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    return render_template('index_v2.html', temp_threshold=temp_threshold, humid_low=humid_low, humid_high=humid_high)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('update_thresholds')
def update_thresholds(data):
    global temp_threshold, humid_low, humid_high
    try:
        temp_threshold = float(data.get('temp_threshold', temp_threshold))
        humid_low = float(data.get('humid_low', humid_low))
        humid_high = float(data.get('humid_high', humid_high))
        emit('threshold_update_success', {
            'temp_threshold': temp_threshold,
            'humid_low': humid_low,
            'humid_high': humid_high
        })
    except Exception as e:
        emit('threshold_update_failure', {'error': str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=3000)
