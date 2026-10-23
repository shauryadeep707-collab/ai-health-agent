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
    - Prompts for symptom duration, severity, age, and existing medical conditions.
    - Prohibits diagnosis declarations and prescription drug generation.
    - Categorizes clinical risk tiers: LOW, MODERATE, HIGH, EMERGENCY.
    - Integrates with Gemini API, Ollama, and offline clinical triage rules.
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
        Generates structured, safe medical guidance.
        """
        # Step 1: Immediate Red Flag Emergency Screening
        is_red_flag, red_flag_desc = AIHealthConsultationService.screen_emergency_red_flags(user_message)

        if is_red_flag:
            emergency_response = (
                f"🚨 **EMERGENCY WARNING SIGN DETECTED: {red_flag_desc}**\n\n"
                "Your symptoms indicate a potentially life-threatening medical situation that requires **immediate emergency medical evaluation**. "
                "Do not wait, and do not attempt self-care at home.\n\n"
                "**URGENT ACTIONS REQUIRED:**\n"
                "1. **Call emergency services immediately** (Dial 112 in India, 911 in North America, or your local emergency number).\n"
                "2. Have someone drive you to the nearest hospital Emergency Department if ambulance response is delayed.\n"
                "3. Stop all physical exertion, sit upright or lie comfortably, and keep your airways clear.\n"
                "4. Inform the emergency triage staff immediately about your exact symptoms upon arrival."
            )
            return {
                "message": emergency_response,
                "risk_category": "EMERGENCY",
                "red_flag_alert": 1,
                "disclaimer": "EMERGENCY ALERT: This is automated triage support. Seek immediate professional emergency healthcare.",
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

        system_prompt = (
            "You are the AI Health Agent clinical assistant. Your mission is to provide safe, clear, "
            "and compassionate health information to patients.\n"
            "STRICT CLINICAL RULES:\n"
            "1. You are NOT a doctor and must NEVER claim to be one.\n"
            "2. NEVER declare a definitive medical diagnosis. Phrase suggestions as 'Possible causes your doctor may consider...'\n"
            "3. NEVER prescribe or recommend specific dosages of prescription-only medications or antibiotics.\n"
            "4. Ask relevant follow-up questions regarding duration, severity (1-10), aggravating/relieving factors, and age.\n"
            "5. Provide safe self-care guidance (hydration, rest, gentle comfort measures) where clinically appropriate.\n"
            "6. Assign a realistic risk tier: 'LOW', 'MODERATE', or 'HIGH'.\n"
            "7. ALWAYS recommend consulting a qualified medical doctor for an in-person or formal clinical assessment.\n"
            "8. End every response with a reminder that this does not substitute for licensed medical care."
        )

        ai_response_text = None
        risk_category = "LOW"
        ai_provider_used = "Rule-based Health Agent"

        # Try Google Gemini
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
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 850}
                }
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            ai_response_text = parts[0].get("text")
                            ai_provider_used = f"Google Gemini ({Config.GEMINI_MODEL})"
            except Exception as e:
                logger.warning("Gemini AI health call failed (%s). Using fallback engine.", e)

        # Try Ollama
        elif Config.AI_PROVIDER == "ollama":
            try:
                ollama_url = f"{Config.OLLAMA_BASE_URL}/api/generate"
                prompt_text = f"{system_prompt}\n{patient_context}\nPatient Query: {user_message}\nAssistant:"
                res = requests.post(ollama_url, json={"model": Config.OLLAMA_MODEL, "prompt": prompt_text, "stream": False}, timeout=15)
                if res.status_code == 200:
                    ai_response_text = res.json().get("response")
                    ai_provider_used = f"Ollama ({Config.OLLAMA_MODEL})"
            except Exception as e:
                logger.warning("Ollama health call failed (%s). Using fallback engine.", e)

        # Fallback Clinical Guidance Engine
        if not ai_response_text:
            ai_response_text = (
                f"Thank you for sharing your symptoms regarding: **{user_message.strip()}**.\n\n"
                "**Clinical Observation & Considerations:**\n"
                "• Symptoms like these can arise from a range of everyday factors such as viral infections, muscular fatigue, hydration levels, or environmental changes.\n"
                "• Because multiple conditions can present with similar symptoms, a qualified healthcare professional should examine you for an accurate evaluation.\n\n"
                "**Helpful Questions to Consider:**\n"
                "1. How long have you experienced these symptoms (days or weeks)?\n"
                "2. On a scale of 1 to 10, how severe is the discomfort?\n"
                "3. Does anything specific make it better or worse (e.g. eating, resting, movement)?\n"
                "4. Are you currently taking any prescription medications or supplements?\n\n"
                "**Safe General Self-Care:**\n"
                "• Ensure optimal oral hydration with water and warm fluids.\n"
                "• Prioritize restful sleep and avoid strenuous physical overexertion.\n"
                "• Monitor your temperature if feeling feverish.\n\n"
                "**When to See a Doctor:**\n"
                "If your symptoms persist for more than 48–72 hours, worsen significantly, or if new symptoms develop, please consult a physician promptly."
            )
            risk_category = "LOW"

        # Determine risk level from text
        lower_resp = (ai_response_text or "").lower()
        if "high risk" in lower_resp or "urgent" in lower_resp:
            risk_category = "HIGH"
        elif "moderate" in lower_resp or "worsen" in lower_resp:
            risk_category = "MODERATE"

        return {
            "message": ai_response_text,
            "risk_category": risk_category,
            "red_flag_alert": 0,
            "disclaimer": "Medical Disclaimer: This AI assistant provides health guidance for educational purposes only. It is not a substitute for clinical diagnosis or in-person medical care.",
            "follow_up_questions": [
                "How many days have you had these symptoms?",
                "Are you experiencing any fever, nausea, or dizziness?",
                "Do you have any known medical conditions or drug allergies?"
            ],
            "recommended_specialty": "General Medicine",
            "ai_provider": ai_provider_used
        }
