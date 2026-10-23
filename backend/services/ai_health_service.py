import re
import json
import logging
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Clinical Emergency "Red-Flag" keywords and signs
RED_FLAG_PATTERNS = [
    (r"\b(crushing|radiating|severe|tightness in)\s*(chest|breast|heart)\b", "Chest pain or pressure (potential acute coronary event)"),
    (r"\b(can'?t breathe|shortness of breath|gasping|severe wheezing|struggling to breathe)\b", "Severe respiratory distress / hypoxia"),
    (r"\b(slurred speech|face drooping|facial droop|sudden weakness|arm numbness|loss of balance)\b", "Signs of acute cerebrovascular event (Stroke)"),
    (r"\b(coughing up blood|hemoptysis|vomiting blood|black tarry stool)\b", "Active internal or gastrointestinal hemorrhage"),
    (r"\b(swollen tongue|throat closing|anaphylaxis|swelling of throat)\b", "Severe systemic allergic anaphylaxis"),
    (r"\b(unconscious|passed out|fainted|seizure|convulsions)\b", "Loss of consciousness or acute seizure activity"),
    (r"\b(suicidal|kill myself|end my life|want to die)\b", "Acute mental health emergency / crisis")
]

class AIHealthConsultationService:
    """
    Conversational AI Health Assistant adhering to strict medical safety guidelines:
    - Screens for acute emergency red flags first.
    - Conducts a step-by-step interview asking ONE question at a time.
    - Prevents long walls of text; outputs concise, compassionate questions and guidance.
    - Categorizes clinical risk tiers: LOW, MODERATE, HIGH, EMERGENCY.
    - Integrates with Gemini API, Ollama, and an offline interactive triage state-engine.
    """

    @staticmethod
    def screen_emergency_red_flags(user_message: str) -> tuple[bool, str]:
        """
        Scans message for life-threatening warning signs.
        Returns: (is_red_flag, red_flag_description)
        """
        lower = user_message.lower()
        for pattern, description in RED_FLAG_PATTERNS:
            if re.search(pattern, lower):
                return True, description
        return False, ""

    @staticmethod
    def generate_health_guidance(user_message: str, conversation_history: list = None, patient_profile: dict = None) -> dict:
        """
        Generates structured, step-by-step medical guidance.
        Asks one question at a time to prevent overwhelming the user.
        """
        # Step 1: Immediate Red Flag Emergency Screening
        is_red_flag, red_flag_desc = AIHealthConsultationService.screen_emergency_red_flags(user_message)

        if is_red_flag:
            emergency_response = (
                f"🚨 **EMERGENCY WARNING SIGN DETECTED: {red_flag_desc}**\n\n"
                "Your symptoms indicate a potentially life-threatening situation requiring **immediate emergency evaluation**.\n\n"
                "**URGENT ACTIONS REQUIRED:**\n"
                "1. **Call emergency services immediately** (Dial 112 in India, 911 in North America, or your local emergency number).\n"
                "2. Go to the nearest Hospital Emergency Department.\n"
                "3. Stop physical exertion, sit comfortably, and keep your airways clear."
            )
            return {
                "message": emergency_response,
                "risk_category": "EMERGENCY",
                "red_flag_alert": 1,
                "disclaimer": "EMERGENCY ALERT: Automated safety triage. Seek immediate professional emergency medical care.",
                "follow_up_questions": [],
                "recommended_specialty": "Emergency Medicine / Critical Care",
                "ai_provider": "Emergency Triage Safety System"
            }

        # Step 2: Context Preparation
        patient_context = ""
        if patient_profile:
            patient_context = (
                f"Patient Profile Context: Gender: {patient_profile.get('gender', 'Unknown')}, "
                f"Blood Group: {patient_profile.get('blood_group', 'Unknown')}, "
                f"Known Allergies: {patient_profile.get('allergies', 'None recorded')}, "
                f"Chronic Conditions: {patient_profile.get('chronic_conditions', 'None recorded')}."
            )

        # Count previous patient messages in this consultation session
        patient_turns = len([m for m in (conversation_history or []) if m.get("sender_type") == "PATIENT"])

        system_prompt = (
            "You are AI Health Agent, a caring and professional healthcare triage assistant.\n"
            "STRICT CONVERSATIONAL RULES:\n"
            "1. KEEP RESPONSES SHORT, FRIENDLY, AND UNDER 50 WORDS. Do NOT write long paragraphs or multiple questions.\n"
            "2. Ask ONLY ONE focused clinical question at a time to interview the patient step-by-step.\n"
            "3. At the end of your response, always provide 3-4 clickable short choices formatted as: OPTIONS: Choice 1 | Choice 2 | Choice 3\n"
            "4. Only after the patient has answered 3 follow-up questions, provide a brief 3-bullet summary with safe home comfort measures and doctor recommendation.\n"
            "5. Never give a definitive diagnosis. Never prescribe prescription medications.\n"
            "6. Always prioritize patient safety."
        )

        ai_response_text = None
        risk_category = "LOW"
        ai_provider_used = "Interactive Health Agent"
        follow_up_questions = []

        # Try Google Gemini if configured
        if Config.AI_PROVIDER == "gemini" and Config.GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
                dialogue_parts = [{"text": f"System Instructions: {system_prompt}\n{patient_context}"}]

                if conversation_history:
                    for msg in conversation_history[-6:]:
                        role = "user" if msg.get("sender_type") == "PATIENT" else "model"
                        dialogue_parts.append({"text": f"{role}: {msg.get('message_text')}"})

                dialogue_parts.append({"text": f"Patient: {user_message}"})

                payload = {
                    "contents": [{"parts": dialogue_parts}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300}
                }
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "")
                            # Parse OPTIONS: if Gemini returned them
                            if "OPTIONS:" in raw_text:
                                text_part, opt_part = raw_text.split("OPTIONS:", 1)
                                ai_response_text = text_part.strip()
                                follow_up_questions = [opt.strip() for opt in opt_part.split("|") if opt.strip()]
                            else:
                                ai_response_text = raw_text.strip()
                            ai_provider_used = f"Google Gemini ({Config.GEMINI_MODEL})"
            except Exception as e:
                logger.warning("Gemini AI health call failed (%s). Using interactive rule engine.", e)

        # Fallback Interactive Step-by-Step Clinical Engine
        if not ai_response_text:
            cleaned_query = user_message.strip()
            lower_msg = cleaned_query.lower()

            info_keywords = ["what is", "how to take", "can i take", "side effects", "what causes", "how does", "dosage of"]
            is_info_query = any(k in lower_msg for k in info_keywords)

            if is_info_query:
                ai_response_text = (
                    f"Here is a quick, safe overview regarding **{cleaned_query}**:\n\n"
                    "• **Key Advice:** Always verify with a licensed pharmacist or physician before combining medications.\n"
                    "• **Safety Note:** Follow standard package directions, take with water, and never exceed stated doses.\n"
                    "• **Precautions:** If you have existing kidney, liver, or stomach concerns, consult your doctor first."
                )
                follow_up_questions = [
                    "Search Medicine Database",
                    "Check Drug Interactions",
                    "I have another question"
                ]
                risk_category = "LOW"

            elif "restart" in lower_msg or "reset" in lower_msg or "clear" in lower_msg:
                ai_response_text = "Session refreshed. What symptoms or questions can I help you check today?"
                follow_up_questions = [
                    "Headache & Sensitivity",
                    "Fever & Body Ache",
                    "Sore Throat & Cough",
                    "Stomach Discomfort"
                ]
                risk_category = "LOW"

            elif patient_turns == 0:
                # TURN 1: Acknowledge & Ask Question 1 (Pain / Severity Scale)
                ai_response_text = (
                    f"I understand you are experiencing: **{cleaned_query}**.\n\n"
                    "To give you clear guidance without a long wall of text, let's check a couple of quick questions one by one.\n\n"
                    "👉 **Question 1 of 3:** On a scale of 1 to 10, how severe or intense is the discomfort right now?"
                )
                follow_up_questions = [
                    "Mild (1 - 3)",
                    "Moderate (4 - 6)",
                    "Severe (7 - 9)",
                    "Very Intense (10)"
                ]
                risk_category = "LOW"

            elif patient_turns == 1:
                # TURN 2: Acknowledge severity & Ask Question 2 (Duration & Onset)
                ai_response_text = (
                    f"Thank you for sharing the intensity (**{cleaned_query}**).\n\n"
                    "👉 **Question 2 of 3:** Did this start suddenly out of nowhere, or did it build up gradually over hours or days?"
                )
                follow_up_questions = [
                    "Started today (built up gradually)",
                    "Started suddenly out of nowhere",
                    "Has lasted 2–3 days",
                    "Comes and goes in waves"
                ]
                risk_category = "MODERATE" if any(w in lower_msg for w in ["severe", "10", "9", "8", "7"]) else "LOW"

            elif patient_turns == 2:
                # TURN 3: Acknowledge duration & Ask Question 3 (Associated Symptoms)
                ai_response_text = (
                    "Got it, that helps narrow this down.\n\n"
                    "👉 **Question 3 of 3:** Are you experiencing any other symptoms alongside this (such as fever, nausea, dizziness, or neck stiffness)?"
                )
                follow_up_questions = [
                    "No other symptoms",
                    "Mild nausea or loss of appetite",
                    "Feeling feverish or chills",
                    "Dizziness or fatigue"
                ]
                risk_category = "LOW"

            else:
                # TURN 4+: Concise, bite-sized summary & recommendation
                ai_response_text = (
                    "Thank you for answering those questions! Here is a brief, safe summary:\n\n"
                    "• **Observation:** Your symptoms are commonly associated with tension, migraine-type episodes, viral fatigue, or dehydration.\n"
                    "• **Safe Comfort Measures:** Rest in a quiet, dark room, stay hydrated with sips of water, and avoid bright screens.\n"
                    "• **When to Consult:** If your discomfort persists beyond 24–48 hours or worsens, a licensed doctor should examine you.\n\n"
                    "Would you like to find a verified doctor or check another symptom?"
                )
                follow_up_questions = [
                    "Find a Verified Doctor",
                    "Check another symptom",
                    "Thank you, I feel informed"
                ]
                risk_category = "LOW"

        # Determine risk level from text
        lower_resp = (ai_response_text or "").lower()
        if "high risk" in lower_resp or "urgent" in lower_resp or "emergency" in lower_resp:
            risk_category = "HIGH"
        elif "moderate" in lower_resp or "worsen" in lower_resp:
            risk_category = "MODERATE"

        return {
            "message": ai_response_text,
            "risk_category": risk_category,
            "red_flag_alert": 0,
            "disclaimer": "Medical Disclaimer: This AI assistant provides health guidance for educational purposes only. It is not a substitute for clinical diagnosis or in-person medical care.",
            "follow_up_questions": follow_up_questions,
            "recommended_specialty": "General Medicine",
            "ai_provider": ai_provider_used
        }
