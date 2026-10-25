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
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    Config.GEMINI_MODEL,
    "gemini-3.8-flash"
]))


class ReportAnalysisService:
    """
    Universal clinical laboratory data extraction and plain English explanatory service.
    Works seamlessly across ANY medical report (Blood, Urine, Liver, Kidney, Thyroid,
    Lipid, Diabetic, Vitamin, etc.) in PDF or Image format using Multimodal AI with
    deterministic clinical rule-engine fallbacks.
    """

    @staticmethod
    def is_generic_title(title: str) -> bool:
        """Returns True if the given title is empty, generic, or an auto-detect placeholder."""
        if not title:
            return True
        t = title.strip().lower()
        generic_phrases = (
            "general lab report", "general diagnostic lab report", "diagnostic lab report",
            "diagnostic report", "comprehensive diagnostic report", "auto-detect", "✨",
            "investigation report", "lab report", "pathology report", "clinical laboratory report"
        )
        if any(p in t for p in generic_phrases) and not any(k in t for k in ("urine", "blood", "cbc", "lipid", "liver", "lft", "kidney", "kft", "rft", "thyroid", "glucose", "diabetic")):
            return True
        return False

    @staticmethod
    def infer_title_from_parameters(parameters: list[dict]) -> str:
        """
        Infers the exact clinical investigation title from extracted parameter names
        with 100% deterministic pathology confidence.
        """
        if not parameters:
            return ""
        names = []
        for p in parameters:
            if isinstance(p, dict):
                names.append(str(p.get("parameter_name", "")).lower())
            elif isinstance(p, str):
                names.append(p.lower())
        combined = " ".join(names)

        if any(k in combined for k in ("pus cells", "epithelial cells", "urine protein", "specific gravity", "leucocytes", "crystals")):
            return "Urine Complete (Routine & Microscopy)"
        if any(k in combined for k in ("hemoglobin", "platelet", "rbc", "wbc", "tlc", "pcv", "neutrophil", "lymphocyte")):
            return "Complete Blood Count (CBC)"
        if any(k in combined for k in ("cholesterol", "triglyceride", "hdl", "ldl", "vldl")):
            return "Comprehensive Lipid Profile"
        if any(k in combined for k in ("sgpt", "sgot", "bilirubin", "alt", "ast", "alkaline phosphatase")):
            return "Liver Function Test (LFT)"
        if any(k in combined for k in ("creatinine", "blood urea", "uric acid", "bun")):
            return "Kidney Function Test (KFT/RFT)"
        if any(k in combined for k in ("tsh", "t3", "t4", "thyroid")):
            return "Thyroid Profile (T3, T4, TSH)"
        if any(k in combined for k in ("hba1c", "fasting blood sugar", "glucose", "post prandial")):
            return "Diabetic & Glucose Profile"
        if any(k in combined for k in ("vitamin d", "vitamin b12", "ferritin")):
            return "Vitamin & Micronutrient Profile"
        return ""

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

        GENERIC_LABELS = {
            "", "general lab report", "general diagnostic lab report",
            "comprehensive diagnostic report", "diagnostic lab report",
            "diagnostic report", "✨ auto-detect test title from document",
            "✨ auto-detect investigation title from document"
        }

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
                ai_title = (ai_data.get("detected_title") or "").strip()
                ai_params = ai_data.get("parameters", [])
                inferred_title = cls.infer_title_from_parameters(ai_params) or cls.extract_report_title(ai_data.get("extracted_text") or extracted_text)

                if cls.is_generic_title(user_test_type):
                    detected_title = (ai_title if not cls.is_generic_title(ai_title) else "") or inferred_title or ai_title or "Diagnostic Lab Report"
                else:
                    detected_title = user_test_type or (ai_title if not cls.is_generic_title(ai_title) else "") or inferred_title or "Diagnostic Lab Report"

                detected_date = user_report_date or ai_data.get("test_date") or cls.extract_report_date(extracted_text)
                return {
                    "detected_title": detected_title,
                    "lab_name": ai_data.get("lab_name", ""),
                    "test_date": detected_date,
                    "extracted_text": ai_data.get("extracted_text") or extracted_text,
                    "parameters": ai_params,
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
        test_values = cls.parse_lab_parameters(extracted_text)
        inferred_fallback = cls.infer_title_from_parameters(test_values) or cls.extract_report_title(extracted_text)
        if cls.is_generic_title(user_test_type):
            detected_title = inferred_fallback or "Diagnostic Lab Report"
        else:
            detected_title = user_test_type or inferred_fallback or "Diagnostic Lab Report"

        detected_date = user_report_date or cls.extract_report_date(extracted_text) or None
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
            "You are an expert clinical laboratory pathologist and data extraction engine. "
            "Analyze this medical lab report document (image or text). "
            "Return ONLY valid JSON matching this exact structure without markdown backticks:\n"
            "{\n"
            '  "detected_title": "Accurate Medical Investigation Title (e.g. Urine Complete (Routine & Microscopy), Complete Blood Count (CBC), Comprehensive Lipid Profile, Liver Function Test (LFT), Kidney Function Test (KFT), etc.)",\n'
            '  "lab_name": "Hospital or laboratory name if visible, else empty string",\n'
            '  "test_date": "Test date in YYYY-MM-DD if visible, else empty string",\n'
            '  "extracted_text": "Clean textual transcription of the test parameters, findings, and impressions",\n'
            '  "parameters": [\n'
            '    {\n'
            '      "parameter_name": "Name of parameter (e.g. Hemoglobin, Pus Cells, Creatinine, Total Cholesterol)",\n'
            '      "measured_value": 0.0,\n'
            '      "measured_text": "Exact string (e.g. 14.2, 250-300, 1+, Negative)",\n'
            '      "unit": "Unit (e.g. mg/dL, Cells/hpf, % or empty)",\n'
            '      "ref_range_min": null,\n'
            '      "ref_range_max": null,\n'
            '      "ref_range_text": "Reference interval string",\n'
            '      "flag": "NORMAL or HIGH or LOW or CRITICAL"\n'
            '    }\n'
            '  ],\n'
            '  "summary_plain_en": "A clear, empathetic, and thorough explanation in plain language. Must include: (1) What test was performed and its purpose, (2) Highlights of key normal parameters and any out-of-range/elevated parameters with their values, (3) A clear, reassuring explanation of what the abnormal findings typically suggest, (4) Reassurance that single lab results fluctuate and require physician review, and (5) Practical wellness guidance.",\n'
            '  "clinical_notes": "Concise summary for clinical review highlighting significant pathology markers",\n'
            '  "risk_level": "LOW or MODERATE or HIGH",\n'
            '  "abnormal_count": 0,\n'
            '  "urgent_flags": "Warning text if critical thresholds reached, else No critical alerts identified.",\n'
            '  "recommendations": "Actionable next steps (e.g. consult primary physician, adequate hydration, follow-up testing)"\n'
            "}"
        )

        parts.append({"text": system_prompt})

        if is_image:
            try:
                import io
                from PIL import Image, ImageOps

                with Image.open(file_path) as im:
                    im = ImageOps.exif_transpose(im)
                    im = im.convert("RGB")
                    im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=85, optimize=True)
                    opt_bytes = buf.getvalue()

                b64_content = base64.b64encode(opt_bytes).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_content}})
            except Exception as e:
                logger.warning("PIL image optimization failed (%s), reading raw file bytes.", e)
                try:
                    with open(file_path, "rb") as f:
                        b64_content = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_content}})
                except Exception as ex:
                    logger.warning("Could not read image file for Gemini: %s", ex)
                    return None
        elif "pdf" in file_type.lower() or file_path.lower().endswith(".pdf"):
            try:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                # If PDF is under 20MB, pass directly to Gemini multimodal
                if len(pdf_bytes) <= 20 * 1024 * 1024:
                    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    parts.append({"inline_data": {"mime_type": "application/pdf", "data": b64_pdf}})
                if pdf_text:
                    parts.append({"text": f"Extracted Text Layer Preview:\n{pdf_text[:3000]}"})
            except Exception as e:
                logger.warning("Could not read PDF bytes for Gemini: %s", e)
                if not pdf_text:
                    return None
                parts.append({"text": f"Document Filename: {original_filename}\nReport Text Content:\n{pdf_text}"})
        else:
            if not pdf_text:
                return None
            parts.append({"text": f"Document Filename: {original_filename}\nReport Text Content:\n{pdf_text}"})

        # Try models in fallback order with retry on transient 503 spikes or timeouts
        for model in FALLBACK_GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={Config.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
            }
            import time
            for attempt in range(2):
                try:
                    res = requests.post(url, json=payload, timeout=35)
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
                                if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                                    parsed = parsed[0]
                                parsed["ai_provider"] = f"Google Gemini ({model})"

                                # Robustly normalize parameters
                                raw_params = (
                                    parsed.get("parameters")
                                    or parsed.get("test_values")
                                    or parsed.get("tests")
                                    or parsed.get("results")
                                    or []
                                )
                                clean_params = []
                                for param in raw_params:
                                    if isinstance(param, dict):
                                        # Accept flexible key naming: parameter, parameter_name, test_name, name
                                        p_name = (
                                            param.get("parameter_name")
                                            or param.get("parameter")
                                            or param.get("test_name")
                                            or param.get("name")
                                            or param.get("investigation")
                                            or ""
                                        ).strip()
                                        if not p_name:
                                            continue

                                        # Measured text & value
                                        raw_val = (
                                            param.get("measured_text")
                                            if param.get("measured_text") is not None
                                            else (
                                                param.get("value")
                                                if param.get("value") is not None
                                                else (
                                                    param.get("result")
                                                    if param.get("result") is not None
                                                    else param.get("measured_value")
                                                )
                                            )
                                        )
                                        m_text = str(raw_val).strip() if raw_val is not None else ""

                                        m_val = param.get("measured_value")
                                        if m_val is None:
                                            nums = re.findall(r"\b\d+(?:\.\d+)?\b", m_text)
                                            if nums:
                                                try:
                                                    m_val = float(nums[-1])
                                                except Exception:
                                                    m_val = None
                                        else:
                                            try:
                                                m_val = float(m_val)
                                            except Exception:
                                                m_val = None

                                        # Unit
                                        u_text = str(param.get("unit") or param.get("units") or "").strip()

                                        # Ref range
                                        r_text = str(
                                            param.get("ref_range_text")
                                            or param.get("reference_range")
                                            or param.get("normal_range")
                                            or param.get("range")
                                            or ""
                                        ).strip()

                                        # Flag
                                        raw_fl = str(param.get("flag") or param.get("status") or param.get("interpretation") or "NORMAL").strip().upper()
                                        if any(k in raw_fl for k in ("CRIT", "PANIC", "EMERG")):
                                            fl = "CRITICAL"
                                        elif any(k in raw_fl for k in ("HIGH", "ELEVAT", "POS", "1+", "2+", "3+", "ABNORM")):
                                            fl = "HIGH"
                                        elif any(k in raw_fl for k in ("LOW", "DECR")):
                                            fl = "LOW"
                                        else:
                                            fl = "NORMAL"

                                        clean_params.append({
                                            "parameter_name": p_name,
                                            "measured_value": m_val,
                                            "measured_text": m_text or (str(m_val) if m_val is not None else "-"),
                                            "unit": u_text,
                                            "ref_range_min": param.get("ref_range_min"),
                                            "ref_range_max": param.get("ref_range_max"),
                                            "ref_range_text": r_text,
                                            "flag": fl
                                        })
                                    elif isinstance(param, str) and param.strip():
                                        name = param.split(":")[0].strip() if ":" in param else param.strip()
                                        clean_params.append({
                                            "parameter_name": name,
                                            "measured_value": None,
                                            "measured_text": param,
                                            "unit": "",
                                            "ref_range_text": "",
                                            "flag": "HIGH" if any(w in param.lower() for w in ("high", "critical", "positive", "1+", "2+", "3+")) else "NORMAL"
                                        })
                                parsed["parameters"] = clean_params

                                # Flexible title
                                parsed["detected_title"] = (
                                    parsed.get("detected_title")
                                    or parsed.get("title")
                                    or parsed.get("test_type")
                                    or parsed.get("test_name")
                                    or ""
                                ).strip()

                                # Flexible summary
                                summary_candidate = (
                                    parsed.get("summary_plain_en")
                                    or parsed.get("summary")
                                    or parsed.get("explanation")
                                    or parsed.get("ai_summary")
                                    or ""
                                ).strip()

                                # If AI gave a very short summary, enrich it with parameter findings
                                if len(summary_candidate) < 40 and clean_params:
                                    abnormals = [p for p in clean_params if p["flag"] in ("HIGH", "LOW", "CRITICAL")]
                                    if abnormals:
                                        summary_candidate = (
                                            f"Your report analysis shows {len(abnormals)} parameter(s) outside standard reference intervals: "
                                            + ", ".join(f"{p['parameter_name']} ({p['measured_text']} {p['unit']})" for p in abnormals)
                                            + ". All other tested values are within normal ranges. Please consult your physician for comprehensive clinical review."
                                        )
                                    else:
                                        summary_candidate = (
                                            f"Good news! All {len(clean_params)} laboratory parameters in this test are currently within standard reference ranges. "
                                            "Continue regular health checkups and maintain a healthy lifestyle."
                                        )
                                parsed["summary_plain_en"] = summary_candidate
                                return parsed
                    elif res.status_code == 503 and attempt == 0:
                        logger.info("Gemini model %s 503, pausing 1.2s before retry...", model)
                        time.sleep(1.2)
                        continue
                    else:
                        logger.warning("Gemini model %s returned status %s: %s", model, res.status_code, res.text[:200])
                        break
                except requests.exceptions.Timeout:
                    logger.warning("Gemini model %s attempt %d timed out (35s)", model, attempt)
                    if attempt == 0:
                        time.sleep(1.5)
                        continue
                    break
                except Exception as e:
                    logger.warning("Gemini model %s attempt %d exception: %s", model, attempt, e)
                    break

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
