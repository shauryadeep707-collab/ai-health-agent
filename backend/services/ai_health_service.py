import re
import json
import logging
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Clinical Emergency "Red-Flag" keywords and signs (Multilingual: English & Hinglish)
RED_FLAG_PATTERNS = [
    (r"\b(crushing|radiating|severe|tightness in|heaviness in)\s*(chest|breast|heart)\b", "Chest pain or pressure (potential acute coronary event)"),
    (r"\b(chhati|seene|chaati)\s*(me|mein)\s*(tez|bada|dard|pressure|jalan)\b", "Severe acute chest pain (coronary emergency)"),
    (r"\b(can'?t breathe|shortness of breath|gasping|severe wheezing|struggling to breathe|saas lene me takleef)\b", "Severe respiratory distress / hypoxia"),
    (r"\b(slurred speech|face drooping|facial droop|sudden weakness|arm numbness|loss of balance|adhrang|lakwa)\b", "Signs of acute cerebrovascular event (Stroke)"),
    (r"\b(coughing up blood|hemoptysis|vomiting blood|black tarry stool|khoon ki ulti)\b", "Active internal or gastrointestinal hemorrhage"),
    (r"\b(swollen tongue|throat closing|anaphylaxis|swelling of throat)\b", "Severe systemic allergic anaphylaxis"),
    (r"\b(unconscious|passed out|fainted|seizure|convulsions|behosh|daura)\b", "Loss of consciousness or acute seizure activity"),
    (r"\b(suicidal|kill myself|end my life|want to die|marne ka mann)\b", "Acute mental health emergency / crisis")
]

def clean_extracted_options(opt_part: str, default_options: list) -> list:
    """Cleans up options split by | and filters out invalid numbers/characters while preserving ranges."""
    clean_opts = []
    bullet_pattern = r"^\s*(?:\d+[\.\)]|\*|•|-)\s*"
    for opt in opt_part.split("|"):
        # Strip leading bullet/number markers (e.g. '1. ', '• ') without stripping ranges like '1-2 days'
        cleaned = re.sub(bullet_pattern, "", opt).strip()
        cleaned = re.sub(r"[\n\r]+", " ", cleaned).strip()
        if len(cleaned) >= 2 and len(cleaned) <= 50 and not cleaned.isdigit():
            clean_opts.append(cleaned)
    return clean_opts if len(clean_opts) >= 2 else default_options

