import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

TRIAGE_PROMPT = """You are a medical triage AI for a rural healthcare system in India.
Given the following patient information, assess the urgency and return a JSON response.

Patient Name: {name}
Age: {age}
Village: {village}
Symptoms: {symptoms}

You MUST return ONLY a valid JSON object with exactly these fields:
{{
  "priority": "RED" or "YELLOW" or "GREEN",
  "summary": "brief medical assessment in 1-2 sentences"
}}

Priority meanings:
- RED: Life-threatening emergency requiring immediate attention (e.g., chest pain, breathing difficulty, severe bleeding, unconsciousness)
- YELLOW: Moderate condition requiring attention within hours (e.g., high fever, persistent pain, infection signs)
- GREEN: Mild condition that can wait (e.g., common cold, mild headache, minor rash)

Return ONLY the JSON object, no other text."""


def triage_patient(name, age, village, symptoms):
    """Send symptoms to Groq LLM and return priority + summary."""
    try:
        prompt = TRIAGE_PROMPT.format(
            name=name,
            age=age,
            village=village,
            symptoms=symptoms
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_completion_tokens=200
        )

        text = response.choices[0].message.content.strip()
        # Clean potential markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        result = json.loads(text)

        priority = result.get("priority", "YELLOW").upper()
        if priority not in ("RED", "YELLOW", "GREEN"):
            priority = "YELLOW"

        print(f"[Groq] Triage: {priority} for {name}")
        return {
            "priority": priority,
            "summary": result.get("summary", "AI assessment unavailable")
        }

    except Exception as e:
        print(f"[Groq Error] {e}")
        return {
            "priority": "YELLOW",
            "summary": "AI triage unavailable — defaulting to moderate priority"
        }
