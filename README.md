# 💊 Medicine Box Reminder and Label Explainer Agent

An AI-powered personal health organization assistant that stores your medicine schedule, explains confusing label instructions in plain language, tracks adherence, and reminds you about refills — while never recommending dosages or making medical decisions.

**Built by:** Prashant | AIXCEL
**Programme:** IIT Mandi — Himshikhar 2026, Agentic AI (Track: AAI)

---

## 📋 Problem Statement

Many people, especially elderly individuals managing multiple prescriptions, struggle to keep track of medicine schedules and misunderstand label instructions (e.g. "take on an empty stomach"). This agent solves that by storing a user's medicine data, explaining labels simply, tracking doses taken, and warning about refills — without ever crossing into medical advice, diagnosis, or treatment decisions.

## 📊 Dataset / Reference Source

A starter dataset of 30 realistic medicine records was manually created following the schema: `medicine_name, user_provided_instruction, time_of_day, start_date, refill_date, notes, doctor_pharmacist_contact`. This is loaded into a local SQLite database and is fully editable through the app.

## 🛠️ Tools Used

- **Python** — core application logic
- **Streamlit** — interactive web UI
- **SQLite** — editable local database (medicines, dose logs, conversation memory)
- **OpenAI GPT-4o-mini** (text + vision) — label explanation, side-effect/interaction reference info, prescription image reading, multilingual output
- **fpdf2** — PDF summary generation
- **python-dotenv** — secure API key management

## 🔄 Project Workflow

1. User views schedule / asks a question / uploads a photo / edits medicines
2. Request routed to the correct backend function
3. Keyword-based guardrail check screens for unsafe personalized requests
4. Relevant data pulled from SQLite (medicines, history, memory)
5. GPT-4o-mini generates a plain-language response under a strict system prompt
6. AI-level guardrails independently re-check scope
7. Result displayed in the UI and logged for memory/adherence tracking

## 🤖 AI / Agent Components

- **Label & Reference Explainer** — explains instructions, side effects, drug/food interactions in plain language
- **Layered Guardrails** — keyword pre-filter + AI system-prompt enforcement, refusing personalized dosage/treatment decisions
- **Vision-based Prescription Reader** — reads photos of medicine strips/prescriptions, flags unreadable images honestly, requires human review before saving
- **Conversation Memory** — logs every explanation given, with history shown per medicine
- **Adherence Tracking** — "Mark as Taken" logging, streaks, 7-day adherence report
- **Multilingual Support** — explanations in English, Hindi, or Gujarati

## ✨ Features

- Editable medicine database (add/edit/delete, search/filter)
- Daily schedule grouped by time of day (supports multiple doses/day)
- Refill warnings (overdue + upcoming)
- AI label explanation with quick-select buttons (meaning, side effects, drug/food interactions)
- Photo/prescription scanning with review-before-save safety
- Mark-as-Taken tracking, adherence streak, due-now banner + audio reminder
- Weekly adherence report with chart
- PDF export of medicine summary
- Caregiver View (separate PIN-protected, read-only dashboard)
- Multi-language explanations (English/Hindi/Gujarati)
- AIXCEL-branded UI design
- Dedicated Limitations & Responsible Use page

## ▶️ How to Run

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd medicine_box_agent

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file in the root folder with:
OPENAI_API_KEY=your_openai_api_key_here
CAREGIVER_PIN=5678

# 5. Initialize the database
python src/setup_database.py

# 6. Run the app
streamlit run app/app.py
```

The app will open at `http://localhost:8501`.

## 📸 Demo Screenshots

*(Add screenshots of Today's Schedule, Explain a Label, Scan Prescription, Adherence Report, and Caregiver View here before submission.)*

## 📈 Results and Insights

The agent successfully demonstrates a complete Agentic AI workflow — task understanding, tool use (database, PDF export, vision model), memory, and layered safety guardrails — validated through manual scenario testing covering guardrail refusals, refill logic, multi-dose scheduling, image reading, and multilingual output.

## ⚠️ Limitations

- Not a certified medical device; not reviewed by any medical authority
- AI-generated side-effect/interaction info is general reference material, not personalized advice
- Photo-based reading can misread unclear images — all scanned entries require user review
- Reminders only work while the app is open in a browser tab (no native background alarms)
- Local, unencrypted data storage in the current version

See the in-app **"Limitations & Responsible Use"** page for full details.

## 🚀 Future Improvements

- Native mobile app with real push notifications
- Voice input for accessibility
- Cloud sync with encrypted storage
- Expanded multi-patient/family account system
- Pharmacy integration for automated refill ordering

## 👤 Team

Prashant — Solo contributor (IIT Mandi, Himshikhar 2026, Agentic AI Programme). Founder, AIXCEL.