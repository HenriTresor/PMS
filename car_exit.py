import cv2
from ultralytics import YOLO
import os
import time
import serial
import serial.tools.list_ports
import sqlite3
from collections import Counter
import pytesseract

# === Configuration ===
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
model = YOLO('best.pt')
db_file = 'parking_system-1.db'

# === Arduino Setup ===
def detect_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "USB-SERIAL" in port.description:
            return port.device
    return None

arduino_port = detect_arduino_port()
arduino = None
if arduino_port:
    print(f"[CONNECTED] Arduino on {arduino_port}")
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
else:
    print("[ERROR] Arduino not detected.")

# === DB Setup ===
conn = sqlite3.connect(db_file, check_same_thread=False)
cursor = conn.cursor()

def get_ultrasonic_distance():
    if not arduino:
        return 999
    try:
        arduino.reset_input_buffer()
        arduino.write(b'd')
        line = arduino.readline().decode().strip()
        return float(line)
    except Exception as e:
        print(f"[WARN] Distance read failed: {e}")
        return 999

def is_payment_complete(plate_number):
    cursor.execute('''
        SELECT payment_status, entry_exit FROM plate_logs 
        WHERE plate_number = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (plate_number,))
    row = cursor.fetchone()
    return row and row[0] == 1 and row[1] == 'entry'

def get_amount(plate_number):
    cursor.execute('''
    SELECT amount from plate_logs WHERE plate_number = ? ORDER BY timestamp DESC LIMIT 1
''', (plate_number,))
    row = cursor.fetchone()
    return row[0] if row else 0

# log alert
def log_alert(plate_number, alert_type, message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT,
                alert_type TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        alert = cursor.execute('''
            INSERT INTO alerts (plate_number, alert_type, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (plate_number, alert_type, message, timestamp))
        conn.commit()
        print(f"[ALERT LOGGED] {alert}: {message}")
    except sqlite3.OperationalError as e:
        print(f"[DB ALERT ERROR] {e}")
        conn.rollback()

# === Main Loop ===
cap = cv2.VideoCapture(0)
plate_buffer = []

print("[EXIT SYSTEM] Running. Press 'q' to quit.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        distance = get_ultrasonic_distance()
        print(f"[DISTANCE] {distance:.2f} cm")

        if distance <= 50:
            results = model(frame)
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    plate_img = frame[y1:y2, x1:x2]

                    # OCR
                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    plate_text = pytesseract.image_to_string(
                        thresh, config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    ).strip().replace(" ", "")

                    if "RA" in plate_text:
                        start = plate_text.find("RA")
                        candidate = plate_text[start:start + 7]
                        if len(candidate) == 7 and candidate[:3].isalpha() and candidate[3:6].isdigit() and candidate[6].isalpha():
                            print(f"[DETECTED] Plate: {candidate}")
                            plate_buffer.append(candidate)

                            if len(plate_buffer) >= 3:
                                most_common = Counter(plate_buffer).most_common(1)[0][0]
                                plate_buffer.clear()
                                timestamp_db = time.strftime('%Y-%m-%d %H:%M:%S')

                                if is_payment_complete(most_common):    
                                    try:
                                        with conn:
                                            amount =  get_amount(most_common)
                                            conn.execute('''
                                                INSERT INTO plate_logs (plate_number, payment_status, amount, entry_exit, timestamp)
                                                VALUES (?, ?, ?, ?, ?)
                                            ''', (most_common, 1, amount, 'exit', timestamp_db))
                                        print(f"[GRANTED] Exit allowed: {most_common} at {timestamp_db}")

                                        if arduino:
                                            arduino.write(b'1')  # open gate
                                            print("[GATE] Open command sent.")
                                            time.sleep(15)
                                            arduino.write(b'0')  # close gate
                                            print("[GATE] Close command sent.")
                                    except sqlite3.OperationalError as e:
                                        print(f"[DB ERROR] Exit logging failed: {e}")
                                        time.sleep(1)
                                else:
                                    print(f"[DENIED] Payment incomplete for {most_common}")
                                    log_alert(most_common, 'payment_incomplete', 'Payment incomplete')
                                    if arduino:
                                        arduino.write(b'2')  # alert via buzzer/LED
                                        print("[ALERT] Buzzer triggered.")
                        else:
                            print("[INVALID] Detected text does not match plate format.")

                    cv2.imshow("Plate", plate_img)
                    cv2.imshow("Processed", thresh)
                    time.sleep(0.5)

        annotated = results[0].plot() if distance <= 50 else frame
        cv2.imshow("Webcam", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user.")

finally:
    cap.release()
    if arduino:
        arduino.close()
    conn.close()
    cv2.destroyAllWindows()
    print("[SHUTDOWN] Exit system stopped.")
