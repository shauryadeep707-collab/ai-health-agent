import os
import random
from PIL import Image, ImageDraw, ImageFont

DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")

LAB_NAMES = [
    "APOLLO DIAGNOSTICS & CLINICAL LAB",
    "DR. LAL PATHLABS CLINICAL REPORT",
    "MAX HEALTHCARE PATHOLOGY SERVICES",
    "METROPOLIS HEALTHCARE BLOOD TEST REPORT",
    "SRL DIAGNOSTICS LABORATORY REPORT"
]

CATEGORIES_INFO = {
    "normal_healthy": {
        "title": "COMPLETE BLOOD COUNT (CBC) - ROUTINE HEALTH CHECKUP",
        "tests": [
            ("Hemoglobin (Hb)", "14.5", "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Total Leucocyte Count (WBC)", "7,200", "4,000 - 11,000", "/cumm", "NORMAL"),
            ("RBC Count", "4.8", "4.5 - 5.9", "mil/uL", "NORMAL"),
            ("Platelet Count", "260,000", "150,000 - 450,000", "/cumm", "NORMAL"),
            ("Fasting Blood Sugar", "92", "70 - 100", "mg/dL", "NORMAL"),
            ("Serum Cholesterol", "165", "< 200", "mg/dL", "NORMAL"),
            ("TSH (Thyroid)", "2.1", "0.4 - 4.5", "uIU/mL", "NORMAL")
        ]
    },
    "anemia_low_hemoglobin": {
        "title": "HEMATOLOGY REPORT - ANEMIA PROFILE",
        "tests": [
            ("Hemoglobin (Hb)", "7.2", "13.0 - 17.0", "g/dL", "CRITICAL LOW"),
            ("RBC Count", "2.9", "4.5 - 5.9", "mil/uL", "LOW"),
            ("Hematocrit (PCV)", "24.5", "40.0 - 50.0", "%", "LOW"),
            ("MCV", "68.0", "80.0 - 100.0", "fL", "MICROCYTIC"),
            ("Total Leucocyte Count (WBC)", "6,800", "4,000 - 11,000", "/cumm", "NORMAL"),
            ("Platelet Count", "210,000", "150,000 - 450,000", "/cumm", "NORMAL")
        ]
    },
    "infection_high_wbc": {
        "title": "HEMATOLOGY REPORT - INFECTION / LEUKOCYTOSIS SCREEN",
        "tests": [
            ("Total Leucocyte Count (WBC)", "18,400", "4,000 - 11,000", "/cumm", "HIGH (INFECTION)"),
            ("Neutrophils", "84", "40 - 75", "%", "HIGH"),
            ("Lymphocytes", "12", "20 - 45", "%", "LOW"),
            ("Hemoglobin (Hb)", "13.2", "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Platelet Count", "320,000", "150,000 - 450,000", "/cumm", "NORMAL")
        ]
    },
    "low_platelets": {
        "title": "HEMATOLOGY REPORT - THROMBOCYTOPENIA / DENGUE MONITOR",
        "tests": [
            ("Platelet Count", "38,000", "150,000 - 450,000", "/cumm", "CRITICAL LOW (BLEED RISK)"),
            ("Total Leucocyte Count (WBC)", "3,400", "4,000 - 11,000", "/cumm", "BORDERLINE LOW"),
            ("Hemoglobin (Hb)", "13.8", "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Hematocrit (PCV)", "42.0", "40.0 - 50.0", "%", "NORMAL")
        ]
    },
    "diabetes_sugar": {
        "title": "BIOCHEMISTRY REPORT - DIABETIC PROFILE",
        "tests": [
            ("Fasting Blood Glucose", "248", "70 - 100", "mg/dL", "VERY HIGH"),
            ("Post Prandial Glucose", "340", "< 140", "mg/dL", "VERY HIGH"),
            ("HbA1c (Glycated Hb)", "10.4", "< 5.7", "%", "HIGH RISK (DIABETIC)"),
            ("Estimated Avg Glucose (eAG)", "251", "70 - 126", "mg/dL", "ELEVATED")
        ]
    },
    "high_cholesterol": {
        "title": "BIOCHEMISTRY REPORT - LIPID PROFILE (CARDIOVASCULAR)",
        "tests": [
            ("Total Serum Cholesterol", "295", "< 200", "mg/dL", "HIGH RISK"),
            ("Triglycerides", "310", "< 150", "mg/dL", "VERY HIGH"),
            ("LDL Cholesterol (Bad)", "192", "< 100", "mg/dL", "HIGH"),
            ("HDL Cholesterol (Good)", "32", "> 40", "mg/dL", "LOW"),
            ("VLDL Cholesterol", "62", "< 30", "mg/dL", "HIGH")
        ]
    },
    "thyroid": {
        "title": "ENDOCRINOLOGY REPORT - THYROID PROFILE (CLIA)",
        "tests": [
            ("TSH (Thyroid Stimulating Hormone)", "14.80", "0.40 - 4.50", "uIU/mL", "HIGH (HYPOTHYROID)"),
            ("Total Triiodothyronine (T3)", "0.55", "0.80 - 2.00", "ng/mL", "LOW"),
            ("Total Thyroxine (T4)", "3.80", "5.10 - 14.10", "ug/dL", "LOW"),
            ("Free T4 (FT4)", "0.62", "0.89 - 1.76", "ng/dL", "LOW")
        ]
    }
}

