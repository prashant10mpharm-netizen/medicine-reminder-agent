import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_PATH = os.path.join("data", "medicine_box.db")

def get_active_medicines():
    # Connect to our database and pull everything into a table
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM medicines", conn)
    conn.close()

    today = datetime.now().date()

    # Convert text dates into real "date" objects so we can compare them
    df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
    df["refill_date"] = pd.to_datetime(df["refill_date"]).dt.date

    # A medicine is "active" if it already started (start_date is today or earlier)
    active = df[df["start_date"] <= today]

    return active, today

def check_refill_warnings(df, today, days_threshold=5):
    warnings = []
    for _, row in df.iterrows():
        days_left = (row["refill_date"] - today).days

        if days_left < 0:
            warnings.append(f"🔴 {row['medicine_name']} — refill date PASSED ({row['refill_date']}). Please refill soon.")
        elif days_left <= days_threshold:
            warnings.append(f"⚠️ {row['medicine_name']} — refill needed in {days_left} day(s), by {row['refill_date']}.")

    return warnings

def print_todays_schedule():
    active, today = get_active_medicines()

    print(f"\n📅 Medicine Schedule — {today.strftime('%A, %d %B %Y')}")
    print("=" * 55)

    # Show medicines grouped by time of day, in a sensible order
    time_order = ["Morning", "Afternoon", "Night", "As needed"]
    for time_slot in time_order:
        meds = active[active["time_of_day"] == time_slot]
        if len(meds) > 0:
            print(f"\n🕒 {time_slot}")
            for _, row in meds.iterrows():
                print(f"   • {row['medicine_name']} — {row['user_provided_instruction']}")

    # Show refill warnings at the end
    print("\n" + "=" * 55)
    warnings = check_refill_warnings(active, today)
    if warnings:
        print("\n🔔 Refill Reminders:")
        for w in warnings:
            print(f"   {w}")
    else:
        print("\n✅ No refills needed in the next 5 days.")

if __name__ == "__main__":
    print_todays_schedule()