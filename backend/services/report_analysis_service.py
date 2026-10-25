import os
import re
import json
import base64
import logging
from pathlib import Path
import pypdf
import requests
from backend.config import Config

logger = logging.getLogger(__name__)

# Comprehensive lab reference range dictionary covering all major pathology disciplines:
# Hematology (CBC), Biochemistry, Renal, Liver, Lipid, Diabetic, Thyroid, Vitamins, and Urine Analysis
STANDARD_LAB_DICTIONARY = {
    # 1. Hematology / Complete Blood Count (CBC)
    "hemoglobin": {"unit": "g/dL", "min": 13.0, "max": 17.0, "name": "Hemoglobin (Hb)", "critical_low": 7.0, "critical_high": 20.0},
    "rbc": {"unit": "million/mcL", "min": 4.5, "max": 5.9, "name": "Red Blood Cell Count (RBC)"},
    "wbc": {"unit": "/mcL", "min": 4000.0, "max": 11000.0, "name": "White Blood Cell Count (WBC)", "critical_low": 2000.0, "critical_high": 30000.0},
    "tlc": {"unit": "/mcL", "min": 4000.0, "max": 11000.0, "name": "Total Leukocyte Count (TLC)"},
    "platelet": {"unit": "/mcL", "min": 150000.0, "max": 450000.0, "name": "Platelet Count", "critical_low": 50000.0},
    "pcv": {"unit": "%", "min": 40.0, "max": 50.0, "name": "Packed Cell Volume (PCV / Hematocrit)"},
    "mcv": {"unit": "fL", "min": 80.0, "max": 100.0, "name": "Mean Corpuscular Volume (MCV)"},
    "mch": {"unit": "pg", "min": 27.0, "max": 33.0, "name": "Mean Corpuscular Hemoglobin (MCH)"},
    "mchc": {"unit": "g/dL", "min": 32.0, "max": 36.0, "name": "MCHC"},
    "esr": {"unit": "mm/hr", "min": 0.0, "max": 20.0, "name": "Erythrocyte Sedimentation Rate (ESR)"},
    "neutrophils": {"unit": "%", "min": 40.0, "max": 75.0, "name": "Neutrophils"},
    "lymphocytes": {"unit": "%", "min": 20.0, "max": 45.0, "name": "Lymphocytes"},
    "eosinophils": {"unit": "%", "min": 1.0, "max": 6.0, "name": "Eosinophils"},
    "monocytes": {"unit": "%", "min": 2.0, "max": 10.0, "name": "Monocytes"},

    # 2. Lipid Profile
    "total cholesterol": {"unit": "mg/dL", "min": 125.0, "max": 200.0, "name": "Total Cholesterol", "critical_high": 300.0},
    "ldl": {"unit": "mg/dL", "min": 0.0, "max": 100.0, "name": "LDL Cholesterol (Direct)", "critical_high": 190.0},
    "hdl": {"unit": "mg/dL", "min": 40.0, "max": 60.0, "name": "HDL Cholesterol"},
    "triglycerides": {"unit": "mg/dL", "min": 50.0, "max": 150.0, "name": "Triglycerides", "critical_high": 500.0},
    "vldl": {"unit": "mg/dL", "min": 5.0, "max": 30.0, "name": "VLDL Cholesterol"},

    # 3. Diabetic Profile
    "fasting blood sugar": {"unit": "mg/dL", "min": 70.0, "max": 100.0, "name": "Fasting Blood Glucose", "critical_low": 54.0, "critical_high": 300.0},
    "post prandial": {"unit": "mg/dL", "min": 70.0, "max": 140.0, "name": "Post-Prandial Glucose", "critical_high": 300.0},
    "random blood sugar": {"unit": "mg/dL", "min": 70.0, "max": 140.0, "name": "Random Blood Glucose", "critical_high": 300.0},
    "hba1c": {"unit": "%", "min": 4.0, "max": 5.6, "name": "Glycated Hemoglobin (HbA1c)", "critical_high": 10.0},

    # 4. Renal / Kidney Function (KFT / RFT)
    "creatinine": {"unit": "mg/dL", "min": 0.6, "max": 1.2, "name": "Serum Creatinine", "critical_high": 4.0},
    "blood urea": {"unit": "mg/dL", "min": 15.0, "max": 40.0, "name": "Blood Urea Nitrogen (BUN)"},
    "uric acid": {"unit": "mg/dL", "min": 3.5, "max": 7.2, "name": "Serum Uric Acid"},
    "sodium": {"unit": "mEq/L", "min": 135.0, "max": 145.0, "name": "Serum Sodium", "critical_low": 120.0, "critical_high": 160.0},
    "potassium": {"unit": "mEq/L", "min": 3.5, "max": 5.1, "name": "Serum Potassium", "critical_low": 2.8, "critical_high": 6.2},
    "calcium": {"unit": "mg/dL", "min": 8.5, "max": 10.5, "name": "Serum Calcium"},

    # 5. Liver Function (LFT)
    "sgpt": {"unit": "U/L", "min": 7.0, "max": 56.0, "name": "ALT (SGPT)", "critical_high": 300.0},
    "alt": {"unit": "U/L", "min": 7.0, "max": 56.0, "name": "ALT (SGPT)", "critical_high": 300.0},
    "sgot": {"unit": "U/L", "min": 10.0, "max": 40.0, "name": "AST (SGOT)", "critical_high": 300.0},
    "ast": {"unit": "U/L", "min": 10.0, "max": 40.0, "name": "AST (SGOT)", "critical_high": 300.0},
    "bilirubin": {"unit": "mg/dL", "min": 0.2, "max": 1.2, "name": "Total Bilirubin", "critical_high": 12.0},
    "direct bilirubin": {"unit": "mg/dL", "min": 0.0, "max": 0.3, "name": "Direct Bilirubin"},
    "alkaline phosphatase": {"unit": "U/L", "min": 44.0, "max": 147.0, "name": "Alkaline Phosphatase (ALP)"},
    "total protein": {"unit": "g/dL", "min": 6.0, "max": 8.3, "name": "Total Serum Protein"},
    "albumin": {"unit": "g/dL", "min": 3.5, "max": 5.0, "name": "Serum Albumin"},

    # 6. Thyroid Function (TFT)
    "tsh": {"unit": "uIU/mL", "min": 0.4, "max": 4.5, "name": "Thyroid Stimulating Hormone (TSH)", "critical_high": 20.0},
    "t3": {"unit": "ng/dL", "min": 80.0, "max": 200.0, "name": "Total Triiodothyronine (T3)"},
    "t4": {"unit": "ug/dL", "min": 4.5, "max": 12.0, "name": "Total Thyroxine (T4)"},

    # 7. Vitamins & Minerals
    "vitamin d": {"unit": "ng/mL", "min": 30.0, "max": 100.0, "name": "Vitamin D (25-OH)", "critical_low": 10.0},
    "vitamin b12": {"unit": "pg/mL", "min": 200.0, "max": 900.0, "name": "Vitamin B12", "critical_low": 100.0},
    "ferritin": {"unit": "ng/mL", "min": 20.0, "max": 250.0, "name": "Serum Ferritin"},

    # 8. Urine Routine & Microscopy (Clinical Pathology)
    "pus cells": {"unit": "Cells/hpf", "min": 0.0, "max": 5.0, "name": "Pus Cells (WBC in Urine)", "critical_high": 100.0},
    "epithelial cells": {"unit": "Cells/hpf", "min": 0.0, "max": 5.0, "name": "Epithelial Cells"},
    "r.b.c": {"unit": "Cells/hpf", "min": 0.0, "max": 3.0, "name": "Urine Red Blood Cells (RBCs)"},
    "red blood cells": {"unit": "Cells/hpf", "min": 0.0, "max": 3.0, "name": "Urine Red Blood Cells (RBCs)"},
    "specific gravity": {"unit": "", "min": 1.000, "max": 1.030, "name": "Specific Gravity"},
    "ph": {"unit": "", "min": 5.0, "max": 8.0, "name": "Urine pH"},
    "protein": {"unit": "", "min": 0.0, "max": 0.0, "name": "Urine Protein / Albumin"},
    "nitrite": {"unit": "", "min": 0.0, "max": 0.0, "name": "Urine Nitrite"},
    "leucocytes": {"unit": "", "min": 0.0, "max": 0.0, "name": "Urine Leucocytes"},
    "bacteria": {"unit": "", "min": 0.0, "max": 0.0, "name": "Urine Bacteria"}
}

