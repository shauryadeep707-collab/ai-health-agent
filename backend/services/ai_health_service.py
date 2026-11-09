import re
import json
import logging
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Clinical Emergency "Red-Flag" keywords and signs (Multilingual: English & Hinglish)
RED_FLAG_PATTERNS = [
    (r"\b(crushing|radiating|severe|tightness in|heaviness in|sharp)\s+.*?(chest|breast|heart)\b", "Severe acute chest pain (coronary event)"),
    (r"\b(chest|heart)\s+.*?(pain|pressure|tightness|heaviness|burn)\b", "Chest pain or pressure (potential acute cardiac event)"),
    (r"\b(chhati|seene|chaati)\s+(?:me|mein)\s+.*?(tez|bada|dard|pressure|jalan|ghutan)\b", "Severe acute chest pain (coronary emergency)"),
    (r"\b(can'?t breathe|shortness of breath|gasping|severe wheezing|struggling to breathe|saas (?:nahi aa|lene me|ful|ruk))\b", "Severe respiratory distress / hypoxia"),
    (r"\b(slurred speech|face drooping|facial droop|sudden weakness|arm numbness|loss of balance|adhrang|lakwa)\b", "Signs of acute cerebrovascular event (Stroke)"),
    (r"\b(coughing up blood|hemoptysis|vomiting blood|black tarry stool|khoon ki ulti)\b", "Active internal or gastrointestinal hemorrhage"),
    (r"\b(swollen tongue|throat closing|anaphylaxis|swelling of throat)\b", "Severe systemic allergic anaphylaxis"),
    (r"\b(unconscious|passed out|fainted|seizure|convulsions|behosh|daura)\b", "Loss of consciousness or acute seizure activity"),
    (r"\b(suicidal|kill myself|end my life|want to die|marne ka mann)\b", "Acute mental health emergency / crisis")
]

# Fast clinical entity knowledge base for patient memory extraction
KNOWN_ALLERGENS = [
    "penicillin", "amoxicillin", "sulfa", "aspirin", "ibuprofen", "paracetamol",
    "codeine", "cephalosporin", "peanuts", "nuts", "shellfish", "seafood",
    "milk", "lactose", "eggs", "soy", "wheat", "gluten", "dust", "pollen", "latex"
]

KNOWN_CONDITIONS = [
    "asthma", "diabetes", "type 1 diabetes", "type 2 diabetes", "hypertension",
    "high bp", "low bp", "high blood pressure", "low blood pressure", "hypotension",
    "thyroid", "hypothyroidism", "hyperthyroidism", "migraine", "epilepsy", "seizure disorder",
    "gerd", "acid reflux", "gastritis", "kidney disease", "renal disease",
    "arthritis", "pcos", "depression", "anxiety", "high cholesterol"
]

def clean_extracted_options(opt_part: str, default_options: list) -> list:
    """Cleans up options split by | and filters out invalid numbers/characters while preserving ranges."""
    clean_opts = []
    bullet_pattern = r"^\s*(?:\d+[\.\)]|\*|•|-|choice\s*\d+:?)\s*"
    for opt in opt_part.split("|"):
        cleaned = re.sub(bullet_pattern, "", opt, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"[\n\r]+", " ", cleaned).strip()
        cleaned = re.sub(r"^\*+|\*+$", "", cleaned).strip()
        if len(cleaned) >= 2 and len(cleaned) <= 60 and not cleaned.isdigit():
            clean_opts.append(cleaned)
    return clean_opts if len(clean_opts) >= 2 else default_options

def extract_clinical_facts_regex(user_message: str) -> dict:
    """
    Pattern-based clinical entity extraction from patient messages.
    Identifies newly declared allergies and chronic conditions in English and Hinglish.
    """
    lower = user_message.lower()
    allergies_found = []
    conditions_found = []

    # Check for direct allergy mentions
    for allergen in KNOWN_ALLERGENS:
        pattern = (
            rf"\b(?:allergic\s+to|allergy\s+(?:to|from|se)?|reaction\s+to)\s+.*?{allergen}\b|"
            rf"\b{allergen}\s+(?:se\s+)?allergy\b"
        )
        if re.search(pattern, lower) or (allergen in lower and any(k in lower for k in ["allergy", "allergic", "reaction", "suit nahi"])):
            allergies_found.append(allergen.title())

    # Check for chronic condition mentions
    for cond in KNOWN_CONDITIONS:
        pattern = (
            rf"\b(?:have|diagnosed\s+with|suffering\s+from|patient\s+of|history\s+of|mujhe)\s+.*?{cond}\b|"
            rf"\b{cond}\s+(?:hai|ki\s+problem|patient)\b"
        )
        if re.search(pattern, lower) or (cond in lower and any(k in lower for k in ["have", "mujhe", "patient", "problem", "bimari", "diagnosed", "rehta hai"])):
            conditions_found.append(cond.title())

    return {
        "allergies": list(set(allergies_found)),
        "conditions": list(set(conditions_found))
    }

