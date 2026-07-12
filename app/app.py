import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import base64
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from label_explainer import explain_label
from image_reader import read_medicine_image
from pdf_export import generate_medicine_summary_pdf

load_dotenv()
CAREGIVER_PIN = os.getenv("CAREGIVER_PIN", "5678")
USER_NAME = "Prashant"

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "medicine_box.db")
BEEP_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "reminder_beep.wav")
TIME_OPTIONS = ["Morning", "Afternoon", "Night", "As needed"]

TEAL = "14B8A6"
TEAL_DARK = "0F3D39"
TEAL_TEXT = "0F766E"
SIDEBAR_BG = "0B1416"
TEXT_DARK = "111827"
GRAY = "6B7280"
LIGHTGRAY = "F5F7F8"
ORANGE = "F59E0B"
RED = "DC2626"

def load_medicines():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM medicines", conn)
    conn.close()
    return df

def get_time_list(time_of_day_str):
    return [t.strip() for t in str(time_of_day_str).split(",") if t.strip()]

def get_refill_status(refill_date_str, today):
    refill_date = pd.to_datetime(refill_date_str).date()
    days_left = (refill_date - today).days
    if days_left < 0:
        return "overdue", days_left
    elif days_left <= 5:
        return "soon", days_left
    else:
        return "ok", days_left