FALLBACK_GEMINI_MODELS = list(dict.fromkeys([
    Config.GEMINI_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]))


class ReportAnalysisService:
    """
    Universal clinical laboratory data extraction and plain English explanatory service.
    Works seamlessly across ANY medical report (Blood, Urine, Liver, Kidney, Thyroid,
    Lipid, Diabetic, Vitamin, etc.) in PDF or Image format using Multimodal AI with
    deterministic clinical rule-engine fallbacks.
    """

    @staticmethod
    def extract_report_title(ocr_text: str) -> str:
        """
        Extracts the genuine medical test/investigation title from report text
        (e.g., 'URINE COMPLETE (ROUTINE & MICROSCOPY)', 'COMPLETE BLOOD COUNT (CBC)',
        'LIVER FUNCTION TEST (LFT)', 'LIPID PROFILE', etc.).
        """
        if not ocr_text:
            return "Diagnostic Lab Report"

        # Explicit known test patterns
        known_titles = [
            (r'URINE\s+COMPLETE\s*[\(\[]?.*?(?:ROUTINE|MICROSCOPY)[\)\]]?', "Urine Complete (Routine & Microscopy)"),
            (r'URINE\s+(?:ROUTINE|ANALYSIS|EXAMINATION)', "Urine Routine Analysis"),
            (r'COMPLETE\s+BLOOD\s+COUNT(?:\s*\(CBC\))?', "Complete Blood Count (CBC)"),
            (r'\bCBC\b', "Complete Blood Count (CBC)"),
            (r'LIVER\s+FUNCTION\s+TEST(?:\s*\(LFT\))?', "Liver Function Test (LFT)"),
            (r'\bLFT\b', "Liver Function Test (LFT)"),
            (r'KIDNEY\s+FUNCTION\s+TEST|RENAL\s+FUNCTION\s+TEST', "Kidney Function Test (KFT/RFT)"),
            (r'\b(?:KFT|RFT)\b', "Kidney Function Test (KFT/RFT)"),
            (r'LIPID\s+PROFILE|CHOLESTEROL\s+PANEL', "Lipid Profile"),
            (r'THYROID\s+(?:PROFILE|PANEL|FUNCTION\s+TEST)', "Thyroid Profile (T3, T4, TSH)"),
            (r'\b(?:TSH|TFT)\b', "Thyroid Function Test"),
            (r'GLUCOSE\s+TOLERANCE|HBA1C|DIABETIC\s+PANEL|BLOOD\s+SUGAR', "Diabetic & Glucose Profile"),
            (r'ELECTROLYTE\s+(?:PANEL|PROFILE)', "Serum Electrolytes"),
            (r'VITAMIN\s+D|VITAMIN\s+B12', "Vitamin Profile"),
            (r'STOOL\s+(?:ROUTINE|EXAMINATION)', "Stool Routine Examination"),
            (r'CLINICAL\s+PATHOLOGY', "Clinical Pathology Report"),
            (r'BIOCHEMISTRY\s+REPORT', "Biochemistry Report")
        ]

        for pattern, friendly_title in known_titles:
            if re.search(pattern, ocr_text, re.IGNORECASE):
                return friendly_title

        # Heuristic header pattern matching: "INVESTIGATION / TEST NAME: XYZ"
        match = re.search(r'(?:Investigation|Test\s*Name|Profile|Panel)\s*[:\-]\s*([A-Za-z0-9\s\(\)\&\-\/]{4,50})', ocr_text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()

        return "Diagnostic Lab Report"

    @staticmethod
    def extract_report_date(ocr_text: str) -> str:
        """Extracts report test date from lab text (e.g. 2026-10-25 or 15/10/2026 or 15-Oct-2026)."""
        if not ocr_text:
            return ""
        date_patterns = [
            r'(?:Date\s*(?:of\s*Collection|Collected|Reported|of\s*Test)?|Test\s*Date|Specimen\s*Date|Sample\s*Date)\s*[:\-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(?:Date\s*(?:of\s*Collection|Collected|Reported|of\s*Test)?|Test\s*Date|Specimen\s*Date|Sample\s*Date)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?:Date\s*(?:of\s*Collection|Collected|Reported|of\s*Test)?|Test\s*Date)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})',
            r'\b(\d{4}-\d{2}-\d{2})\b',
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                raw_d = match.group(1).strip()
                try:
                    from datetime import datetime
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d %B %Y"):
                        try:
                            dt = datetime.strptime(raw_d, fmt)
                            return dt.strftime("%Y-%m-%d")
                        except ValueError:
                            pass
                except Exception:
                    pass
                return raw_d
        return ""

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

        return text.strip()

    @staticmethod
    def parse_lab_parameters(raw_text: str) -> list[dict]:
        """
        Deterministic regex and dictionary matching to extract laboratory test parameters,
        numerical values, qualitative statuses (1+, Positive, Negative), and out-of-range flags.
        """
        extracted = []
        lines = raw_text.splitlines()
        seen_keys = set()

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 3:
                continue

            lower_line = line_str.lower()
            for key, dict_info in STANDARD_LAB_DICTIONARY.items():
                if key in lower_line and key not in seen_keys:
                    unit = dict_info.get("unit", "")
                    ref_min = dict_info.get("min", 0.0)
                    ref_max = dict_info.get("max", 0.0)
                    ref_text = f"{ref_min} - {ref_max} {unit}".strip()

                    # Check for qualitative markers (e.g. 1+, 2+, 3+, Positive, Negative, Present)
                    qual_match = re.search(r'\b([1-4]\+|positive|negative|present|absent|normal)\b', lower_line)
                    range_match = re.search(r'\b(\d+\s*[\-\–]\s*\d+)\b', line_str)
                    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", line_str)

                    val = None
                    val_text = ""
                    flag = "NORMAL"

                    if range_match:
                        val_text = range_match.group(1).replace(" ", "")
                        # e.g., 250-300 Pus Cells -> parse upper bound
                        parts = val_text.split("-")
                        try:
                            upper = float(parts[-1])
                            val = upper
                            if upper > ref_max:
                                flag = "CRITICAL" if upper >= (dict_info.get("critical_high") or 50.0) else "HIGH"
                        except Exception:
                            pass
                    elif numbers:
                        val = float(numbers[0])
                        val_text = str(val)
                        if "critical_low" in dict_info and val <= dict_info["critical_low"]:
                            flag = "CRITICAL"
                        elif "critical_high" in dict_info and val >= dict_info["critical_high"]:
                            flag = "CRITICAL"
                        elif ref_max > 0 and val < ref_min:
                            flag = "LOW"
                        elif ref_max > 0 and val > ref_max:
                            flag = "HIGH"
                    elif qual_match:
                        val_text = qual_match.group(1).title()
                        if val_text in ("1+", "2+", "3+", "4+", "Positive", "Present"):
                            flag = "HIGH"
                        else:
                            flag = "NORMAL"

                    if val_text:
                        extracted.append({
                            "parameter_name": dict_info["name"],
                            "measured_value": val,
                            "measured_text": val_text,
                            "unit": unit,
                            "ref_range_min": ref_min,
                            "ref_range_max": ref_max,
                            "ref_range_text": ref_text,
                            "flag": flag
                        })
                        seen_keys.add(key)
                        break

        return extracted

    @classmethod
    def analyze_report_comprehensive(
        cls,
        file_path: str,
        file_type: str,
        original_filename: str,
        user_test_type: str = "",
        user_report_date: str = ""
    ) -> dict:
        """
        Universal comprehensive report analyzer.
        1. Employs Gemini Multimodal Vision / Language API to extract Title, Date, Lab,
           and structured lab values directly from images or documents.
        2. Falls back seamlessly to offline deterministic rule-engine and regex parser.
        """
        is_image = any(img_ext in file_type.lower() for img_ext in ("jpg", "jpeg", "png", "webp", "image")) or \
                   Path(file_path).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")

        extracted_text = ""
        if not is_image:
            extracted_text = cls.extract_text_from_file(file_path, file_type)

        # -------------------------------------------------------------
        # STEP 1: Attempt Multimodal AI Extraction (Gemini)
        # -------------------------------------------------------------
        if Config.AI_PROVIDER == "gemini" and Config.GEMINI_API_KEY:
            ai_data = cls._call_gemini_multimodal(
                file_path=file_path,
                file_type=file_type,
                is_image=is_image,
                pdf_text=extracted_text,
                original_filename=original_filename
            )
            if ai_data:
                detected_title = user_test_type or ai_data.get("detected_title") or cls.extract_report_title(extracted_text)
                detected_date = user_report_date or ai_data.get("test_date") or cls.extract_report_date(extracted_text)
                return {
                    "detected_title": detected_title,
                    "lab_name": ai_data.get("lab_name", ""),
                    "test_date": detected_date,
                    "extracted_text": ai_data.get("extracted_text") or extracted_text,
                    "parameters": ai_data.get("parameters", []),
                    "ai_analysis": {
                        "ai_provider": ai_data.get("ai_provider", "Google Gemini"),
                        "summary_plain_en": ai_data.get("summary_plain_en", ""),
                        "clinical_notes": ai_data.get("clinical_notes", ""),
                        "abnormal_count": ai_data.get("abnormal_count", 0),
                        "urgent_flags": ai_data.get("urgent_flags", "No critical alerts identified."),
                        "risk_level": ai_data.get("risk_level", "LOW"),
                        "recommendations": ai_data.get("recommendations", "")
                    }
                }

        # -------------------------------------------------------------
        # STEP 2: Rule-Based Fallback Engine (Offline / Local)
        # -------------------------------------------------------------
        detected_title = user_test_type or cls.extract_report_title(extracted_text) or "Diagnostic Lab Report"
        detected_date = user_report_date or cls.extract_report_date(extracted_text) or None
        test_values = cls.parse_lab_parameters(extracted_text)
        explanation = cls.generate_ai_explanation(test_values, original_filename)

        return {
            "detected_title": detected_title,
            "lab_name": "",
            "test_date": detected_date,
            "extracted_text": extracted_text,
            "parameters": test_values,
            "ai_analysis": explanation
        }

    @classmethod
    def _call_gemini_multimodal(
        cls,
        file_path: str,
        file_type: str,
        is_image: bool,
        pdf_text: str,
        original_filename: str
    ) -> dict | None:
        """Calls Gemini with structured schema to extract parameters from image or text."""
        parts = []

        system_prompt = (
            "You are an expert clinical laboratory data extraction engine. "
            "Analyze this medical lab report document (image or text). "
            "Return ONLY valid JSON matching this exact structure without markdown backticks:\n"
            "{\n"
            '  "detected_title": "Official Test Title (e.g. Urine Complete (Routine & Microscopy), Complete Blood Count (CBC), Lipid Profile, Liver Function Test, etc.)",\n'
            '  "lab_name": "Hospital or laboratory name if visible, else empty string",\n'
            '  "test_date": "Test date in YYYY-MM-DD if visible, else empty string",\n'
            '  "extracted_text": "Clean textual transcription of the test parameters and findings",\n'
            '  "parameters": [\n'
            '    {\n'
            '      "parameter_name": "Name of parameter (e.g. Hemoglobin, Pus Cells, Creatinine, Protein)",\n'
            '      "measured_value": 0.0,\n'
            '      "measured_text": "Exact string (e.g. 14.2, 250-300, 1+, Negative)",\n'
            '      "unit": "Unit (e.g. mg/dL, Cells/hpf, % or empty)",\n'
            '      "ref_range_min": null,\n'
            '      "ref_range_max": null,\n'
            '      "ref_range_text": "Reference interval string",\n'
            '      "flag": "NORMAL or HIGH or LOW or CRITICAL"\n'
            '    }\n'
            '  ],\n'
            '  "summary_plain_en": "Compassionate, patient-friendly explanation in plain English highlighting normal vs abnormal findings, reassurance, and practical health notes.",\n'
            '  "clinical_notes": "Concise summary for clinical review",\n'
            '  "risk_level": "LOW or MODERATE or HIGH",\n'
            '  "abnormal_count": 0,\n'
            '  "urgent_flags": "Warning text if critical, else No critical alerts identified.",\n'
            '  "recommendations": "Actionable next steps (hydration, doctor consultation, etc.)"\n'
            "}"
        )

        parts.append({"text": system_prompt})

        if is_image:
            try:
                mime = "image/jpeg"
                if "png" in file_type.lower() or file_path.lower().endswith(".png"):
                    mime = "image/png"
                elif "webp" in file_type.lower() or file_path.lower().endswith(".webp"):
                    mime = "image/webp"

                with open(file_path, "rb") as f:
                    b64_content = base64.b64encode(f.read()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": mime, "data": b64_content}})
            except Exception as e:
                logger.warning("Could not read image file for Gemini: %s", e)
                return None
        else:
            if not pdf_text:
                return None
            parts.append({"text": f"Document Filename: {original_filename}\nReport Text Content:\n{pdf_text}"})

        # Try models in fallback order
        for model in FALLBACK_GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={Config.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
            }
            try:
                res = requests.post(url, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        c_parts = candidates[0]["content"].get("parts", [])
                        if c_parts:
                            raw_json = c_parts[0].get("text", "").strip()
                            # Clean possible code fence
                            raw_json = re.sub(r"^```(?:json)?", "", raw_json).rstrip("`").strip()
                            parsed = json.loads(raw_json)
                            parsed["ai_provider"] = f"Google Gemini ({model})"

                            # Ensure numerical values match schema
                            for param in parsed.get("parameters", []):
                                if param.get("measured_value") is not None:
                                    try:
                                        param["measured_value"] = float(param["measured_value"])
                                    except Exception:
                                        param["measured_value"] = None
                            return parsed
                else:
                    logger.warning("Gemini model %s returned status %s: %s", model, res.status_code, res.text[:200])
            except Exception as e:
                logger.warning("Gemini model %s exception: %s", model, e)

        return None

    @staticmethod
    def generate_ai_explanation(test_values: list[dict], original_filename: str) -> dict:
        """
        Sends extracted parameters to AI model or rule engine to create a plain English summary.
        """
        if not test_values:
            return {
                "ai_provider": "Clinical Diagnostic Validator",
                "summary_plain_en": (
                    "⚠️ **No Diagnostic Laboratory Parameters Detected**\n\n"
                    "The system did not detect any standard laboratory test values in this uploaded file.\n\n"
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

        abnormal_descriptions = []
        for item in abnormal_items:
            direction = "elevated (above reference range)" if item.get("flag") == "HIGH" else ("at critical threshold" if item.get("flag") == "CRITICAL" else "below normal reference limits")
            abnormal_descriptions.append(
                f"• {item['parameter_name']} is currently measured at {item.get('measured_text', item.get('measured_value'))} {item.get('unit', '')}, which is {direction}."
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
            "3. If you experience acute symptoms (e.g. fever, acute pain, dizziness), seek immediate medical care."
        )

        return {
            "ai_provider": "Rule-based Clinical Engine",
            "summary_plain_en": summary,
            "clinical_notes": f"Analyzed {len(test_values)} parameters. Found {abnormal_count} out-of-range parameters.",
            "abnormal_count": abnormal_count,
            "urgent_flags": urgent_flags,
            "risk_level": risk_level,
            "recommendations": recommendations
        }
