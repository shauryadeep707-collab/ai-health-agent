import os
import re
import json
import logging
from pathlib import Path
import pypdf
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Standard lab reference range dictionary for common blood and biochemical markers
STANDARD_LAB_DICTIONARY = {
    "hemoglobin": {"unit": "g/dL", "min": 13.0, "max": 17.0, "name": "Hemoglobin (Hb)", "critical_low": 7.0, "critical_high": 20.0},
    "rbc": {"unit": "million/mcL", "min": 4.5, "max": 5.9, "name": "Red Blood Cell Count (RBC)"},
    "wbc": {"unit": "/mcL", "min": 4000.0, "max": 11000.0, "name": "White Blood Cell Count (WBC)", "critical_low": 2000.0, "critical_high": 30000.0},
    "platelet": {"unit": "/mcL", "min": 150000.0, "max": 450000.0, "name": "Platelet Count", "critical_low": 50000.0},
    "total cholesterol": {"unit": "mg/dL", "min": 125.0, "max": 200.0, "name": "Total Cholesterol", "critical_high": 300.0},
    "ldl": {"unit": "mg/dL", "min": 0.0, "max": 100.0, "name": "LDL Cholesterol (Direct)", "critical_high": 190.0},
    "hdl": {"unit": "mg/dL", "min": 40.0, "max": 60.0, "name": "HDL Cholesterol"},
    "triglycerides": {"unit": "mg/dL", "min": 50.0, "max": 150.0, "name": "Triglycerides", "critical_high": 500.0},
    "fasting blood sugar": {"unit": "mg/dL", "min": 70.0, "max": 100.0, "name": "Fasting Blood Glucose", "critical_low": 54.0, "critical_high": 300.0},
    "post prandial": {"unit": "mg/dL", "min": 70.0, "max": 140.0, "name": "Post-Prandial Glucose", "critical_high": 300.0},
    "hba1c": {"unit": "%", "min": 4.0, "max": 5.6, "name": "Glycated Hemoglobin (HbA1c)", "critical_high": 10.0},
    "creatinine": {"unit": "mg/dL", "min": 0.6, "max": 1.2, "name": "Serum Creatinine", "critical_high": 4.0},
    "blood urea": {"unit": "mg/dL", "min": 15.0, "max": 40.0, "name": "Blood Urea Nitrogen (BUN)"},
    "uric acid": {"unit": "mg/dL", "min": 3.5, "max": 7.2, "name": "Serum Uric Acid"},
    "sgpt": {"unit": "U/L", "min": 7.0, "max": 56.0, "name": "ALT (SGPT)"},
    "sgot": {"unit": "U/L", "min": 10.0, "max": 40.0, "name": "AST (SGOT)"},
    "bilirubin": {"unit": "mg/dL", "min": 0.2, "max": 1.2, "name": "Total Bilirubin"},
    "tsh": {"unit": "uIU/mL", "min": 0.4, "max": 4.5, "name": "Thyroid Stimulating Hormone (TSH)"},
    "vitamin d": {"unit": "ng/mL", "min": 30.0, "max": 100.0, "name": "Vitamin D (25-OH)"},
    "vitamin b12": {"unit": "pg/mL", "min": 200.0, "max": 900.0, "name": "Vitamin B12"}
}

