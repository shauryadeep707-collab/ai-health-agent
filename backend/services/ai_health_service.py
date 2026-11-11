import re
import json
import logging
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Clinical Emergency "Red-Flag" keywords and signs (Multilingual: English & Hinglish)
RED_FLAG_PATTERNS = [
    (r"(?<!no\s)(?<!not\s)\b(crushing|radiating|severe|tightness in|heaviness in)\s+(?:\w+\s+){0,3}(chest|breast|heart)\b", "Chest pain emergency (severe acute coronary event)"),
    (r"(?<!no\s)(?<!not\s)(?<!without\s)\b(chest|heart)\s+(?:\w+\s+){0,2}(pain|pressure|tightness|heaviness)\b", "Chest pain or pressure (potential acute cardiac event)"),
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
    Senior MBBS/MD Clinical Consultant Doctor AI (Dr. Aanya):
    - Short, point-to-point clinical triage (no long essays).
    - Prescribes safe supportive/OTC medicines in a structured Prescription Box (Rx) with:
      Medicine name, frequency (times a day), when to take, duration (how many days), and key notes.
    - Active clinical listening & dynamic memory learning saved directly to database.
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
    def generate_health_guidance(user_message: str, conversation_history: list = None, patient_profile: dict = None, doctor_profile: dict = None) -> dict:
        """
        Generates short, point-to-point doctor guidance with a mandatory Prescription Box.
        Supports both Dr. Aanya (General AI Assistant) and appointed AI Specialist doctors (e.g. Dr. Priya Sharma).
        """
        # Step 1: Immediate Red Flag Emergency Screening
        # In Doctor Appointment Chat (doctor_profile), only trigger hard emergency block on explicit acute crises
        # so mild/unqualified symptom mentions (e.g. "I have chest pain") allow the doctor to talk and triage normally first.
        is_red_flag, red_flag_desc = AIHealthConsultationService.screen_emergency_red_flags(user_message)
        if is_red_flag and doctor_profile:
            lower_q = user_message.lower()
            is_unmistakable_crisis = any(
                k in lower_q for k in [
                    "crushing", "radiating", "can't breathe", "cant breathe", "gasping",
                    "slurred speech", "face drooping", "vomiting blood", "coughing up blood",
                    "unconscious", "passed out", "fainted", "seizure", "suicidal", "kill myself",
                    "anaphylaxis", "throat closing", "behosh", "khoon ki ulti"
                ]
            )
            if not is_unmistakable_crisis:
                is_red_flag = False

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
                f"CLINICAL INSTRUCTION: Address the patient warmly by name. Cross-check your guidance against their known allergies and chronic conditions."
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

        # Step 4: Doctor Persona Setup (Default: Dr. Aanya; Appointment AI Doctor: e.g. Dr. Priya Sharma)
        doctor_display_name = "Dr. Aanya"
        doctor_specialty = "General Medicine / Internal Medicine"
        doctor_qual = "MBBS, MD"
        appointment_ctx = ""

        if doctor_profile:
            raw_doc_name = (doctor_profile.get("full_name") or "Priya Sharma").strip()
            clean_doc = re.sub(r"^(?:dr\.?\s*)+", "", raw_doc_name, flags=re.IGNORECASE).strip()
            doctor_display_name = f"Dr. {clean_doc}" if clean_doc else "Dr. Priya Sharma"
            doctor_specialty = doctor_profile.get("specialty") or "Clinical Specialist"
            doctor_qual = doctor_profile.get("medical_qualification") or doctor_profile.get("qualification") or "MBBS, MD"
            reason = (doctor_profile.get("appointment_reason") or "").strip()
            if reason:
                appointment_ctx = f"\nAPPOINTMENT CONTEXT: You are consulting with this patient during their confirmed appointment. Reason for visit: {reason}"

        patient_turns = sum(1 for m in (conversation_history or []) if m.get("sender_type") == "PATIENT")
        lower_user_q = user_message.lower().strip()
        is_greeting_only = bool(re.match(r"^(?:hi+|hello+|hey+|namaste|hlo|good\s+(?:morning|afternoon|evening))[\s!.,]*$", lower_user_q))
        explicitly_wants_meds = any(k in lower_user_q for k in ["prescribe", "prescription", "medicine", "tablet", "dawai", "rx", "meds"])
        talk_first_mode = is_greeting_only or (bool(doctor_profile) and patient_turns == 0 and not explicitly_wants_meds)

        if talk_first_mode:
            stage_instructions = (
                "CONVERSATION STAGE: NORMAL DOCTOR CONSULTATION — TALK FIRST (DO NOT PRESCRIBE YET).\n"
                "3. Keep your reply warm, natural, and conversational like a real doctor chatting (2 to 4 short sentences MAX).\n"
                "   - Acknowledge the patient's message calmly.\n"
                "   - Ask 1 or 2 brief, focused clinical questions first (e.g., how long it has been going on, whether mild or severe, triggers like food/stress, or any associated symptoms) before diagnosing or prescribing.\n"
                "   - If the patient mentions chest discomfort, stay calm and ask if it feels mild/burning or heavy/squeezing with breathlessness (briefly note: seek 112 emergency care only if severe/crushing).\n"
                "   - DO NOT include 'Clinical Assessment', 'Home Supportive Care' bullet walls, or any PRESCRIPTION BOX table in this turn.\n"
            )
        else:
            stage_instructions = (
                "CONVERSATION STAGE: CLINICAL EXPLANATION & PRESCRIPTION.\n"
                "3. RESPONSE FORMAT (USE THESE 3 CONCISE SECTIONS):\n"
                "   • 🩺 **Clinical Assessment:** (2 short bullet points on the most probable causes)\n"
                "   • 🏠 **Home Supportive Care:** (2-3 short bullet points on immediate relief, diet, hydration)\n"
                "   • ⚠️ **Red Flag Warnings:** (1-2 short bullet points on critical signs to visit ER)\n"
                "4. PRESCRIPTION BOX (MANDATORY AT THE END OF MEDICAL ADVICE):\n"
                "   You MUST prescribe 1-2 safe OTC or supportive medicines in a clear table formatted exactly as:\n"
                "   📋 **PRESCRIPTION BOX (Rx):**\n"
                "   | 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                "   | :--- | :--- | :--- | :--- | :--- |\n"
                "   | [Medicine 1] | [e.g. 2 times a day] | [e.g. 30 min before breakfast / after meals with water] | [e.g. 3 to 5 days] | [Short clinical advice] |\n"
                "   (Add a 2nd row for antacid, electrolyte/ORS, or fever relief if appropriate)\n"
            )

        system_prompt = (
            f"You are {doctor_display_name}, a highly respected Senior Consultant {doctor_specialty} Doctor ({doctor_qual}) at AI Health Agent.{appointment_ctx}\n"
            "CRITICAL CONSULTATION INSTRUCTIONS (STRICTLY ENFORCE):\n"
            "1. KEEP YOUR RESPONSE SHORT, CRISP, AND POINT-TO-POINT. Never write long essays or wordy paragraphs.\n"
            "2. MULTILINGUAL: If the patient writes in Hindi/Hinglish (e.g. 'sar dard', 'acidity', 'ulti'), reply in warm, natural Hinglish. If in English, reply in clean, concise English.\n"
            f"{stage_instructions}"
            "5. DYNAMIC PATIENT MEMORY: If the patient mentions an allergy or chronic condition, note it and append at the very end:\n"
            "   LEARNED: allergy: <allergen or none> | condition: <condition or none>\n"
            "6. FOLLOW-UP OPTIONS: Provide 3 short clickable options at the very end:\n"
            "   OPTIONS: Option 1 | Option 2 | Option 3"
        )

        ai_response_text = None
        risk_category = "LOW"
        ai_provider_used = f"{doctor_display_name} AI (Clinical Consultant)"
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
                            "temperature": 0.2,
                            "maxOutputTokens": 2500
                        }
                    }

                    res = requests.post(url, json=payload, timeout=15)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts:
                                raw_text = parts[0].get("text", "").strip()
                                if raw_text:
                                    ai_response_text = raw_text
                                    ai_provider_used = f"{doctor_display_name} AI (Gemini {model_name})"
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
                    f"{doctor_display_name} (Senior Clinical Consultant):"
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
                        ai_provider_used = f"{doctor_display_name} AI (Ollama {Config.OLLAMA_MODEL})"
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

        # Step 8: High-Precision Empathetic Clinical Fallback (Short, Point-to-Point + Prescription Box)
        if not ai_response_text:
            cleaned_query = user_message.strip()
            lower_msg = cleaned_query.lower()

            if "restart" in lower_msg or "reset" in lower_msg or "clear" in lower_msg:
                ai_response_text = (
                    f"Hello {patient_name}! Our consultation has been refreshed. "
                    f"I am {doctor_display_name}, your Clinical Health Consultant. What symptoms can I check for you today?"
                )
                follow_up_questions = [
                    "Acidity & Bloating",
                    "Headache & Nausea",
                    "Cough & Mild Fever",
                    "Body Ache & Fatigue"
                ]
            elif talk_first_mode:
                is_hinglish = any(w in lower_msg for w in ["dard", "sir", "sar", "pet", "ulti", "bukhar", "khansi", "gala", "chakkar", "mujhe", "hai", "khana", "namaste"])
                if is_greeting_only:
                    ai_response_text = (
                        f"Hello {patient_name}! I'm {doctor_display_name}. Good to connect with you — how are you feeling today, and what symptoms or questions can I help you with?"
                    )
                    follow_up_questions = ["I have chest discomfort", "Acidity after meals", "Headache & fatigue"]
                elif is_hinglish:
                    ai_response_text = (
                        f"Namaste {patient_name}, main {doctor_display_name} hoon. Aapki problem samajhne ke liye pehle 2 chote sawaal:\n\n"
                        "1. Yeh takleef **kab se** hai aur kitni tez (halki ya zyada) lag rahi hai?\n"
                        "2. Kya iske saath koi aur lakshan (jaise bukhar, ghabrahat, saans phoolna, ya kisi dawai se allergy) bhi hai?"
                    )
                    follow_up_questions = ["Aaj subah se halki hai", "2-3 din se moderate hai", "Koi allergy nahi hai"]
                else:
                    ai_response_text = (
                        f"Hello {patient_name}, I'm {doctor_display_name}. Before I suggest treatment, let's talk through two quick details:\n\n"
                        "1. **How long** have you noticed these symptoms, and would you describe them as mild, moderate, or severe?\n"
                        "2. Are you having any **other symptoms** (fever, nausea, breathlessness) or any known medication allergies?"
                    )
                    follow_up_questions = ["Started today & mild", "Since 2-3 days, moderate", "No allergies, need relief tips"]
            else:
                is_hinglish = any(w in lower_msg for w in ["dard", "sir", "sar", "pet", "ulti", "bukhar", "khansi", "gala", "chakkar", "mujhe", "hai", "khana"])

                # Determine clinical condition for targeted short response + prescription
                if any(w in lower_msg for w in ["acidity", "gas", "bloat", "pet", "indigestion", "heartburn", "acid"]):
                    if is_hinglish:
                        ai_response_text = (
                            f"Namaste {patient_name}, main {doctor_display_name} hoon. Acidity aur bloating ke liye yeh points follow karein:\n\n"
                            "🩺 **Clinical Assessment:**\n"
                            "• **Indigestion (Dyspepsia):** Khana jaldi khane ya spicy/oily khane se gas banna.\n"
                            "• **Acid Reflux:** Pet ka acid upar aane se pet phoolna aur jalan hona.\n\n"
                            "🏠 **Home Supportive Care:**\n"
                            "• Khana khane ke baad 10-15 minute dheere tehele; turant bistar par na letein.\n"
                            "• Thoda-thoda karke gunguna paani piyein; chai/coffee aur cold drink se bachein.\n"
                            "• Ek baar mein zyada khane ki jagah halka aur saadha khana lein.\n\n"
                            "⚠️ **Red Flag Warnings:**\n"
                            "• Pet me achanak bohot tez dard hona ya baar-baar ulti aana.\n"
                            "• Kale rang ka mal (black stool) ya nigalne me dard hona.\n\n"
                            "📋 **PRESCRIPTION BOX (Rx):**\n"
                            "| 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| **Tab. Pantoprazole 40mg** | Din mein 1 baar | Subah nashte se 30 min pehle | 3 - 5 din | Pet ka acid kam karne ke liye |\n"
                            "| **Syp. Digene Gel (10ml)** | Din mein 2 baar | Khana khane ke 1 ghante baad | 3 din | Gas aur jalan se turant aaram |"
                        )
                    else:
                        ai_response_text = (
                            f"Hello {patient_name}, I am {doctor_display_name}. Here is your quick point-to-point assessment and prescription for acidity and bloating:\n\n"
                            "🩺 **Clinical Assessment:**\n"
                            "• **Indigestion (Dyspepsia):** Delayed digestion causing gas buildup after meals.\n"
                            "• **Acid Reflux (GERD):** Excess gastric acid irritated by spicy foods or stress.\n\n"
                            "🏠 **Home Supportive Care:**\n"
                            "• Take a light 15-minute walk after meals; do not recline for 2 hours.\n"
                            "• Sip warm water or ginger tea; strictly avoid carbonated soda and caffeine.\n"
                            "• Eat smaller, frequent portions and chew thoroughly.\n\n"
                            "⚠️ **Red Flag Warnings:**\n"
                            "• Sharp, severe abdominal pain radiating to your back.\n"
                            "• Dark/black tarry stools or persistent vomiting.\n\n"
                            "📋 **PRESCRIPTION BOX (Rx):**\n"
                            "| 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| **Pantoprazole 40mg (1 Tab)** | Once daily | 30 mins before breakfast | 3 - 5 days | Reduces stomach acid production |\n"
                            "| **Digene Antacid Gel (10ml)** | 2 to 3 times a day | 1 hour after meals | 3 days | Rapid relief from gas & heartburn |"
                        )
                    follow_up_questions = ["What food should I avoid?", "Can I drink milk?", "When should I consult in person?"]

                elif any(w in lower_msg for w in ["headache", "sir dard", "sar dard", "migraine"]):
                    if is_hinglish:
                        ai_response_text = (
                            f"Namaste {patient_name}. Sar dard ke liye quick points aur safe prescription yeh hai:\n\n"
                            "🩺 **Clinical Assessment:**\n"
                            "• **Tension Headache:** Screen time, neend ki kami ya stress ki wajah se maspeshiyo me khinchav.\n"
                            "• **Dehydration / Fatigue:** Paani ki kami se sar me bhaari-pan.\n\n"
                            "🏠 **Home Supportive Care:**\n"
                            "• Ek shaant aur andhere kamre me aaram karein; phone screen band rakhein.\n"
                            "• Khoob paani ya nariyal paani piyein.\n"
                            "• Mathe par thande paani ki patti rakhein.\n\n"
                            "⚠️ **Red Flag Warnings:**\n"
                            "• Achanak aane wala bohot tez dard (thunderclap) ya gardan me akad.\n"
                            "• Aankhon ke aage andhera chhana ya bolne me takleef.\n\n"
                            "📋 **PRESCRIPTION BOX (Rx):**\n"
                            "| 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| **Tab. Paracetamol 500mg** | Din mein 2 baar | Khana khane ke baad paani se | 2 - 3 din | Sar dard aur thakan ke liye |\n"
                            "| **ORS / Hydration Drink** | Din mein 1 sachet | 1 litre paani me gholkar | 2 din | Sharir me paani ki kami poori kare |"
                        )
                    else:
                        ai_response_text = (
                            f"Hello {patient_name}, here is your concise clinical assessment and prescription for headache relief:\n\n"
                            "🩺 **Clinical Assessment:**\n"
                            "• **Tension Headache:** Eye strain, stress, or lack of quality sleep.\n"
                            "• **Dehydration Fatigue:** Fluid deficit triggering cerebral vascular sensitivity.\n\n"
                            "🏠 **Home Supportive Care:**\n"
                            "• Rest in a quiet, dimly lit room; step away from mobile/laptop screens.\n"
                            "• Hydrate with water or electrolyte fluids steadily.\n"
                            "• Apply a cold compress to your forehead or temples.\n\n"
                            "⚠️ **Red Flag Warnings:**\n"
                            "• Sudden explosive headache or accompanying neck stiffness.\n"
                            "• Vision blurring, limb weakness, or confusion.\n\n"
                            "📋 **PRESCRIPTION BOX (Rx):**\n"
                            "| 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| **Paracetamol 500mg (1 Tab)** | Twice a day | After meals with water | 2 - 3 days | Safe pain and tension relief |\n"
                            "| **Oral Rehydration Salts (ORS)** | 1 sachet daily | Dissolved in 1L drinking water | 2 days | Restores vital hydration balance |"
                        )
                    follow_up_questions = ["Is this a migraine?", "Can I take coffee?", "Check my blood pressure"]

                else:
                    # General illness / fever / fatigue
                    ai_response_text = (
                        f"Hello {patient_name}, here is your quick clinical assessment and supportive prescription:\n\n"
                        "🩺 **Clinical Assessment:**\n"
                        "• **Mild Viral or Seasonal Strain:** Everyday fatigue, weather change, or immune reaction.\n"
                        "• **Physical Exhaustion:** Stress and inadequate rest.\n\n"
                        "🏠 **Home Supportive Care:**\n"
                        "• Prioritize 8 hours of uninterrupted rest; avoid strenuous physical exertion.\n"
                        "• Maintain continuous hydration with warm fluids, soups, and water.\n"
                        "• Eat freshly cooked, simple food (khichdi, oats, toast).\n\n"
                        "⚠️ **Red Flag Warnings:**\n"
                        "• High fever (>102°F) not subsiding with medication.\n"
                        "• Breathing difficulty, chest pressure, or extreme lethargy.\n\n"
                        "📋 **PRESCRIPTION BOX (Rx):**\n"
                        "| 💊 Medicine Name & Dose | 🕒 Times a Day (Frequency) | ⏰ When to Take | 📅 How Many Days | 📝 Key Note |\n"
                        "| :--- | :--- | :--- | :--- | :--- |\n"
                        "| **Paracetamol 500mg** | Twice a day | After light food with water | 3 days | For body ache and fever control |\n"
                        "| **Vitamin C + Zinc Chewable** | Once daily | After lunch | 5 days | Supports natural immune recovery |"
                    )
                    follow_up_questions = ["What diet helps fast recovery?", "When should I see a doctor?", "Check safe medications"]

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
            follow_up_questions = ["What food should I avoid?", "How soon will I feel better?", "When should I see a doctor?"]

        lower_resp = (ai_response_text or "").lower()
        if "high risk" in lower_resp or "urgent" in lower_resp or "emergency" in lower_resp:
            risk_category = "HIGH"
        elif "moderate" in lower_resp or "worsen" in lower_resp or "specialist" in lower_resp:
            risk_category = "MODERATE"

        return {
            "message": ai_response_text,
            "risk_category": risk_category,
            "red_flag_alert": 0,
            "disclaimer": f"Medical Guidance Notice: {doctor_display_name} provides clinical triage and educational guidance. It is not an in-person diagnostic examination.",
            "follow_up_questions": follow_up_questions,
            "recommended_specialty": doctor_specialty,
            "ai_provider": ai_provider_used,
            "learned_memory": {
                "allergies": learned_allergies,
                "conditions": learned_conditions
            } if (learned_allergies or learned_conditions) else None
        }
