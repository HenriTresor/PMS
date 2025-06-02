from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date
import sqlite3

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "parking_system-1.db"

def get_connection():
   try:
    conn  = sqlite3.connect(DB_FILE)
    print('connected to db')
    return conn
   except Exception as e:
        print("-> Exception connecting to db: ", e)


@app.get("/vehicles-in-parking")
def vehicles_in_parking():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT plate_number, timestamp
            FROM plate_logs
            WHERE entry_exit = 'entry' AND plate_number NOT IN (
                SELECT plate_number FROM plate_logs WHERE entry_exit = 'exit'
            )
        """)
        result = cur.fetchall()
    return [{"plate_number": r[0], "entry_time": r[1]} for r in result]

@app.get("/today-revenue")
def today_revenue():
    today_str = date.today().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT SUM(amount) FROM plate_logs
            WHERE payment_status = 1 AND date(timestamp) = ?
        """, (today_str,))
        result = cur.fetchone()[0]
    return {"revenue_today": result or 0}

@app.get("/unauthorized-attempts")
def unauthorized_attempts():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM alerts
        """)
        result = cur.fetchone()[0]
    return {"unauthorized_access": result}
@app.get("/system-logs")
def get_system_logs():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get plate logs
    cursor.execute("""
        SELECT id, plate_number, payment_status, amount, entry_exit, timestamp
        FROM plate_logs
    """)
    plate_logs = [
        {
            "id": row[0],
            "plate_number": row[1],
            "payment_status": row[2],
            "amount": row[3],
            "entry_exit": row[4],
            "timestamp": row[5],
            "type": "plate_log"
        }
        for row in cursor.fetchall()
    ]

    # Get alerts
    cursor.execute("""
        SELECT id, plate_number, alert_type, message, timestamp
        FROM alerts
    """)
    alerts = [
        {
            "id": row[0],
            "plate_number": row[1],
            "alert_type": row[2],
            "message": row[3],
            "timestamp": row[4],
            "type": "alert"
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    # Combine and sort all logs by timestamp (descending)
    combined_logs = plate_logs + alerts
    combined_logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return combined_logs


@app.get("/recent-activity")
def recent_activity():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT plate_number, entry_exit, timestamp, payment_status
            FROM plate_logs
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
    data = []
    for plate, direction, ts, paid in rows:
        if direction == "entry":
            action = f"Checked in at {ts}"
            status = "PAID" if paid else "UNPAID"
        elif direction == "exit" :
            action = f"Unauthorized exit at {ts}"
            status = "UNPAID"
        else:
            action = f"Checked out at {ts}"
            status = "PAID" if paid else "UNPAID"
        data.append({
            "plate_number": plate,
            "action": action,
            "status": status
        })
    return data
