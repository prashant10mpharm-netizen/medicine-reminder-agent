from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LANGUAGE_NAMES = {
    "English": "English",
    "Hindi": "Hindi (Devanagari script)",
    "Gujarati": "Gujarati script"
}

def _transcribe_table(base64_image, mime_type):
    """
    STEP 1: Ask the AI to just transcribe the prescription/label as plain text,
    row by row, with no formatting pressure. This improves reading accuracy,
    similar to how professional OCR pipelines separate 'reading' from 'organizing'.
    """
    data_url = f"data:{mime_type};base64,{base64_image}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful transcription assistant. Transcribe ALL visible text "
                    "from this medicine label or prescription image EXACTLY as printed, "
                    "preserving the table structure. For any dosage pattern written as numbers "
                    "separated by dashes (e.g. 1-0-0), read each digit very carefully, one at a "
                    "time, left to right - do not let digits from other rows influence your reading. "
                    "If a digit is even slightly unclear, write [unclear] instead of guessing. "
                    "Go row by row, medicine by medicine. Do not summarize or skip anything."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this image exactly, row by row."},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
                ]
            }
        ],
        temperature=0.0,
        max_tokens=1200
    )
    return response.choices[0].message.content


def read_medicine_image(image_bytes, mime_type="image/jpeg", language="English"):
    """
    Reads a photo of a medicine strip, box, or prescription using a two-step process:
    1. Careful plain-text transcription (forces high-detail image reading)
    2. Structuring that transcription into per-medicine fields
    This two-step approach reduces (but cannot fully eliminate) digit misreads -
    the user must always review before saving.
    """

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    lang_instruction = LANGUAGE_NAMES.get(language, "English")

    # ----- Step 1: careful transcription -----
    transcription = _transcribe_table(base64_image, mime_type)

    # ----- Step 2: structure the transcription into fields -----
    system_prompt = f"""You are given a plain-text transcription of a medicine label or
prescription (already carefully read from a photo). Your job is now ONLY to organize
this text into structured fields - do NOT re-interpret or change any numbers, just
reformat what is already given to you.

For each medicine mentioned, extract: name, dosage pattern, frequency/duration, timing,
and notes - as SEPARATE fields, copied exactly from the transcription. If the
transcription marked something as [unclear], keep it as "unclear" in that field -
never invent a number to replace it.

Write "simple_explanation" and "confidence_note" ONLY in {lang_instruction}.
Keep medicine names/dosages in their original language/script - do not translate these.

STRICT RULES:
- NEVER recommend a dosage, timing change, or treatment decision.
- NEVER confirm if something is "safe" for the person.
- Always remind the user to verify with their pharmacist, especially anything unclear.

Respond ONLY in this exact JSON format, nothing else:
{{
  "is_readable": true or false,
  "doctor_name_found": "doctor name if visible, or 'not visible'",
  "simple_explanation": "a short, friendly overall explanation in {lang_instruction}",
  "confidence_note": "a short honest note in {lang_instruction} about clarity, mentioning if any fields were unclear",
  "medicines": [
    {{
      "medicine_name": "exact name, or 'unclear'",
      "dosage_pattern": "exact dosage pattern (e.g. '1-0-0'), or 'unclear'",
      "frequency_duration": "exact frequency/duration, or 'not specified'",
      "timing_instruction": "exact timing, or 'not specified'",
      "notes": "exact notes, or ''"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the transcription to organize:\n\n{transcription}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=1000
    )

    result = json.loads(response.choices[0].message.content)

    if "medicines" not in result or not isinstance(result["medicines"], list):
        result["medicines"] = []

    return result