PATIENTS = [
    ("Mr. Rajesh Kumar", "42 Y / Male", "DR-REF-1092"),
    ("Mrs. Sunita Verma", "58 Y / Female", "DR-REF-8841"),
    ("Mr. Amit Sharma", "31 Y / Male", "DR-REF-3420"),
    ("Mrs. Pooja Gupta", "27 Y / Female", "DR-REF-7104"),
    ("Mr. Vikram Singh", "65 Y / Male", "DR-REF-9051")
]

def draw_report(category, index):
    width, height = 800, 1050
    img = Image.new("RGB", (width, height), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(180, 180, 190), width=2)
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline=(220, 220, 230), width=1)

    # Top Header
    lab_name = random.choice(LAB_NAMES)
    draw.rectangle([(30, 30), (width - 30, 110)], fill=(235, 242, 250))
    draw.text((50, 45), lab_name, fill=(15, 45, 90))
    draw.text((50, 75), "Accredited Medical Diagnostics Laboratory | ISO 15189:2012 Certified", fill=(100, 110, 120))

    # Patient Details Strip
    pat_name, pat_age, ref_no = random.choice(PATIENTS)
    draw.rectangle([(30, 120), (width - 30, 200)], fill=(245, 247, 250), outline=(210, 215, 225))
    draw.text((45, 130), f"Patient Name: {pat_name}", fill=(20, 20, 20))
    draw.text((45, 155), f"Age / Gender: {pat_age}", fill=(20, 20, 20))
    draw.text((45, 175), f"Ref Doctor  : Dr. S. K. Mehta (MD)", fill=(60, 60, 60))

    draw.text((480, 130), f"Report ID  : LAB-{random.randint(100000, 999999)}", fill=(20, 20, 20))
    draw.text((480, 155), f"Sample Date: 2026-10-24 08:30 AM", fill=(20, 20, 20))
    draw.text((480, 175), f"Report Date: 2026-10-24 02:45 PM", fill=(20, 20, 20))

    # Test Section Heading
    info = CATEGORIES_INFO[category]
    draw.rectangle([(30, 215), (width - 30, 250)], fill=(18, 55, 110))
    draw.text((45, 225), info["title"], fill=(255, 255, 255))

    # Table Header
    y = 265
    draw.rectangle([(30, y), (width - 30, y + 28)], fill=(225, 230, 240))
    draw.text((45, y + 6), "INVESTIGATION (TEST NAME)", fill=(30, 30, 30))
    draw.text((360, y + 6), "RESULT", fill=(30, 30, 30))
    draw.text((470, y + 6), "REF. INTERVAL", fill=(30, 30, 30))
    draw.text((610, y + 6), "UNIT", fill=(30, 30, 30))
    draw.text((690, y + 6), "STATUS", fill=(30, 30, 30))

    draw.line([(30, y + 28), (width - 30, y + 28)], fill=(160, 170, 190), width=2)
    y += 35

    # Rows
    for row in info["tests"]:
        tname, res, ref, unit, status = row
        # Highlight abnormal rows
        if "HIGH" in status or "LOW" in status or "RISK" in status or "MICROCYTIC" in status:
            draw.rectangle([(32, y - 3), (width - 32, y + 28)], fill=(255, 245, 245))
            status_color = (190, 20, 20)
            res_color = (180, 0, 0)
        else:
            status_color = (20, 130, 40)
            res_color = (10, 10, 10)

        draw.text((45, y + 4), tname, fill=(20, 20, 20))
        draw.text((360, y + 4), res, fill=res_color)
        draw.text((470, y + 4), ref, fill=(80, 80, 80))
        draw.text((610, y + 4), unit, fill=(80, 80, 80))
        draw.text((690, y + 4), status, fill=status_color)

        draw.line([(30, y + 30), (width - 30, y + 30)], fill=(230, 235, 240), width=1)
        y += 38

    # Doctor Notes & Signature
    y = max(y + 30, 820)
    draw.line([(30, y), (width - 30, y)], fill=(200, 205, 215), width=1)
    y += 15
    draw.text((45, y), "CLINICAL INTERPRETATION / PATHOLOGIST COMMENTS:", fill=(40, 40, 40))
    y += 22
    if category == "normal_healthy":
        draw.text((45, y), "- All blood count parameters are within physiological biological reference limits.", fill=(70, 70, 70))
    elif category == "anemia_low_hemoglobin":
        draw.text((45, y), "- Microcytic hypochromic anemia picture observed. Suggest Serum Ferritin & Iron studies.", fill=(160, 20, 20))
    elif category == "infection_high_wbc":
        draw.text((45, y), "- Marked neutrophilic leukocytosis. Clinical correlation with acute bacterial infection advised.", fill=(160, 20, 20))
    elif category == "low_platelets":
        draw.text((45, y), "- Severe thrombocytopenia. Monitor for petechiae/bleeding manifestations. Repeat in 24 hrs.", fill=(160, 20, 20))
    elif category == "diabetes_sugar":
        draw.text((45, y), "- Uncontrolled glycemic levels consistent with active Diabetes Mellitus. Consult Diabetologist.", fill=(160, 20, 20))
    elif category == "high_cholesterol":
        draw.text((45, y), "- Hypercholesterolemia with elevated atherogenic risk profile. Dietary & statin evaluation advised.", fill=(160, 20, 20))
    elif category == "thyroid":
        draw.text((45, y), "- Primary hypothyroidism picture indicated by elevated TSH and suppressed free thyroid hormone.", fill=(160, 20, 20))

    # Stamp / Signatures
    draw.rectangle([(width - 260, height - 120), (width - 60, height - 50)], outline=(160, 180, 210), width=1)
    draw.text((width - 240, height - 105), "[OFFICIAL LAB SEAL]", fill=(120, 140, 180))
    draw.text((width - 240, height - 85), "Dr. R. K. Singhania, MD", fill=(40, 40, 40))
    draw.text((width - 240, height - 68), "Consultant Pathologist", fill=(90, 90, 90))

    return img

def main():
    print("=" * 60)
    print("GENERATING REALISTIC BLOOD TEST REPORT IMAGES")
    print("=" * 60)
    total_created = 0
    for cat in CATEGORIES_INFO:
        cat_dir = os.path.join(DATASET_ROOT, cat)
        os.makedirs(cat_dir, exist_ok=True)
        # Create 5 diverse sample images for each class
        for i in range(1, 6):
            img = draw_report(cat, i)
            file_name = f"blood_report_{cat}_{i:02d}.jpg"
            file_path = os.path.join(cat_dir, file_name)
            img.save(file_path, "JPEG", quality=92)
            total_created += 1
            print(f"  [OK] Saved: {cat}/{file_name}")

    print("=" * 60)
    print(f"Total {total_created} Blood Test Report Images Created Successfully!")
    print(f"Dataset Location: {DATASET_ROOT}")
    print("=" * 60)

if __name__ == "__main__":
    main()
