from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UNSAFE_KEYWORDS = [
    "should i take", "how much should i", "is it safe for me",
    "can i take with", "can i mix", "what dose", "increase dose",
    "decrease dose", "stop taking", "is it okay to skip",
    "diagnose", "what disease", "what's wrong with me",
    "can i stop", "should i stop", "is it safe to"
]

LANGUAGE_NAMES = {
    "English": "English",
    "Hindi": "Hindi (Devanagari script)",
    "Gujarati": "Gujarati script"
}

def is_medical_advice_request(question: str) -> bool:
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in UNSAFE_KEYWORDS)

def get_refusal_message(language: str) -> str:
    """Generates the refusal message in the requested language using the AI itself."""
    lang_instruction = LANGUAGE_NAMES.get(language, "English")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Respond only in {lang_instruction}. Keep it short, 2-3 sentences."},
            {"role": "user", "content": "Write a short, polite message saying: I cannot make personalized medical decisions like changing, stopping, combining, or adjusting a medicine dose. Please contact your doctor or pharmacist. I can share general reference information about side effects or interactions if asked."}
        ],
        temperature=0.2,
        max_tokens=150
    )
    return "⚠️ " + response.choices[0].message.content

def explain_label(medicine_name: str, instruction_text: str, user_question: str = None, language: str = "English"):
    """
    Explains label instructions AND provides general reference information on
    side effects, drug interactions, and food interactions - as EDUCATIONAL
    information only. Responds in the requested language.
    """

    question_to_check = user_question if user_question else instruction_text
    if is_medical_advice_request(question_to_check):
        return get_refusal_message(language)

    lang_instruction = LANGUAGE_NAMES.get(language, "English")

    system_prompt = f"""You are a Medicine Label & Reference Information assistant. 
Your job is to explain label instructions AND share general reference information 
about side effects, drug interactions, and food interactions.

IMPORTANT: Respond ONLY in {lang_instruction}. The entire response must be in {lang_instruction}, 
written simply so an everyday person (not a doctor) can understand it.

STRICT RULES YOU MUST FOLLOW:
- You may explain general, commonly-known side effects, drug interactions, and 
  food interactions for the named medicine, framed as "commonly reported" or 
  "generally known" information - never as a certainty for this specific person.
- NEVER tell the user what TO DO with this information (e.g. never say "you should 
  stop," "it's safe for you," "you can skip this," "take instead").
- NEVER recommend a dosage, timing change, or treatment decision.
- NEVER confirm whether something is personally "safe" or "unsafe" for the user.
- ALWAYS end any side-effect/interaction answer with a short reminder to confirm 
  with their doctor or pharmacist before acting on it (translated into {lang_instruction}).
- If asked to diagnose, prescribe, or make any personal decision, respond (in {lang_instruction}):
  "I can't provide medical advice - please consult your doctor or pharmacist for this."
- Keep answers short, simple, and in everyday language (avoid heavy medical jargon).
"""

    user_prompt = f"""Medicine: {medicine_name}
Label instruction: "{instruction_text}"

{f'User question: {user_question}' if user_question else 'Please explain this instruction in simple terms.'}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=350
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print("TEST: Hindi explanation")
    print("-" * 50)
    print(explain_label("Metformin 500mg", "Take after meals twice daily",
                         "What are the common side effects?", language="Hindi"))