class AIHealthConsultationService:
    """
    Senior MBBS/MD Clinical Consultant Doctor AI:
    - Empathetic, warm, professional bedside manner (Dr. Aanya, MD).
    - Active clinical listening: explains causes, home supportive care, red flags.
    - Dynamic Patient Memory: Learns from patient messages across turns and updates Supabase database.
    - Pharmacological safety checking (WHO essential medicines RAG + drug interactions).
    - Multilingual fluency: Conversational English and natural Hinglish.
    - Life-threatening red flag emergency screening (Call 112 / 108 / 911).
    """

    @staticmethod
    def screen_emergency_red_flags(user_message: str) -> tuple[bool, str]:
        """
        Scans message for acute emergency red flags.
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
        Generates empathetic, doctor-style clinical guidance with dynamic patient learning.
        """
        # Step 1: Immediate Red Flag Emergency Screening
        is_red_flag, red_flag_desc = AIHealthConsultationService.screen_emergency_red_flags(user_message)

        if is_red_flag:
            emergency_response = (
                f"🚨 **EMERGENCY WARNING SIGN DETECTED: {red_flag_desc}**\n\n"
                "Your symptoms indicate a potentially critical condition requiring **immediate emergency medical evaluation**.\n\n"
                "**URGENT ACTIONS REQUIRED:**\n"
                "1. **Call emergency services immediately** (Dial **112** or **108** in India, **911** in North America).\n"
                "2. Go directly to the nearest Hospital Emergency Department.\n"
                "3. Stop physical exertion, sit comfortably, and keep your airways clear.\n"
                "4. If you are alone, alert a family member or neighbor right away."
            )
            return {
                "message": emergency_response,
                "risk_category": "EMERGENCY",
                "red_flag_alert": 1,
                "disclaimer": "EMERGENCY ALERT: Immediate professional emergency medical care required.",
                "follow_up_questions": ["Call 112 / Emergency", "Find Nearest Hospital", "Notify Emergency Contact"],
                "recommended_specialty": "Emergency Medicine / Critical Care",
                "ai_provider": "Emergency Clinical Safety System",
                "learned_memory": None
            }

        # Step 2: Patient Profile & Clinical Memory Preparation
        patient_name = "there"
        patient_context = ""
        known_allergies = "None recorded"
        known_conditions = "None recorded"

        if patient_profile:
            patient_name = patient_profile.get("full_name") or "there"
            known_allergies = patient_profile.get("allergies") or "None recorded"
            known_conditions = patient_profile.get("chronic_conditions") or "None recorded"
            gender = patient_profile.get("gender") or "Not specified"
            blood_group = patient_profile.get("blood_group") or "Not specified"

            patient_context = (
                f"PATIENT CLINICAL RECORD (FROM PERSISTENT DATABASE MEMORY):\n"
                f"• Patient Name: {patient_name}\n"
                f"• Gender: {gender} | Blood Group: {blood_group}\n"
                f"• Known Allergies: {known_allergies}\n"
                f"• Chronic Conditions / Medical History: {known_conditions}\n"
                f"CLINICAL INSTRUCTION: You already know this patient's medical history. Greet them warmly by name if it's the start of the chat. "
                f"Always cross-check your guidance against their known allergies and chronic conditions."
            )

        # Step 3: Pharmacology Knowledge RAG (Retrieval-Augmented Generation)
        med_context = ""
        try:
            from backend.database.repositories import MedicineRepository
            matched_meds = []
            words = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", user_message.lower())
                     if w not in ("and", "the", "for", "with", "have", "what", "how", "take", "can", "mild", "severe", "feeling", "today", "yesterday", "doctor", "please")]
            for word in words[:6]:
                found = MedicineRepository.search(word, limit=2)
                if found:
                    for m in found:
                        if m["medicine_id"] not in [x["medicine_id"] for x in matched_meds]:
                            matched_meds.append(m)
            if matched_meds:
                med_context = "\nVERIFIED PHARMACOLOGY REFERENCE:\n"
                for m in matched_meds[:3]:
                    med_context += (
                        f"• Drug: {m['brand_name']} ({m['generic_name']})\n"
                        f"  Class: {m['therapeutic_class']} | Common Uses: {m['common_uses']}\n"
                        f"  Precautions: {m['safety_precautions']} | Contraindications: {m['contraindications']}\n"
                    )
                if len(matched_meds) >= 2:
                    interactions = MedicineRepository.check_interactions([m["medicine_id"] for m in matched_meds])
                    if interactions:
                        med_context += "  DRUG-DRUG INTERACTIONS:\n"
                        for inter in interactions:
                            med_context += f"  - [{inter['severity']}]: {inter['interaction_desc']} Advice: {inter['clinical_advice']}\n"
        except Exception as e:
            logger.warning("Medicine RAG lookup failed: %s", e)

        # Step 4: Doctor Persona System Prompt
        system_prompt = (
            "You are Dr. Aanya, a highly respected Senior Consultant Clinical Doctor (MBBS, MD) at AI Health Agent.\n"
            "YOUR CLINICAL CONSULTATION MANNER:\n"
            "1. Talk like a real, caring, highly competent medical doctor. Use a warm, reassuring, and empathetic tone.\n"
            "2. Multilingual: If the patient writes in Hindi/Hinglish (e.g. 'sar dard', 'ulti jaisa'), respond in natural, friendly Hinglish. If in English, respond in clear, compassionate English.\n"
            "3. Active Clinical Listening & Guidance:\n"
            "   - Reassure the patient first so they feel heard and cared for.\n"
            "   - Provide clear Clinical Reasoning: explain in simple terms what might be happening (e.g. tension headache, viral irritation, migraine, gastric reflux).\n"
            "   - Offer practical Home Care and Supportive Measures (hydration, rest, dietary care, light meals).\n"
            "   - Clearly state Red Flag Warning Signs when they should immediately seek in-person emergency or specialist care.\n"
            "4. Dynamic Patient Memory & Learning:\n"
            "   - If the patient mentions an allergy (e.g. 'allergic to penicillin', 'dust allergy') or a chronic condition (e.g. 'asthma', 'diabetes', 'high BP'), or regular medications, acknowledge it warmly.\n"
            "   - At the VERY END of your response, output a learning tag formatted exactly as:\n"
            "     LEARNED: allergy: <allergen or none> | condition: <condition or none>\n"
            "5. Follow-up Clickable Options:\n"
            "   - End your response with 3 natural clickable follow-up options for the patient, formatted exactly as:\n"
            "     OPTIONS: Option 1 | Option 2 | Option 3\n"
            "6. Safety & Boundaries: Do not write prescription dosages for schedule H drugs. Emphasize that you provide clinical triage guidance."
        )

        ai_response_text = None
        risk_category = "LOW"
        ai_provider_used = "Senior Clinical Health Consultant"
        follow_up_questions = []
        learned_allergies = []
        learned_conditions = []

        # Step 5: Call Google Gemini API (Model Cascade with Fallback)
        if Config.AI_PROVIDER == "gemini" and Config.GEMINI_API_KEY:
            gemini_models = [Config.GEMINI_MODEL, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
            for model_name in gemini_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={Config.GEMINI_API_KEY}"
                    full_system = f"{system_prompt}\n\n{patient_context}\n\n{med_context}".strip()

                    contents = []
                    if conversation_history:
                        for msg in conversation_history[-8:]:
                            role = "user" if msg.get("sender_type") == "PATIENT" else "model"
                            txt = msg.get("message_text", "").strip()
                            if txt:
                                contents.append({"role": role, "parts": [{"text": txt}]})

                    contents.append({"role": "user", "parts": [{"text": user_message}]})

                    payload = {
                        "system_instruction": {"parts": [{"text": full_system}]},
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.25,
                            "maxOutputTokens": 2048
                        }
                    }

                    res = requests.post(url, json=payload, timeout=10)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts:
                                raw_text = parts[0].get("text", "").strip()
                                if raw_text:
                                    ai_response_text = raw_text
                                    ai_provider_used = f"Dr. Aanya AI (Gemini {model_name})"
                                    break
                    else:
                        logger.warning("Gemini %s returned HTTP %s: %s", model_name, res.status_code, res.text[:200])
                except Exception as e:
                    logger.warning("Gemini %s attempt failed (%s). Trying next cascade model.", model_name, e)

        # Step 6: Try Local Ollama if Gemini failed or Ollama configured
        if not ai_response_text and (Config.AI_PROVIDER == "ollama" or not Config.GEMINI_API_KEY):
            try:
                ollama_url = f"{Config.OLLAMA_BASE_URL}/api/generate"
                prompt_full = (
                    f"{system_prompt}\n\n{patient_context}\n\n{med_context}\n"
                    f"Patient Query: {user_message}\n"
                    "Dr. Aanya (Senior Clinical Consultant):"
                )
                res = requests.post(
                    ollama_url,
                    json={
                        "model": Config.OLLAMA_MODEL or "med-ai",
                        "prompt": prompt_full,
                        "stream": False,
                        "options": {"temperature": 0.2, "num_predict": 400}
                    },
                    timeout=8
                )
                if res.status_code == 200:
                    raw_ollama = res.json().get("response", "").strip()
                    if raw_ollama:
                        ai_response_text = raw_ollama
                        ai_provider_used = f"Dr. Aanya AI (Ollama {Config.OLLAMA_MODEL})"
            except Exception as e:
                logger.info("Ollama local inference skipped: %s", e)

        # Step 7: Parse OPTIONS and LEARNED tags from generated text
        if ai_response_text:
            learned_match = re.search(r"LEARNED:\s*allergy:\s*([^|\n]+)\s*\|\s*condition:\s*([^\n]+)", ai_response_text, re.IGNORECASE)
            if learned_match:
                raw_allergy = learned_match.group(1).strip()
                raw_condition = learned_match.group(2).strip()

                if raw_allergy.lower() not in ("none", "null", "n/a", "no", "not specified"):
                    for item in raw_allergy.split(","):
                        c = item.strip().title()
                        if c and len(c) > 1:
                            learned_allergies.append(c)

                if raw_condition.lower() not in ("none", "null", "n/a", "no", "not specified"):
                    for item in raw_condition.split(","):
                        c = item.strip().title()
                        if c and len(c) > 1:
                            learned_conditions.append(c)

                ai_response_text = re.sub(r"LEARNED:\s*allergy:[^\n]+\|\s*condition:[^\n]+", "", ai_response_text, flags=re.IGNORECASE).strip()

            if "OPTIONS:" in ai_response_text:
                text_part, opt_part = ai_response_text.split("OPTIONS:", 1)
                ai_response_text = text_part.strip()
                follow_up_questions = clean_extracted_options(opt_part, ["Tell me more", "What home remedies help?", "When should I see a doctor?"])

        # Also run regex clinical entity extractor as a safety net
        regex_extracted = extract_clinical_facts_regex(user_message)
        for a in regex_extracted["allergies"]:
            if not any(a.lower() == x.lower() for x in learned_allergies):
                learned_allergies.append(a)
        for c in regex_extracted["conditions"]:
            if not any(c.lower() == x.lower() for x in learned_conditions):
                learned_conditions.append(c)

        # Step 8: High-Precision Empathetic Clinical Fallback (if AI service is offline)
        if not ai_response_text:
            cleaned_query = user_message.strip()
            lower_msg = cleaned_query.lower()

            if "restart" in lower_msg or "reset" in lower_msg or "clear" in lower_msg:
                ai_response_text = (
                    f"Hello {patient_name}! Our consultation has been refreshed. "
                    "I am Dr. Aanya, your Clinical Health Consultant. What symptoms or questions can I help you check today?"
                )
                follow_up_questions = [
                    "Throbbing Headache & Nausea",
                    "Dry Cough & Mild Fever",
                    "Stomach Acidity & Bloating",
                    "Body Fatigue & Muscle Ache"
                ]
            elif med_context and any(k in lower_msg for k in ["what is", "how to take", "can i take", "side effect", "dosage", "use"]):
                ai_response_text = (
                    f"Here is verified clinical pharmacology guidance regarding **{cleaned_query}**:\n\n"
                    f"{med_context.strip()}\n\n"
                    "• **Doctor's Advice:** Always take medications with adequate water and strictly adhere to prescribed limits."
                )
                follow_up_questions = ["Check Drug Interactions", "Find Verified Doctor", "Safe dosage guidelines"]
            else:
                is_hinglish = any(w in lower_msg for w in ["dard", "sir", "sar", "pet", "ulti", "bukhar", "khansi", "gala", "chakkar", "mujhe", "hai"])
                if is_hinglish:
                    ai_response_text = (
                        f"Namaste {patient_name}. Main Dr. Aanya hoon. Aapki takleef sunkar mujhe dhyan aaya ki aap **{cleaned_query}** se pareshan hain.\n\n"
                        "**Doctor's Clinical Observation:**\n"
                        "Aam taur par yeh lakshan thakaan, mausam ke badlav, viral fatigue ya gastric irritation ki wajah se ho sakte hain.\n\n"
                        "**Gharelu Upay aur Aaram (Supportive Care):**\n"
                        "1. **Adequate Rest:** Ek shant kamre me aaram karein aur phone/screen se thodi doori banayein.\n"
                        "2. **Hydration:** Ghoont-ghoont karke halka gunguna paani ya ORS piyein.\n"
                        "3. **Light Meals:** Tel-masale aur bhari khane se bachein; khichdi ya dal-chawal lein.\n\n"
                        "⚠️ **Red Flag Warning:** Agar dard achanak bohot tez ho jaye, saans lene me takleef ho, ya 102°F se zyada bukhar ho, toh turant doctor ko consult karein."
                    )
                    follow_up_questions = [
                        "Kyunki dard kal se hai, kya dawa lu?",
                        "Kya mujhe doctor ko dikhana chahiye?",
                        "Gharelu upay aur batayein"
                    ]
                else:
                    ai_response_text = (
                        f"Hello {patient_name}, I am Dr. Aanya. I hear your concern regarding **{cleaned_query}**.\n\n"
                        "**Clinical Assessment & Possibilities:**\n"
                        "Symptoms like these commonly stem from viral fatigue, tension, mild dehydration, or everyday physical strain.\n\n"
                        "**Recommended Supportive Home Care:**\n"
                        "1. **Rest & Recovery:** Rest in a calm, dimly lit room and avoid straining your eyes.\n"
                        "2. **Hydration:** Sip water steadily throughout the day or take electrolyte fluids.\n"
                        "3. **Gentle Nutrition:** Stick to bland, easily digestible food (toast, soups, oatmeal).\n\n"
                        "⚠️ **When to Seek Urgent Care:** If symptoms worsen significantly over the next 24 hours, or you develop severe fever, persistent vomiting, or difficulty breathing, please seek immediate in-person medical evaluation."
                    )
                    follow_up_questions = [
                        "What home remedies can help?",
                        "Should I consult a specialist?",
                        "Can I take OTC pain relief?"
                    ]

        # Step 9: Append Clinical Memory Note if new facts were learned
        learned_summary = []
        if learned_allergies:
            learned_summary.append(f"Allergies: {', '.join(learned_allergies)}")
        if learned_conditions:
            learned_summary.append(f"Conditions: {', '.join(learned_conditions)}")

        if learned_summary:
            ai_response_text += f"\n\n🧠 *Clinical Memory Updated:* Recorded **{' | '.join(learned_summary)}** in your patient health file."

        # Step 10: Ensure Clean Follow-Up Options
        if not follow_up_questions or len(follow_up_questions) < 2:
            follow_up_questions = ["What home remedies help?", "When should I consult a doctor?", "Check safe medications"]

        # Determine risk level from text
        lower_resp = (ai_response_text or "").lower()
        if "high risk" in lower_resp or "urgent" in lower_resp or "emergency" in lower_resp:
            risk_category = "HIGH"
        elif "moderate" in lower_resp or "worsen" in lower_resp or "specialist" in lower_resp:
            risk_category = "MODERATE"

        return {
            "message": ai_response_text,
            "risk_category": risk_category,
            "red_flag_alert": 0,
            "disclaimer": "Medical Guidance Notice: Dr. Aanya provides clinical triage and educational guidance. It is not an in-person diagnostic examination.",
            "follow_up_questions": follow_up_questions,
            "recommended_specialty": "General Medicine / Internal Medicine",
            "ai_provider": ai_provider_used,
            "learned_memory": {
                "allergies": learned_allergies,
                "conditions": learned_conditions
            } if (learned_allergies or learned_conditions) else None
        }
