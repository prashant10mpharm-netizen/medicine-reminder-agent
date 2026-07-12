import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join("data", "medicine_box.db")
CSV_PATH = os.path.join("data", "medicine_schedule.csv")

def create_database():
    df = pd.read_csv(CSV_PATH)
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("medicines", conn, if_exists="replace", index=False)
    conn.close()
    print(f"✅ Database created successfully at {DB_PATH}")
    print(f"✅ Loaded {len(df)} medicine records")

def create_conversation_log_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            medicine_name TEXT,
            question TEXT,
            answer TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Conversation log table ready")

def create_dose_log_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dose_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT,
            dose_date TEXT,
            time_slot TEXT,
            taken_at TEXT,
            UNIQUE(medicine_name, dose_date, time_slot)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Dose log (adherence tracking) table ready")

if __name__ == "__main__":
    create_database()
    create_conversation_log_table()
    create_dose_log_table()