def update_medicine(medicine_name, new_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE medicines
        SET user_provided_instruction = ?, time_of_day = ?, start_date = ?,
            refill_date = ?, notes = ?, doctor_pharmacist_contact = ?
        WHERE medicine_name = ?
    """, (new_data["instruction"], new_data["time_of_day"], new_data["start_date"],
          new_data["refill_date"], new_data["notes"], new_data["doctor_contact"], medicine_name))
    conn.commit()
    conn.close()

def delete_medicine(medicine_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicines WHERE medicine_name = ?", (medicine_name,))
    conn.commit()
    conn.close()

def add_medicine(new_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO medicines (medicine_name, user_provided_instruction, time_of_day,
                                start_date, refill_date, notes, doctor_pharmacist_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (new_data["medicine_name"], new_data["instruction"], new_data["time_of_day"],
          new_data["start_date"], new_data["refill_date"], new_data["notes"], new_data["doctor_contact"]))
    conn.commit()
    conn.close()

def save_to_memory(medicine_name, question, answer):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversation_log (timestamp, medicine_name, question, answer)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), medicine_name, question, answer))
    conn.commit()
    conn.close()

def get_recent_memory(medicine_name=None, limit=20):
    conn = sqlite3.connect(DB_PATH)
    if medicine_name:
        log_df = pd.read_sql(
            "SELECT * FROM conversation_log WHERE medicine_name = ? ORDER BY id DESC LIMIT ?",
            conn, params=(medicine_name, limit))
    else:
        log_df = pd.read_sql("SELECT * FROM conversation_log ORDER BY id DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return log_df

def mark_dose_taken(medicine_name, time_slot, dose_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO dose_log (medicine_name, dose_date, time_slot, taken_at)
        VALUES (?, ?, ?, ?)
    """, (medicine_name, dose_date, time_slot, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def unmark_dose_taken(medicine_name, time_slot, dose_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dose_log WHERE medicine_name = ? AND dose_date = ? AND time_slot = ?",
                   (medicine_name, dose_date, time_slot))
    conn.commit()
    conn.close()

def get_taken_doses(dose_date):
    conn = sqlite3.connect(DB_PATH)
    log_df = pd.read_sql("SELECT medicine_name, time_slot, taken_at FROM dose_log WHERE dose_date = ?",
                          conn, params=(dose_date,))
    conn.close()
    return log_df

def get_taken_doses_set(dose_date):
    log_df = get_taken_doses(dose_date)
    return set(zip(log_df["medicine_name"], log_df["time_slot"]))

def get_expected_doses(df):
    expected = []
    for _, row in df.iterrows():
        for t in get_time_list(row["time_of_day"]):
            if t != "As needed":
                expected.append((row["medicine_name"], t))
    return set(expected)

def calculate_streak(df):
    expected = get_expected_doses(df)
    if not expected:
        return 0
    streak = 0
    day = datetime.now().date() - timedelta(days=1)
    while True:
        taken = get_taken_doses_set(str(day))
        if expected.issubset(taken):
            streak += 1
            day -= timedelta(days=1)
        else:
            break
    return streak

def get_beep_audio_html():
    if not os.path.exists(BEEP_PATH):
        return ""
    with open(BEEP_PATH, "rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode()
    return f'<audio autoplay="true"><source src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>'

def get_current_time_slot():
    hour = datetime.now().hour
    if hour < 12:
        return "Morning"
    elif hour < 17:
        return "Afternoon"
    else:
        return "Night"

def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

def get_weekly_adherence_data(df):
    expected = get_expected_doses(df)
    total_expected = len(expected)
    rows = []
    for i in range(6, -1, -1):
        day = datetime.now().date() - timedelta(days=i)
        taken = get_taken_doses_set(str(day))
        taken_count = len(expected.intersection(taken))
        pct = round((taken_count / total_expected) * 100) if total_expected > 0 else 0
        rows.append({"Date": day.strftime("%a"), "Taken": taken_count, "Expected": total_expected, "Adherence %": pct})
    return pd.DataFrame(rows)

def count_refills_due(df, today):
    count = 0
    for _, row in df.iterrows():
        status, _ = get_refill_status(row["refill_date"], today)
        if status in ("overdue", "soon"):
            count += 1
    return count

st.set_page_config(page_title="Medicine Reminder & Label Explainer", page_icon="💊", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:wght@600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
h1, h2, h3 {{ font-family: 'Lora', serif !important; color: #{TEXT_DARK}; }}

section[data-testid="stSidebar"] {{ background: #{SIDEBAR_BG} !important; }}
section[data-testid="stSidebar"] * {{ color: #CBD5D9 !important; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
    padding: 10px 12px; border-radius: 10px; margin-bottom: 4px;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
    background: #{TEAL} !important;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {{
    color: #FFFFFF !important; font-weight: 600 !important;
}}

div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {{
    border-radius: 999px !important;
    border: 1.5px solid #{TEAL} !important;
    color: #{TEAL_TEXT} !important;
    background: #FFFFFF !important;
    font-weight: 600 !important;
    padding: 0.4rem 1rem !important;
}}
div[data-testid="stButton"] button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
    background: #{TEAL} !important; color: #FFFFFF !important; border-color: #{TEAL} !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 14px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}}

.pill {{ display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:999px; font-weight:600; font-size:13px; white-space:nowrap; }}
.pill-orange {{ background:#FEF3E2; color:#B45309; }}
.pill-red {{ background:#FDEAEA; color:#B91C1C; }}
.pill-teal {{ background:#{TEAL}; color:#FFFFFF; }}
.eyebrow {{ color:#{TEAL_TEXT}; font-weight:700; font-size:12.5px; letter-spacing:1.5px; text-transform:uppercase; }}
</style>
""", unsafe_allow_html=True)

if "language" not in st.session_state:
    st.session_state["language"] = "English"
if "caregiver_unlocked" not in st.session_state:
    st.session_state["caregiver_unlocked"] = False
if "scan_added_indices" not in st.session_state:
    st.session_state["scan_added_indices"] = set()

st.sidebar.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:22px;">
    <div style="width:44px; height:44px; border-radius:50%; background:#{TEAL}; display:flex; align-items:center; justify-content:center; font-size:20px;">💊</div>
    <div>
        <div style="font-weight:700; font-size:15px; color:#FFFFFF; line-height:1.2;">Medicine Reminder<br>& Label Explainer</div>
        <div style="font-size:11px; color:#{TEAL}; letter-spacing:1px;">AIXCEL</div>
    </div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Go to:", [
    "📅 Today's Schedule", "💬 Explain a Label", "🗂️ Manage Medicines",
    "📷 Scan Prescription", "📊 Adherence Report", "👥 Caregiver View",
    "ℹ️ Limitations & Responsible Use"
], label_visibility="collapsed")

st.sidebar.markdown("""
<div style="position:fixed; bottom:20px; font-size:11px; color:#7C8B90; line-height:1.5;">
Personal organization tool.<br>Not a certified medical device.<br>Always consult your doctor or pharmacist.
</div>
""", unsafe_allow_html=True)

df = load_medicines()
today = datetime.now().date()
today_str = str(today)
selected_language = st.session_state["language"]

if len(df) == 0 and page not in ["👥 Caregiver View", "ℹ️ Limitations & Responsible Use", "📷 Scan Prescription"]:
    st.info("👋 **Welcome!** You haven't added any medicines yet. Go to **🗂️ Manage Medicines** to add your first one.")
    st.stop()

# ============================================================
# PAGE 1 — TODAY'S SCHEDULE
# ============================================================

if page == "📅 Today's Schedule":
    taken_today = get_taken_doses_set(today_str)
    expected_today = get_expected_doses(df)
    current_slot = get_current_time_slot()
    streak = calculate_streak(df)
    refills_due = count_refills_due(df, today)

    col_greet, col_b1, col_b2 = st.columns([3, 1, 1])
    with col_greet:
        st.markdown(f'<div class="eyebrow">{today.strftime("%A, %d %B %Y").upper()}</div>', unsafe_allow_html=True)
        st.markdown(f"## {get_greeting()}, {USER_NAME}")
        st.caption("Here's what's on today, grouped by time of day.")
    with col_b1:
        st.markdown(f'<div style="text-align:right; padding-top:20px;"><span class="pill pill-orange">🔥 {streak} day streak</span></div>', unsafe_allow_html=True)
    with col_b2:
        st.markdown(f'<div style="text-align:right; padding-top:20px;"><span class="pill pill-red">⚠️ {refills_due} refills due</span></div>', unsafe_allow_html=True)

    due_now = [(m, t) for (m, t) in expected_today if t == current_slot and (m, t) not in taken_today]
    if due_now:
        med_list = ", ".join(sorted(set(m for m, t in due_now)))
        st.markdown(f"""
        <div style="background:#{TEAL_DARK}; color:#fff; padding:16px 20px; border-radius:12px; display:flex; gap:14px; align-items:center; margin:16px 0;">
            <div style="font-size:20px;">🔔</div>
            <div>
                <div style="font-weight:700; font-size:15px;">{len(due_now)} dose(s) due in the next hour</div>
                <div style="font-size:13px; opacity:0.85;">{med_list} {'are' if len(due_now) > 1 else 'is'} coming up</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.markdown(get_beep_audio_html(), unsafe_allow_html=True)

    col_main, col_side = st.columns([2.2, 1])

    with col_main:
        for time_slot in TIME_OPTIONS:
            meds = df[df["time_of_day"].apply(lambda x: time_slot in get_time_list(x))]
            if len(meds) > 0:
                st.markdown(f"#### 🗓️ {time_slot}")
                for _, row in meds.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**🔵 {row['medicine_name']}**")
                            st.caption(row["user_provided_instruction"])
                        with c2:
                            is_taken = (row["medicine_name"], time_slot) in taken_today
                            if time_slot == "As needed":
                                st.caption("No tracking needed")
                            elif is_taken:
                                st.markdown('<div style="text-align:right;"><span class="pill pill-teal">✓ Taken</span></div>', unsafe_allow_html=True)
                                if st.button("Undo", key=f"undo_{row['medicine_name']}_{time_slot}"):
                                    unmark_dose_taken(row["medicine_name"], time_slot, today_str)
                                    st.rerun()
                            else:
                                if st.button("Mark as Taken", key=f"take_{row['medicine_name']}_{time_slot}"):
                                    mark_dose_taken(row["medicine_name"], time_slot, today_str)
                                    st.rerun()

    with col_side:
        with st.container(border=True):
            st.markdown("**⚠️ Refill Warnings**")
            any_warning = False
            for _, row in df.iterrows():
                status, days_left = get_refill_status(row["refill_date"], today)
                if status != "ok":
                    any_warning = True
                    label = f"{abs(days_left)} days overdue" if days_left < 0 else f"due in {days_left} days"
                    color = "pill-red" if status == "overdue" else "pill-orange"
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin:8px 0;">
                        <span style="font-size:13.5px;">{row['medicine_name']}</span>
                        <span class="pill {color}" style="font-size:11px; padding:4px 10px;">{label}</span>
                    </div>""", unsafe_allow_html=True)
            if not any_warning:
                st.caption("No refills needed soon.")

        with st.container(border=True):
            st.markdown("**🔥 Adherence Streak**")
            st.markdown(f'<div style="font-size:42px; font-weight:700; color:#{TEAL_TEXT}; text-align:center;">{streak}</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; color:#6B7280; font-size:12.5px;">days in a row, all doses on time</div>', unsafe_allow_html=True)

# ============================================================
# PAGE 2 — EXPLAIN A LABEL
# ============================================================

elif page == "💬 Explain a Label":
    st.markdown('<div class="eyebrow">Label & Reference Explainer</div>', unsafe_allow_html=True)
    st.markdown("## Explain a Label")
    st.caption("Plain-language explanations — never a dosage or treatment decision.")

    col_left, col_right = st.columns([1, 1.1])

    medicine_names = df["medicine_name"].tolist()

    with col_left:
        with st.container(border=True):
            st.markdown("**MEDICINE**")
            selected_medicine = st.selectbox("Medicine", medicine_names, label_visibility="collapsed")
            selected_row = df[df["medicine_name"] == selected_medicine].iloc[0]
            st.markdown(f'*"{selected_row["user_provided_instruction"]}"*')

            if st.session_state.get("explain_medicine") != selected_medicine:
                st.session_state["explain_medicine"] = selected_medicine
                st.session_state.pop("explain_result", None)

            def run_explanation(question_text):
                with st.spinner("Thinking..."):
                    result = explain_label(
                        medicine_name=selected_row["medicine_name"],
                        instruction_text=selected_row["user_provided_instruction"],
                        user_question=question_text,
                        language=st.session_state["language"]
                    )
                st.session_state["explain_result"] = result
                save_to_memory(selected_row["medicine_name"], question_text if question_text else "General explanation", result)

            qc1, qc2 = st.columns(2)
            with qc1:
                if st.button("What does this mean?", use_container_width=True):
                    run_explanation(None)
            with qc2:
                if st.button("Side effects", use_container_width=True):
                    run_explanation("What are the common side effects?")
            qc3, qc4 = st.columns(2)
            with qc3:
                if st.button("Drug interactions", use_container_width=True):
                    run_explanation("What are common drug interactions with this medicine?")
            with qc4:
                if st.button("Food interactions", use_container_width=True):
                    run_explanation("Does this interact with any foods or drinks?")

            user_question = st.text_input("Or ask your own question", value="")

            st.markdown("&nbsp;", unsafe_allow_html=True)
            lc1, lc2, lc3 = st.columns(3)
            with lc1:
                if st.button(("✓ " if selected_language == "English" else "") + "English", use_container_width=True):
                    st.session_state["language"] = "English"
                    st.rerun()
            with lc2:
                if st.button(("✓ " if selected_language == "Hindi" else "") + "हिंदी", use_container_width=True):
                    st.session_state["language"] = "Hindi"
                    st.rerun()
            with lc3:
                if st.button(("✓ " if selected_language == "Gujarati" else "") + "ગુજરાતી", use_container_width=True):
                    st.session_state["language"] = "Gujarati"
                    st.rerun()

            if st.button("Explain this label", type="primary", use_container_width=True):
                run_explanation(user_question if user_question else None)

    with col_right:
        response_text = st.session_state.get("explain_result", "Ask a question on the left, and the explanation will appear here.")

        st.markdown(f"""
        <div style="background:#{TEAL_DARK}; color:#E6F4F1; padding:24px; border-radius:14px; min-height:340px;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
                <div style="width:32px; height:32px; border-radius:50%; background:#{TEAL}; display:flex; align-items:center; justify-content:center;">💬</div>
                <div style="font-weight:700; color:#fff;">Label Explainer</div>
            </div>
            <div style="font-size:14.5px; line-height:1.6;">{response_text}</div>
            <hr style="border-color:rgba(255,255,255,0.15); margin:20px 0 10px 0;">
            <div style="font-size:11px; opacity:0.7;">General reference information only — not personalized medical advice. Always confirm dosage or treatment changes with your doctor or pharmacist.</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🕘 Past questions about this medicine"):
        history = get_recent_memory(medicine_name=selected_medicine, limit=10)
        if len(history) > 0:
            for _, h in history.iterrows():
                st.markdown(f"**{h['timestamp']}** — *{h['question']}*")
                st.caption(h["answer"])
                st.divider()
        else:
            st.caption("No past questions yet for this medicine.")

# ============================================================
# PAGE 3 — MANAGE MEDICINES
# ============================================================

elif page == "🗂️ Manage Medicines":
    st.markdown('<div class="eyebrow">Medicine Database</div>', unsafe_allow_html=True)
    st.markdown("## Manage Your Medicines")

    search_term = st.text_input("🔍 Search by medicine name or doctor:", "")
    filtered_df = df.copy()
    if search_term:
        filtered_df = filtered_df[
            filtered_df["medicine_name"].str.contains(search_term, case=False, na=False) |
            filtered_df["doctor_pharmacist_contact"].str.contains(search_term, case=False, na=False)
        ]

    st.write(f"Showing {len(filtered_df)} of {len(df)} medicines")

    if st.button("🧾 Download Medicine Summary (PDF)"):
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "medicine_summary.pdf")
        generate_medicine_summary_pdf(df, pdf_path)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Click here to download PDF", data=f, file_name="medicine_summary.pdf", mime="application/pdf")

    st.dataframe(filtered_df[["medicine_name", "time_of_day", "refill_date", "doctor_pharmacist_contact"]],
                 use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### ✏️ Edit a Medicine")

    if len(filtered_df) > 0:
        edit_choice = st.selectbox("Select medicine to edit:", filtered_df["medicine_name"].tolist())
        row = df[df["medicine_name"] == edit_choice].iloc[0]
        current_times = [t for t in get_time_list(row["time_of_day"]) if t in TIME_OPTIONS]

        with st.form("edit_form"):
            new_instruction = st.text_input("Label instruction", value=row["user_provided_instruction"])
            new_times = st.multiselect("Time(s) of day", TIME_OPTIONS, default=current_times)
            new_start = st.text_input("Start date (YYYY-MM-DD)", value=str(row["start_date"]))
            new_refill = st.text_input("Refill date (YYYY-MM-DD)", value=str(row["refill_date"]))
            new_notes = st.text_input("Notes", value=row["notes"])
            new_doctor = st.text_input("Doctor/Pharmacist contact", value=row["doctor_pharmacist_contact"])
            col1, col2 = st.columns(2)
            with col1:
                save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)
            with col2:
                delete_clicked = st.form_submit_button("🗑️ Delete This Medicine", use_container_width=True)

        if save_clicked:
            if len(new_times) == 0:
                st.error("Please select at least one time of day.")
            else:
                update_medicine(edit_choice, {"instruction": new_instruction, "time_of_day": ", ".join(new_times),
                                               "start_date": new_start, "refill_date": new_refill,
                                               "notes": new_notes, "doctor_contact": new_doctor})
                st.success(f"✅ {edit_choice} updated successfully!")
                st.rerun()
        if delete_clicked:
            delete_medicine(edit_choice)
            st.success(f"🗑️ {edit_choice} deleted.")
            st.rerun()
    else:
        st.info("No medicines match your search.")

    st.divider()
    st.markdown("#### ➕ Add a New Medicine")
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("Medicine name")
        add_instruction = st.text_input("Label instruction")
        add_times = st.multiselect("Time(s) of day", TIME_OPTIONS)
        add_start = st.text_input("Start date (YYYY-MM-DD)", value=str(datetime.now().date()))
        add_refill = st.text_input("Refill date (YYYY-MM-DD)")
        add_notes = st.text_input("Notes (optional)")
        add_doctor = st.text_input("Doctor/Pharmacist contact")
        add_clicked = st.form_submit_button("➕ Add Medicine", use_container_width=True)

    if add_clicked:
        if new_name and add_refill and len(add_times) > 0:
            add_medicine({"medicine_name": new_name, "instruction": add_instruction, "time_of_day": ", ".join(add_times),
                          "start_date": add_start, "refill_date": add_refill, "notes": add_notes, "doctor_contact": add_doctor})
            st.success(f"✅ {new_name} added successfully!")
            st.rerun()
        else:
            st.error("Please fill in Medicine name, Refill date, and at least one time of day.")

# ============================================================
# PAGE 4 — SCAN PRESCRIPTION  (mandatory verification checkbox)
# ============================================================

elif page == "📷 Scan Prescription":
    st.markdown('<div class="eyebrow">Vision-Based Prescription Reader</div>', unsafe_allow_html=True)
    st.markdown("## Scan Prescription")
    st.caption("Reads a medicine strip or prescription photo — human review required before saving. Can detect multiple medicines in one photo.")

    col_left, col_right = st.columns([1, 1.1])

    with col_left:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding:20px 0;'>☁️<br><b>Upload a photo of the medicine strip or prescription</b><br><span style='color:#6B7280; font-size:12.5px;'>JPEG or PNG, up to 10MB</span></div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
            if uploaded_file is not None:
                st.image(uploaded_file, use_container_width=True)
                read_clicked = st.button("🔍 Read & Explain This Image", use_container_width=True, type="primary")
            else:
                read_clicked = False

    with col_right:
        if uploaded_file is None:
            st.markdown(f"""
            <div style="background:#{LIGHTGRAY}; border-radius:14px; min-height:340px; display:flex; align-items:center; justify-content:center; color:#{GRAY};">
                Upload a photo to see the AI reading here.
            </div>""", unsafe_allow_html=True)
        else:
            if read_clicked:
                with st.spinner("Reading image carefully..."):
                    image_bytes = uploaded_file.getvalue()
                    st.session_state["scan_image_bytes"] = image_bytes
                    mime_type = uploaded_file.type
                    result = read_medicine_image(image_bytes, mime_type, language=st.session_state["language"])
                    st.session_state["scan_result"] = result
                    st.session_state["scan_added_indices"] = set()

            if "scan_result" in st.session_state:
                result = st.session_state["scan_result"]
                if not result.get("is_readable", False):
                    st.warning("⚠️ This image wasn't clearly readable. Try a clearer, well-lit photo, or enter details manually in 'Manage Medicines'.")
                    st.caption(f"Note: {result.get('confidence_note', '')}")
                else:
                    with st.container(border=True):
                        num_meds = len(result.get("medicines", []))
                        st.success(f"✅ Image read successfully — found {num_meds} medicine(s)")
                        st.markdown("**Overview**")
                        st.write(result.get("simple_explanation", ""))
                        st.caption(f"🔎 {result.get('confidence_note', '')}")

    if "scan_result" in st.session_state and st.session_state["scan_result"].get("is_readable", False):
        result = st.session_state["scan_result"]
        medicines_found = result.get("medicines", [])
        doctor_found = result.get("doctor_name_found", "")

        st.divider()
        st.markdown("#### ✏️ Review Each Medicine Before Adding")

        if len(medicines_found) == 0:
            st.warning("No individual medicines could be clearly identified in this image.")

        for idx, med in enumerate(medicines_found):
            already_added = idx in st.session_state["scan_added_indices"]

            with st.container(border=True):
                header_col1, header_col2 = st.columns([4, 1])
                with header_col1:
                    st.markdown(f"**Medicine {idx + 1}: {med.get('medicine_name', 'Unclear')}**")
                with header_col2:
                    if already_added:
                        st.markdown('<span class="pill pill-teal">✓ Added</span>', unsafe_allow_html=True)

                if not already_added:
                    st.markdown(f"""
                    <div style="background:#FDEAEA; border: 1.5px solid #{RED}; border-radius:8px; padding:12px 14px; margin-bottom:10px; font-size:13px; color:#7A1518;">
                    🚨 <b>Dosage accuracy cannot be guaranteed by AI.</b> You MUST compare every field below against the original photo before saving — this matters especially for controlled or psychiatric medications.
                    </div>""", unsafe_allow_html=True)

                    zoom_col, form_col = st.columns([1, 1.4])

                    with zoom_col:
                        st.markdown("**📷 Original photo (check against this):**")
                        if "scan_image_bytes" in st.session_state:
                            st.image(st.session_state["scan_image_bytes"], use_container_width=True)

                    with form_col:
                        st.caption(f"🔎 AI read — Dosage: **{med.get('dosage_pattern', 'unclear')}**  |  Duration: **{med.get('frequency_duration', 'not specified')}**  |  Timing: **{med.get('timing_instruction', 'not specified')}**  |  Notes: **{med.get('notes', '')}**")

                        default_instruction = " | ".join(filter(None, [
                            f"Dosage: {med.get('dosage_pattern', '')}" if med.get('dosage_pattern') else "",
                            f"Timing: {med.get('timing_instruction', '')}" if med.get('timing_instruction') else "",
                            f"Duration: {med.get('frequency_duration', '')}" if med.get('frequency_duration') else "",
                            f"Notes: {med.get('notes', '')}" if med.get('notes') else "",
                        ]))

                        with st.form(f"scan_add_form_{idx}"):
                            scan_name = st.text_input("Medicine name", value=med.get("medicine_name", ""), key=f"name_{idx}")
                            scan_instruction = st.text_input("Instructions found (edit if anything looks wrong)", value=default_instruction, key=f"instr_{idx}")
                            scan_times = st.multiselect("Time(s) of day", TIME_OPTIONS, key=f"times_{idx}")
                            scan_start = st.text_input("Start date (YYYY-MM-DD)", value=str(datetime.now().date()), key=f"start_{idx}")
                            scan_refill = st.text_input("Refill date (YYYY-MM-DD)", value="", key=f"refill_{idx}")
                            scan_notes = st.text_input("Notes (optional)", value="", key=f"notes_{idx}")
                            scan_doctor = st.text_input("Doctor/Pharmacist contact", value=doctor_found, key=f"doctor_{idx}")

                            verified = st.checkbox("✅ I have compared this dosage to the original photo, digit by digit, and confirm it is correct", key=f"verify_{idx}")

                            confirm_add = st.form_submit_button("➕ Add This Medicine to My List", use_container_width=True)

                        if confirm_add:
                            if not verified:
                                st.error("🚫 Please tick the verification checkbox first — this confirms you checked the dosage yourself before saving.")
                            elif scan_name and scan_refill and len(scan_times) > 0:
                                add_medicine({
                                    "medicine_name": scan_name, "instruction": scan_instruction,
                                    "time_of_day": ", ".join(scan_times), "start_date": scan_start,
                                    "refill_date": scan_refill, "notes": scan_notes, "doctor_contact": scan_doctor
                                })
                                st.session_state["scan_added_indices"].add(idx)
                                st.success(f"✅ {scan_name} added to your medicine list!")
                                st.rerun()
                            else:
                                st.error("Please fill in Medicine name, Refill date, and at least one time of day.")

        if len(medicines_found) > 0 and len(st.session_state["scan_added_indices"]) == len(medicines_found):
            st.success("🎉 All medicines from this scan have been added to your list!")
            if st.button("Scan Another Prescription"):
                del st.session_state["scan_result"]
                st.session_state["scan_added_indices"] = set()
                st.session_state.pop("scan_image_bytes", None)
                st.rerun()

# ============================================================
# PAGE 5 — ADHERENCE REPORT
# ============================================================

elif page == "📊 Adherence Report":
    st.markdown('<div class="eyebrow">Weekly Summary</div>', unsafe_allow_html=True)
    st.markdown("## Adherence Report")
    st.caption("Last 7 days of Mark-as-Taken activity.")

    report_df = get_weekly_adherence_data(df)
    avg_adherence = round(report_df["Adherence %"].mean()) if len(report_df) > 0 else 0
    total_taken = int(report_df["Taken"].sum())
    streak = calculate_streak(df)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        with st.container(border=True):
            st.markdown("**Doses taken on time, per day**")
            st.bar_chart(report_df.set_index("Date")["Adherence %"], color=f"#{TEAL}")

    with col_right:
        with st.container(border=True):
            st.markdown(f'<div style="font-size:38px; font-weight:700; color:#{TEAL_TEXT}; text-align:center;">{avg_adherence}%</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; color:#6B7280; font-size:12.5px;">Adherence this week</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown(f'<div style="font-size:28px; font-weight:700; text-align:center;">{streak}</div><div style="text-align:center; color:#6B7280; font-size:11.5px;">Day streak</div>', unsafe_allow_html=True)
        with c2:
            with st.container(border=True):
                st.markdown(f'<div style="font-size:28px; font-weight:700; text-align:center;">{total_taken}</div><div style="text-align:center; color:#6B7280; font-size:11.5px;">Doses logged</div>', unsafe_allow_html=True)

# ============================================================
# PAGE 6 — CAREGIVER VIEW
# ============================================================

elif page == "👥 Caregiver View":
    if not st.session_state["caregiver_unlocked"]:
        st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1, 1.2, 1])
        with col_b:
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align:center; padding:10px 0 6px 0;">
                    <div style="width:56px; height:56px; border-radius:50%; background:#{TEAL}; display:inline-flex; align-items:center; justify-content:center; font-size:24px;">🔒</div>
                    <h3 style="margin-top:14px;">Caregiver View</h3>
                    <div style="color:#6B7280; font-size:13px; margin-bottom:16px;">Enter the caregiver PIN for read-only access</div>
                </div>""", unsafe_allow_html=True)
                entered_pin = st.text_input("PIN", type="password", max_chars=4, label_visibility="collapsed")
                if st.button("Unlock", use_container_width=True, type="primary"):
                    if entered_pin == CAREGIVER_PIN:
                        st.session_state["caregiver_unlocked"] = True
                        st.rerun()
                    else:
                        st.error("Incorrect PIN.")
        st.stop()

    if len(df) == 0:
        st.info("No medicines have been added yet.")
        st.stop()

    st.markdown(f'<span class="pill pill-teal">👥 Caregiver View</span> &nbsp; <span class="pill" style="background:#E9F5EE; color:#1E7A46;">READ-ONLY</span>', unsafe_allow_html=True)
    st.markdown(f"## {USER_NAME}'s Adherence Today")
    st.caption("No edit controls are exposed in this view.")

    taken_today_df = get_taken_doses(today_str)
    expected_today = get_expected_doses(df)
    taken_today_set = set(zip(taken_today_df["medicine_name"], taken_today_df["time_slot"])) if len(taken_today_df) > 0 else set()
    streak = calculate_streak(df)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        with st.container(border=True):
            st.markdown("**🔥 Today's Status**")
            for time_slot in TIME_OPTIONS:
                meds = df[df["time_of_day"].apply(lambda x: time_slot in get_time_list(x))]
                for _, row in meds.iterrows():
                    if time_slot == "As needed":
                        continue
                    is_taken = (row["medicine_name"], time_slot) in taken_today_set
                    if is_taken:
                        taken_time = taken_today_df[
                            (taken_today_df["medicine_name"] == row["medicine_name"]) &
                            (taken_today_df["time_slot"] == time_slot)]["taken_at"].values[0]
                        badge = f'<span class="pill pill-teal" style="font-size:11px; padding:4px 10px;">Taken {taken_time.split(" ")[-1]}</span>'
                    else:
                        badge = '<span class="pill pill-orange" style="font-size:11px; padding:4px 10px;">Pending</span>'
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin:10px 0;">
                        <span>{row['medicine_name']}</span>{badge}
                    </div>""", unsafe_allow_html=True)

    with col_right:
        with st.container(border=True):
            st.markdown("**⚠️ Refill Warnings**")
            any_warning = False
            for _, row in df.iterrows():
                status, days_left = get_refill_status(row["refill_date"], today)
                if status != "ok":
                    any_warning = True
                    label = f"{abs(days_left)} days overdue" if days_left < 0 else f"due in {days_left} days"
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; margin:8px 0; font-size:13px;">
                        <span>{row['medicine_name']}</span><span class="pill pill-red" style="font-size:11px; padding:4px 10px;">{label}</span>
                    </div>""", unsafe_allow_html=True)
            if not any_warning:
                st.caption("No refills needed soon.")

        with st.container(border=True):
            st.markdown("**🔥 Streak**")
            st.markdown(f'<div style="font-size:38px; font-weight:700; text-align:center;">{streak}</div><div style="text-align:center; color:#6B7280; font-size:12px;">days in a row</div>', unsafe_allow_html=True)

    if st.button("🔒 Lock Caregiver View"):
        st.session_state["caregiver_unlocked"] = False
        st.rerun()

# ============================================================
# PAGE 7 — LIMITATIONS & RESPONSIBLE USE
# ============================================================

elif page == "ℹ️ Limitations & Responsible Use":
    st.markdown('<div class="eyebrow">Responsible By Design</div>', unsafe_allow_html=True)
    st.markdown("## Limitations & Responsible Use")

    st.markdown("""
### What this app is
A **personal organization tool** that helps you keep track of medicine schedules, understand label instructions in simple language, and remember to take your doses on time.

### What this app is NOT
- ❌ Not a medical device, not approved or reviewed by any medical authority
- ❌ Does not diagnose any condition, illness, or disease
- ❌ Does not recommend dosages or treatment changes
- ❌ Not a substitute for a licensed doctor or pharmacist

### Known limitations
- 📷 **Photo scanning accuracy**: Testing with real prescriptions (including psychiatric/controlled medications) confirmed that AI vision reading can occasionally misread dosage digits, especially in tightly-packed tables. Because of this, a **mandatory verification checkbox** blocks saving any scanned medicine until the user explicitly confirms they checked it against the original photo, digit by digit.
- 🌐 AI explanations are general reference information, not personalized medical guidance
- 💾 Data is stored locally, not currently synced or encrypted for cloud storage
- 🔔 Reminders only work while the app is open in a browser tab

### Responsible use guidelines
1. Always confirm details with your doctor or pharmacist
2. Do not rely on this app as your only source of medical information
3. In an emergency, contact emergency services immediately — do not use this app
4. Review your medicine list periodically with your doctor

### Future roadmap
- 📱 Native mobile app with real push notifications
- 🎙️ Voice input for accessibility
- 🔐 Cloud sync with encrypted storage

---
*Built by PRASHANTKUMAR JOGIYA FOUNDER OF PRAAG BIOSCIENCE PVT LTD — IIT Mandi, Himshikhar 2026 Agentic AI Programme.*
""")