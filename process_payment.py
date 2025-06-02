import serial
import time
import serial.tools.list_ports
import platform
import sqlite3
from datetime import datetime

DB_FILE = 'parking_system-1.db'
RATE_PER_HOUR = 500

def detect_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    system = platform.system()
    for port in ports:
        desc = port.description.lower()
        if system == "Windows" and "com11" in port.device.lower():
            return port.device
        elif system == "Linux" and ("ttyusb" in port.device.lower() or "ttyacm" in port.device.lower()):
            return port.device
        elif system == "Darwin" and ("usbmodem" in port.device.lower() or "usbserial" in port.device.lower()):
            return port.device
    return None

def parse_arduino_data(line):
    try:
        parts = line.strip().split(',')
        print(f"[ARDUINO] Parsed parts: {parts}")
        if len(parts) != 2:
            return None, None
        plate = parts[0].strip().upper()
        balance_str = ''.join(c for c in parts[1] if c.isdigit())
        if balance_str:
            balance = int(balance_str)
            return plate, balance
        return None, None
    except ValueError as e:
        print(f"[ERROR] Value error in parsing: {e}")
        return None, None

def process_payment(plate, balance, ser):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get the latest unpaid entry for the plate
        cursor.execute('''
            SELECT id, timestamp FROM plate_logs
            WHERE plate_number = ? AND payment_status = 0
            ORDER BY timestamp DESC LIMIT 1
        ''', (plate,))
        result = cursor.fetchone()

        if not result:
            print("[PAYMENT] Plate not found or already paid.")
            return

        log_id, entry_time_str = result
        entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
        exit_time = datetime.now()
        hours_spent = int((exit_time - entry_time).total_seconds() / 3600) + 1
        amount_due = hours_spent * RATE_PER_HOUR

        if balance < amount_due:
            print(f"[PAYMENT] Insufficient balance: {balance} < {amount_due}")
            ser.write(b'I\n')
            return

        # Wait for Arduino to say "READY"
        print("[WAIT] Waiting for Arduino to be READY...")
        start_time = time.time()
        while True:
            if ser.in_waiting:
                arduino_response = ser.readline().decode().strip()
                print(f"[ARDUINO] {arduino_response}")
                if arduino_response == "READY":
                    break
            if time.time() - start_time > 10:
                print("[ERROR] Timeout waiting for Arduino READY")
                return
            time.sleep(0.1)

        new_balance = balance - amount_due
        ser.write(f"{new_balance}\r\n".encode())
        print(f"> Sent new balance to Arduino: {new_balance} RWF")


        # Wait for Arduino to confirm the write
        start_time = time.time()
        print("[WAIT] Waiting for Arduino confirmation...")
        while True:
            if ser.in_waiting:
                confirm = ser.readline().decode().strip()
                print(f"[ARDUINO] {confirm}")
                if "DONE" in confirm:
                    print("[ARDUINO] Write confirmed")
                    cursor.execute('''
                        UPDATE plate_logs
                        SET payment_status = 1
                        WHERE id = ?
                    ''', (log_id,))
                    conn.commit()
                    break
            if time.time() - start_time > 10:
                print("[ERROR] Timeout waiting for confirmation")
                break
            time.sleep(0.1)

        conn.close()
    except Exception as e:
        print(f"[ERROR] Payment processing failed: {e}")

def main():
    port = detect_arduino_port()
    if not port:
        print("[ERROR] Arduino not found")
        return

    try:
        ser = serial.Serial(port, 9600, timeout=2)
        print(f"[CONNECTED] Listening on {port}")
        time.sleep(2)
        ser.reset_input_buffer()

        while True:
            try:
                if ser.in_waiting:
                    line = ser.readline().decode().strip()
                    if line and ',' in line:
                        print(f"[SERIAL] Received: {line}")
                        plate, balance = parse_arduino_data(line)
                        if plate and balance is not None:
                            process_payment(plate, balance, ser)
            except serial.SerialException as e:
                print(f"[ERROR] Serial communication failed: {e}")
                time.sleep(1)
            time.sleep(0.1)

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    except KeyboardInterrupt:
        print("[EXIT] Program terminated")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    main()