class ReportAnalysisService:
    """
    Extracts structured laboratory values from uploaded PDF reports and generates
    safe, non-diagnostic plain English explanations powered by Google Gemini or Ollama.
    """

    @staticmethod
    def extract_text_from_file(file_path: str, file_type: str) -> str:
        """Extracts text content from a PDF or image file."""
        text = ""
        path = Path(file_path)
        if not path.exists():
            return ""

        if "pdf" in file_type.lower() or path.suffix.lower() == ".pdf":
            try:
                reader = pypdf.PdfReader(str(path))
                pages_text = [page.extract_text() or "" for page in reader.pages]
                text = "\n".join(pages_text).strip()
            except Exception as e:
                logger.warning("Error reading PDF with pypdf (%s), attempting text stream extraction.", e)
                try:
                    text = path.read_text(errors="ignore")
                except Exception:
                    pass

        # If no text was extracted (e.g. image without embedded text layer), return empty string
        return text.strip()

    @staticmethod
    def parse_lab_parameters(raw_text: str) -> list[dict]:
        """
        Heuristic regex and dictionary matching to extract laboratory test parameters,
        measured numerical values, units, reference intervals, and flags.
        """
        extracted = []
        lines = raw_text.splitlines()

        # Regular expression for matching "Parameter Name ... Value ... Unit ... Range"
        pattern = re.compile(
            r"([A-Za-z\s\(\)\/\-\+0-9]{3,35})\s+([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z\/\%mcLdLuIU]+)?\s*(?:(?:([0-9]+(?:\.[0-9]+)?)\s*[\-\–]\s*([0-9]+(?:\.[0-9]+)?))|(?:\<\s*([0-9]+(?:\.[0-9]+)?))|(?:\>\s*([0-9]+(?:\.[0-9]+)?)))?",
            re.IGNORECASE
        )

        seen_keys = set()

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 5:
                continue

            # Check against standard lab dictionary
            lower_line = line_str.lower()
            for key, dict_info in STANDARD_LAB_DICTIONARY.items():
                if key in lower_line and key not in seen_keys:
                    # Search for numerical value on this line
                    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", line_str)
                    if numbers:
                        val = float(numbers[0])
                        unit = dict_info.get("unit", "")
                        ref_min = dict_info.get("min", 0.0)
                        ref_max = dict_info.get("max", 0.0)
                        ref_text = f"{ref_min} - {ref_max} {unit}"

                        # Determine flag
                        flag = "NORMAL"
                        if "critical_low" in dict_info and val <= dict_info["critical_low"]:
                            flag = "CRITICAL"
                        elif "critical_high" in dict_info and val >= dict_info["critical_high"]:
                            flag = "CRITICAL"
                        elif val < ref_min:
                            flag = "LOW"
                        elif val > ref_max:
                            flag = "HIGH"

                        extracted.append({
                            "parameter_name": dict_info["name"],
                            "measured_value": val,
                            "measured_text": str(val),
                            "unit": unit,
                            "ref_range_min": ref_min,
                            "ref_range_max": ref_max,
                            "ref_range_text": ref_text,
                            "flag": flag
                        })
                        seen_keys.add(key)
                        break

        # Return empty list if no genuine clinical lab parameters matched
        return extracted

    @staticmethod
    def generate_ai_explanation(test_values: list[dict], original_filename: str) -> dict:
        """
        Sends extracted parameters to AI model (Gemini / Ollama / Fallback) to create a plain English summary,
        abnormal counts, urgent flags, and clear non-diagnostic medical disclaimers.
        If no lab parameters were detected, returns an honest validation advisory.
        """
        if not test_values:
            return {
                "ai_provider": "Clinical Diagnostic Validator",
                "summary_plain_en": (
                    "⚠️ **No Diagnostic Laboratory Parameters Detected**\n\n"
                    "The system did not detect any standard laboratory test values (such as Blood Glucose, Hemoglobin, Lipid Panel, or Creatinine) in this uploaded file.\n\n"
                    "**Guidance:**\n"
                    "• Ensure the uploaded document is a genuine laboratory or pathology test report.\n"
                    "• If uploading an image or scan, ensure the text and numbers are sharp, upright, and clearly legible.\n"
                    "• Digital PDF reports directly from diagnostic laboratories yield the highest extraction accuracy."
                ),
                "clinical_notes": "Non-diagnostic or unreadable image uploaded. No clinical parameters extracted.",
                "abnormal_count": 0,
                "urgent_flags": None,
                "risk_level": "LOW",
                "recommendations": "Please upload a clear PDF or photo of an official diagnostic lab report."
            }

        abnormal_items = [v for v in test_values if v.get("flag") in ("LOW", "HIGH", "CRITICAL")]
        critical_items = [v for v in test_values if v.get("flag") == "CRITICAL"]

        abnormal_count = len(abnormal_items)
        risk_level = "EMERGENCY" if critical_items else ("HIGH" if abnormal_count >= 3 else ("MODERATE" if abnormal_count > 0 else "LOW"))

        # Build prompt for AI provider
        extracted_summary_text = "\n".join([
            f"- {v['parameter_name']}: {v['measured_value']} {v['unit']} (Ref: {v['ref_range_text']}) -> {v['flag']}"
            for v in test_values
        ])

        system_instruction = (
            "You are a compassionate medical information assistant. Explain the following laboratory report "
            "in simple, reassuring English. "
            "CRITICAL MEDICAL SAFETY REQUIREMENTS:\n"
            "1. Explain what each out-of-range value means in simple terms.\n"
            "2. EXPLICITLY state that abnormal test results do NOT automatically establish a medical diagnosis.\n"
            "3. Do not invent diagnoses, medications, or specific dosages.\n"
            "4. If any values are critical, advise immediate emergency care.\n"
            "5. Advise the patient to consult their qualified treating physician for full clinical interpretation."
        )

        ai_response_text = None
        ai_provider_used = "Rule-based Clinical Engine"

        # 1. Try Gemini if configured
        if Config.AI_PROVIDER == "gemini" and Config.GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": f"{system_instruction}\n\nReport Filename: {original_filename}\nExtracted Lab Values:\n{extracted_summary_text}"}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
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
                logger.warning("Gemini API call failed (%s). Falling back to clinical rules engine.", e)

        # 2. Try Ollama if configured
        elif Config.AI_PROVIDER == "ollama":
            try:
                ollama_url = f"{Config.OLLAMA_BASE_URL}/api/generate"
                payload = {
                    "model": Config.OLLAMA_MODEL,
                    "prompt": f"{system_instruction}\n\nExtracted Values:\n{extracted_summary_text}",
                    "stream": False
                }
                res = requests.post(ollama_url, json=payload, timeout=15)
                if res.status_code == 200:
                    ai_response_text = res.json().get("response")
                    ai_provider_used = f"Ollama ({Config.OLLAMA_MODEL})"
            except Exception as e:
                logger.warning("Ollama call failed (%s). Falling back to clinical rules engine.", e)

        # 3. Clinical Rules Engine Fallback (Deterministic, Safe, Always Available)
        if not ai_response_text:
            abnormal_descriptions = []
            for item in abnormal_items:
                direction = "elevated (above reference range)" if item["flag"] == "HIGH" else "below normal reference limits"
                abnormal_descriptions.append(
                    f"• {item['parameter_name']} is currently measured at {item['measured_value']} {item['unit']}, which is {direction}."
                )

            if abnormal_descriptions:
                summary = (
                    f"Your medical report has been processed. Of the {len(test_values)} parameters analyzed, "
                    f"{len(abnormal_items)} parameter(s) are outside standard laboratory reference intervals:\n\n"
                    + "\n".join(abnormal_descriptions)
                    + "\n\n"
                    "IMPORTANT HEALTH NOTE:\n"
                    "Laboratory values can fluctuate due to hydration, diet, stress, time of day, and recent physical exertion. "
                    "An abnormal result does NOT automatically establish a disease or diagnosis. "
                    "These findings should be evaluated by your healthcare provider in conjunction with your personal clinical history."
                )
            else:
                summary = (
                    f"Good news! All {len(test_values)} tested parameters in this report are currently within their standard laboratory reference intervals. "
                    "Remember that normal lab results should still be viewed in the context of your overall physical well-being. "
                    "Maintain routine wellness checkups and discuss any persistent symptoms with your doctor."
                )
            ai_response_text = summary

        urgent_flags = ""
        if critical_items:
            urgent_flags = "URGENT WARNING: One or more parameters are at critical clinical thresholds. Seek urgent medical attention or visit an emergency department."
        elif abnormal_count > 0:
            urgent_flags = "Mild-to-moderate variance noted. Non-emergency physician follow-up recommended."
        else:
            urgent_flags = "No critical alerts identified."

        recommendations = (
            "1. Schedule a consultation with a registered doctor to discuss these findings in clinical context.\n"
            "2. Do not start, discontinue, or alter dosages of any medication without professional guidance.\n"
            "3. If you experience acute symptoms (e.g. chest pain, breathing difficulty, dizziness), seek immediate emergency care."
        )

        return {
            "ai_provider": ai_provider_used,
            "summary_plain_en": ai_response_text,
            "clinical_notes": f"Analyzed {len(test_values)} parameters. Found {abnormal_count} out-of-range parameters.",
            "abnormal_count": abnormal_count,
            "urgent_flags": urgent_flags,
            "risk_level": risk_level,
            "recommendations": recommendations
        }
