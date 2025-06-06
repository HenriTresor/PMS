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
pytesseract.pytesseract.tesseract_cmd = r'Tesseract-OCR\tesseract.exe'
model = YOLO('model.pt')
save_dir = 'plates'
os.makedirs(save_dir, exist_ok=True)
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
cursor.execute('''
    CREATE TABLE IF NOT EXISTS plate_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT NOT NULL,
        payment_status INTEGER DEFAULT 0,
        amount INTEGER DEFAULT 0,
        entry_exit TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
''')
cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT,
                alert_type TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
conn.commit()

# === Arduino Distance Fetch ===
def get_ultrasonic_distance():
    if not arduino:
        return 999
    try:
        arduino.reset_input_buffer()
        arduino.write(b'd')
        line = arduino.readline().decode().strip()
        return float(line)
    except Exception as e:
        print(f"[WARN] Failed to read distance: {e}")
        return 999

# === Entry System Logic ===
cap = cv2.VideoCapture(0)
plate_buffer = []
last_saved_plate = None
last_entry_time = 0
entry_cooldown = 300  # seconds

print("[ENTRY SYSTEM] Running. Press 'q' to exit.")

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

                    # OCR Processing
                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    plate_text = pytesseract.image_to_string(
                        thresh,
                        config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    ).strip().replace(" ", "")

                    if "RA" in plate_text:
                        start = plate_text.find("RA")
                        candidate = plate_text[start:start + 7]
                        if len(candidate) == 7 and candidate[:3].isalpha() and candidate[3:6].isdigit() and candidate[6].isalpha():
                            print(f"[DETECTED] Plate: {candidate}")
                            plate_buffer.append(candidate)

                            # Save plate image
                            timestamp_str = time.strftime('%Y%m%d_%H%M%S')
                            cv2.imwrite(os.path.join(save_dir, f"{candidate}_{timestamp_str}.jpg"), plate_img)

                            if len(plate_buffer) >= 3:
                                most_common = Counter(plate_buffer).most_common(1)[0][0]
                                plate_buffer.clear()
                                now = time.time()

                                if most_common != last_saved_plate or (now - last_entry_time) > entry_cooldown:
                                    timestamp_db = time.strftime('%Y-%m-%d %H:%M:%S')
                                    try:
                                        with conn:
                                            cursor.execute('''
                                                    SELECT * FROM plate_logs
                                                    WHERE plate_number = ? AND payment_status = 0
                                                    ORDER BY timestamp DESC
                                                    LIMIT 1
                                                    ''', (most_common,))
                                            unpaid_record = cursor.fetchone()

                                            if unpaid_record:
                                                    print(f"[BLOCKED] Vehicle {most_common} has unpaid entry. Entry denied.")
                                                    timestamp_alert = time.strftime('%Y-%m-%d %H:%M:%S')
                                                    with conn:
                                                        conn.execute('''INSERT INTO alerts (plate_number, alert_type, message, timestamp)
                                                                    VALUES (?, ?, ?, ?)''',
                                                                (most_common, 'unpaid_entry_attempt',
                                                                f'Blocked re-entry for unpaid vehicle {most_common}', timestamp_alert))
                                                        if arduino:
                                                            arduino.write(b'2')
                                            else:
                                                timestamp_db = time.strftime('%Y-%m-%d %H:%M:%S')
                                                try:
                                                    with conn:
                                                        conn.execute('''INSERT INTO plate_logs (plate_number, payment_status, entry_exit, timestamp)
                                                                        VALUES (?, ?, ?, ?)''',
                                                                    (most_common, 0, 'entry', timestamp_db))
                                                    print(f"[LOGGED] Entry: {most_common} at {timestamp_db}")

                                                    if arduino:
                                                        arduino.write(b'1')  # Open gate
                                                        print("[GATE] Opening...")
                                                        time.sleep(15)
                                                        arduino.write(b'0')  # Close gate
                                                        print("[GATE] Closing...")

                                                    last_saved_plate = most_common
                                                    last_entry_time = now
                                                except sqlite3.OperationalError as e:
                                                    print(f"[DB ERROR] Could not write to DB: {e}")
                                                    time.sleep(1)
                                    except Exception as e:
                                        print("Exception occurred:", e)
                                else:
                                    arduino.write(b'2')
                                    print("[SKIPPED] Duplicate entry within cooldown.")

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
    print("[EXITED] Clean shutdown.")