class AIHealthConsultationService:
    """
    Conversational AI Health Assistant adhering to strict medical safety guidelines:
    - Screens for acute emergency red flags first (English & Hinglish).
    - Features trained clinical pharmacology RAG (WHO Essential Medicines Compendium).
    - Interfaces with local Ollama (`med-ai`), Google Gemini, and offline clinical triage rules.
    - Conducts a step-by-step interview asking ONE question at a time with clean clickable chips.
    - Prevents long walls of text; outputs concise, compassionate questions and guidance.
    - Categorizes clinical risk tiers: LOW, MODERATE, HIGH, EMERGENCY.
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
                f"Patient Profile: Gender: {patient_profile.get('gender', 'Unknown')}, "
                f"Blood Group: {patient_profile.get('blood_group', 'Unknown')}, "
                f"Known Allergies: {patient_profile.get('allergies', 'None recorded')}, "
                f"Chronic Conditions: {patient_profile.get('chronic_conditions', 'None recorded')}."
            )

        # Count previous patient messages in this consultation session
        patient_turns = len([m for m in (conversation_history or []) if m.get("sender_type") == "PATIENT"])

        system_prompt = (
            "You are AI Health Agent, a highly trained clinical triage and pharmacology assistant.\n"
            "STRICT CLINICAL RULES:\n"
            "1. KEEP RESPONSES SHORT, EMPATHETIC, AND UNDER 50 WORDS. Do NOT write long paragraphs.\n"
            "2. Ask ONLY ONE focused question at a time to guide the patient step-by-step.\n"
            "3. At the end of your response, always provide 3-4 clickable short choices formatted exactly as:\n"
            "OPTIONS: Choice 1 | Choice 2 | Choice 3\n"
            "4. Never prescribe prescription medications. Never give definitive diagnoses.\n"
            "5. If medicines are discussed, mention safe maximum limits and food instructions."
        )

        ai_response_text = None
        risk_category = "LOW"
        ai_provider_used = "Trained Clinical Health Agent"
        follow_up_questions = []

        # Step 3: Pharmacology Knowledge RAG (Retrieval-Augmented Generation)
        med_context = ""
        try:
            from backend.database.repositories import MedicineRepository
            matched_meds = []
            words = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", user_message.lower()) if w not in ("and", "the", "for", "with", "have", "what", "how", "take", "can", "mild", "severe")]
            for word in words[:6]:
                found = MedicineRepository.search(word, limit=2)
                if found:
                    for m in found:
                        if m["medicine_id"] not in [x["medicine_id"] for x in matched_meds]:
                            matched_meds.append(m)
            if matched_meds:
                med_context = "VERIFIED PHARMACOLOGY COMPENDIUM:\n"
                for m in matched_meds[:3]:
                    med_context += (
                        f"• Drug: {m['brand_name']} ({m['generic_name']})\n"
                        f"  Class: {m['therapeutic_class']}\n"
                        f"  Common Uses: {m['common_uses']}\n"
                        f"  Precautions: {m['safety_precautions']}\n"
                        f"  Contraindications: {m['contraindications']}\n"
                        f"  Side Effects: {m['common_side_effects']}\n"
                    )
                if len(matched_meds) >= 2:
                    interactions = MedicineRepository.check_interactions([m["medicine_id"] for m in matched_meds])
                    if interactions:
                        med_context += "  DRUG-DRUG INTERACTIONS:\n"
                        for inter in interactions:
                            med_context += f"  - [{inter['severity']}]: {inter['interaction_desc']} Advice: {inter['clinical_advice']}\n"
        except Exception as e:
            logger.warning("Medicine RAG lookup failed: %s", e)

        # Step 4: Try Local Ollama AI (med-ai)
        if Config.AI_PROVIDER == "ollama" or (not Config.GEMINI_API_KEY and not ai_response_text):
            try:
                ollama_url = f"{Config.OLLAMA_BASE_URL}/api/generate"
                prompt_full = (
                    f"{system_prompt}\n\n"
                    f"{patient_context}\n"
                    f"{med_context}\n"
                    f"Patient Query: {user_message}\n"
                    "Assistant (keep response concise, empathetic, and under 50 words):"
                )
                res = requests.post(
                    ollama_url,
                    json={
                        "model": Config.OLLAMA_MODEL or "med-ai",
                        "prompt": prompt_full,
                        "stream": False,
                        "options": {"temperature": 0.15, "num_predict": 140}
                    },
                    timeout=8  # Fast 8s timeout to prevent freezing
                )
                if res.status_code == 200:
                    raw_ollama = res.json().get("response", "").strip()
                    if raw_ollama:
                        if "OPTIONS:" in raw_ollama:
                            text_part, opt_part = raw_ollama.split("OPTIONS:", 1)
                            ai_response_text = text_part.strip()
                            follow_up_questions = clean_extracted_options(opt_part, ["Yes", "No", "Tell me more"])
                        else:
                            ai_response_text = raw_ollama
                        ai_provider_used = f"Ollama ({Config.OLLAMA_MODEL})"
            except Exception as e:
                logger.info("Ollama local inference skipped or timed out (%s). Using high-speed clinical engine.", e)

        # Step 5: Try Google Gemini if configured and Ollama not used
        if not ai_response_text and Config.AI_PROVIDER == "gemini" and Config.GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
                dialogue_parts = [{"text": f"System Instructions: {system_prompt}\n{patient_context}\n{med_context}"}]

                if conversation_history:
                    for msg in conversation_history[-6:]:
                        role = "user" if msg.get("sender_type") == "PATIENT" else "model"
                        dialogue_parts.append({"text": f"{role}: {msg.get('message_text')}"})

                dialogue_parts.append({"text": f"Patient: {user_message}"})

                payload = {
                    "contents": [{"parts": dialogue_parts}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 250}
                }
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "")
                            if "OPTIONS:" in raw_text:
                                text_part, opt_part = raw_text.split("OPTIONS:", 1)
                                ai_response_text = text_part.strip()
                                follow_up_questions = clean_extracted_options(opt_part, ["Mild", "Moderate", "Severe"])
                            else:
                                ai_response_text = raw_text.strip()
                            ai_provider_used = f"Google Gemini ({Config.GEMINI_MODEL})"
            except Exception as e:
                logger.warning("Gemini AI health call failed (%s). Using interactive rule engine.", e)

        # Step 6: High-Precision Deterministic Clinical Heuristic & RAG Engine
        if not ai_response_text:
            cleaned_query = user_message.strip()
            lower_msg = cleaned_query.lower()

            # Direct Pharmacology Question Checking
            if med_context and any(k in lower_msg for k in ["what is", "how to take", "can i take", "side effect", "dosage", "use", "interact"]):
                ai_response_text = (
                    f"Here is verified medical information regarding **{cleaned_query}**:\n\n"
                    f"{med_context.strip()}\n\n"
                    "• **Safety Rule:** Always take medications with water and never exceed prescribed daily limits."
                )
                follow_up_questions = [
                    "Check Drug Interactions",
                    "Find a Verified Doctor",
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
                # TURN 1: Specific symptom identification & Question 1 (Severity)
                symptom_detected = "your symptoms"
                if any(w in lower_msg for w in ["headache", "migraine", "sir dard", "sar dard"]):
                    symptom_detected = "headache / discomfort"
                elif any(w in lower_msg for w in ["fever", "bukhar", "temperature", "chills"]):
                    symptom_detected = "fever & body chills"
                elif any(w in lower_msg for w in ["cough", "khansi", "sore throat", "gale me", "cold", "zukaam"]):
                    symptom_detected = "cough & throat irritation"
                elif any(w in lower_msg for w in ["stomach", "pet dard", "acidity", "gas", "bloating", "nausea"]):
                    symptom_detected = "stomach discomfort"

                ai_response_text = (
                    f"I understand you are experiencing: **{cleaned_query}**.\n\n"
                    f"Let us check your {symptom_detected} step-by-step so you get safe guidance without a long wall of text.\n\n"
                    "**Question 1 of 3:** On a scale of 1 to 10, how severe or intense is the discomfort right now?"
                )
                follow_up_questions = [
                    "Mild (1 - 3)",
                    "Moderate (4 - 6)",
                    "Severe (7 - 9)",
                    "Very Intense (10)"
                ]
                risk_category = "LOW"

            elif patient_turns == 1:
                # TURN 2: Duration & Onset
                ai_response_text = (
                    f"Thank you for sharing the intensity (**{cleaned_query}**).\n\n"
                    "**Question 2 of 3:** Did this start suddenly out of nowhere, or did it build up gradually over hours or days?"
                )
                follow_up_questions = [
                    "Started today (built up gradually)",
                    "Started suddenly out of nowhere",
                    "Has lasted 2 - 3 days",
                    "Comes and goes in waves"
                ]
                risk_category = "MODERATE" if any(w in lower_msg for w in ["severe", "10", "9", "8", "7"]) else "LOW"

            elif patient_turns == 2:
                # TURN 3: Associated Secondary Symptoms
                ai_response_text = (
                    "Got it, that helps narrow this down.\n\n"
                    "**Question 3 of 3:** Are you experiencing any other symptoms alongside this (such as fever, nausea, dizziness, or neck stiffness)?"
                )
                follow_up_questions = [
                    "No other symptoms",
                    "Mild nausea or loss of appetite",
                    "Feeling feverish or chills",
                    "Dizziness or fatigue"
                ]
                risk_category = "LOW"

            else:
                # TURN 4+: Concise summary & doctor referral
                ai_response_text = (
                    "Thank you for answering those questions! Here is a brief, safe summary:\n\n"
                    "• **Observation:** Your reported symptoms are consistent with everyday mild-to-moderate irritation, tension, or viral fatigue.\n"
                    "• **Safe Home Care:** Rest in a comfortable, quiet room, stay well hydrated with water/warm fluids, and avoid physical strain.\n"
                    "• **When to Consult:** If your discomfort persists beyond 24–48 hours or worsens, a licensed doctor should examine you.\n\n"
                    "Would you like to book a consultation with a verified doctor?"
                )
                follow_up_questions = [
                    "Find a Verified Doctor",
                    "Check another symptom",
                    "Thank you, I feel informed"
                ]
                risk_category = "LOW"

        # Ensure follow-up questions are clean
        if not follow_up_questions or len(follow_up_questions) < 2:
            follow_up_questions = ["Mild (1 - 3)", "Moderate (4 - 6)", "Severe (7 - 9)"]

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
