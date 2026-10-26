import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")

LABS = [
    ("DR. LAL PATHLABS CLINICAL DIAGNOSTICS", "National Reference Lab, Delhi-NCR | NABL & CAP Accredited"),
    ("METROPOLIS HEALTHCARE LIMITED", "Central Pathology & Laboratory Services | ISO 15189:2012"),
    ("SRL DIAGNOSTICS & RESEARCH CENTER", "Super Religare Laboratories | Quality First Diagnostics"),
    ("APOLLO DIAGNOSTICS PATHOLOGY SERVICES", "A Unit of Apollo Hospitals Enterprise Ltd."),
    ("MAX HEALTHCARE PATHOLOGY & LAB MEDICINE", "Institute of Laboratory Medicine, New Delhi"),
    ("THYROCARE TECHNOLOGIES LIMITED", "Central Processing Laboratory, D-37/1, TTC MIDC, Turbhe"),
    ("QUEST DIAGNOSTICS HEALTHCARE", "Precision Clinical Testing & Reference Laboratory")
]

PATIENT_FIRST_NAMES = [
    "Rajesh", "Amit", "Pooja", "Sunita", "Ramesh", "Deepak", "Sanjay", "Anjali",
    "Vikram", "Sneha", "Kavita", "Mohit", "Rahul", "Priya", "Neha", "Manish",
    "Kishore", "Geeta", "Sunil", "Ritu", "Alok", "Vandana", "Suresh", "Meena"
]
PATIENT_LAST_NAMES = [
    "Kumar", "Sharma", "Verma", "Gupta", "Singh", "Patel", "Yadav", "Mishra",
    "Chauhan", "Joshi", "Bhatia", "Aggarwal", "Reddy", "Mehta", "Malhotra", "Saxena"
]

DOCTORS = [
    "Dr. S. K. Mehta (MD, Medicine)", "Dr. Anita Roy (MD, Pathology)",
    "Dr. R. K. Singhania (MBBS, DCP)", "Dr. Pradeep Bansal (MD, FACP)",
    "Dr. Neha Kapoor (MD, Consultant)"
]

CATEGORIES = [
    "normal_healthy",
    "anemia_low_hemoglobin",
    "infection_high_wbc",
    "low_platelets",
    "diabetes_sugar",
    "high_cholesterol",
    "thyroid"
]

def generate_report_content(category):
    """Generate dynamic clinical parameters and labels for each category."""
    if category == "normal_healthy":
        title = "COMPLETE BLOOD COUNT (CBC) & BIOCHEMICAL SCREEN"
        hb = round(random.uniform(13.2, 16.8), 1)
        wbc = f"{random.randint(4500, 10200):,}"
        rbc = round(random.uniform(4.5, 5.7), 2)
        plt = f"{random.randint(180, 390)},000"
        glu = random.randint(76, 98)
        chol = random.randint(135, 195)
        tsh = round(random.uniform(0.9, 3.8), 2)
        tests = [
            ("Hemoglobin (Hb)", str(hb), "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Total Leucocyte Count (WBC)", wbc, "4,000 - 11,000", "/cumm", "NORMAL"),
            ("RBC Count", str(rbc), "4.5 - 5.9", "mil/uL", "NORMAL"),
            ("Platelet Count", plt, "150,000 - 450,000", "/cumm", "NORMAL"),
            ("Fasting Blood Glucose", str(glu), "70 - 100", "mg/dL", "NORMAL"),
            ("Total Cholesterol", str(chol), "< 200", "mg/dL", "NORMAL"),
            ("TSH (Thyroid)", str(tsh), "0.4 - 4.5", "uIU/mL", "NORMAL")
        ]
        comment = "All laboratory parameters are within normal physiological reference intervals."

    elif category == "anemia_low_hemoglobin":
        title = "HEMATOLOGY COMPLETE REPORT - ANEMIA PROFILE"
        hb = round(random.uniform(5.5, 10.4), 1)
        rbc = round(random.uniform(2.4, 3.8), 2)
        pcv = round(random.uniform(21.0, 33.0), 1)
        mcv = round(random.uniform(62.0, 77.0), 1)
        mch = round(random.uniform(19.0, 25.0), 1)
        tests = [
            ("Hemoglobin (Hb)", str(hb), "13.0 - 17.0", "g/dL", "CRITICAL LOW" if hb < 8.0 else "LOW"),
            ("RBC Count", str(rbc), "4.5 - 5.9", "mil/uL", "LOW"),
            ("Packed Cell Volume (PCV)", str(pcv), "40.0 - 50.0", "%", "LOW"),
            ("Mean Corpuscular Volume (MCV)", str(mcv), "80.0 - 100.0", "fL", "MICROCYTIC"),
            ("MCH", str(mch), "27.0 - 32.0", "pg", "HYPOCHROMIC"),
            ("Platelet Count", f"{random.randint(160, 410)},000", "150,000 - 450,000", "/cumm", "NORMAL"),
            ("Serum Ferritin", str(random.randint(4, 18)), "20 - 250", "ng/mL", "DEFICIENT")
        ]
        comment = f"Microcytic hypochromic anemia (Hb {hb} g/dL). Recommend iron profile & clinical workup."

    elif category == "infection_high_wbc":
        title = "HEMATOLOGY REPORT - LEUKOCYTOSIS & INFECTION SCREEN"
        wbc_val = random.randint(12500, 29000)
        neutro = random.randint(78, 92)
        lympho = 100 - neutro - random.randint(2, 6)
        tests = [
            ("Total Leucocyte Count (TLC)", f"{wbc_val:,}", "4,000 - 11,000", "/cumm", "CRITICAL HIGH (INFECTION)"),
            ("Absolute Neutrophil Count", f"{int(wbc_val * neutro / 100):,}", "2,000 - 7,000", "/cumm", "HIGH"),
            ("Neutrophils Percentage", f"{neutro}%", "40 - 75", "%", "ELEVATED"),
            ("Lymphocytes", f"{lympho}%", "20 - 45", "%", "RELATIVE LOW"),
            ("Hemoglobin (Hb)", str(round(random.uniform(12.5, 15.5), 1)), "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Platelet Count", f"{random.randint(180, 440)},000", "150,000 - 450,000", "/cumm", "NORMAL"),
            ("C-Reactive Protein (CRP)", str(round(random.uniform(15.0, 85.0), 1)), "< 5.0", "mg/L", "HIGH POSITIVE")
        ]
        comment = f"Severe leukocytosis (WBC {wbc_val:,}) with neutrophilia. Acute bacterial infection suspected."

    elif category == "low_platelets":
        title = "HEMATOLOGY REPORT - THROMBOCYTOPENIA & DENGUE EVALUATION"
        plt_val = random.randint(12000, 95000)
        tests = [
            ("Platelet Count", f"{plt_val:,}", "150,000 - 450,000", "/cumm", "CRITICAL LOW (BLEED RISK)" if plt_val < 50000 else "LOW"),
            ("Mean Platelet Volume (MPV)", str(round(random.uniform(7.0, 11.5), 1)), "7.5 - 11.5", "fL", "NORMAL"),
            ("Total Leucocyte Count (WBC)", f"{random.randint(2800, 4800):,}", "4,000 - 11,000", "/cumm", "BORDERLINE LEUKOPENIA"),
            ("Hematocrit (PCV)", str(round(random.uniform(39.0, 48.0), 1)), "40.0 - 50.0", "%", "NORMAL"),
            ("Hemoglobin (Hb)", str(round(random.uniform(12.8, 16.0), 1)), "13.0 - 17.0", "g/dL", "NORMAL"),
            ("Dengue NS1 Antigen", random.choice(["REACTIVE / POSITIVE", "POSITIVE"]), "NON-REACTIVE", "", "ALERT")
        ]
        comment = f"Significant thrombocytopenia (Platelets {plt_val:,}). High risk of spontaneous bleeding. Monitor closely."

    elif category == "diabetes_sugar":
        title = "BIOCHEMISTRY REPORT - DIABETIC & GLYCEMIC PROFILE"
        fbs = random.randint(138, 380)
        ppbs = fbs + random.randint(60, 160)
        hba1c = round(random.uniform(7.2, 13.8), 1)
        tests = [
            ("Fasting Blood Glucose", str(fbs), "70 - 100", "mg/dL", "CRITICAL HIGH" if fbs > 200 else "HIGH"),
            ("Post Prandial Blood Glucose", str(ppbs), "< 140", "mg/dL", "VERY HIGH"),
            ("HbA1c (Glycated Hemoglobin)", f"{hba1c}%", "< 5.7", "%", "POOR GLYCEMIC CONTROL"),
            ("Estimated Avg Glucose (eAG)", str(int(28.7 * hba1c - 46.7)), "70 - 126", "mg/dL", "ELEVATED"),
            ("Urine Glucose", random.choice(["+++ Positive", "++++ Positive", "++ Positive"]), "Negative", "", "GLYCOSURIA")
        ]
        comment = f"Markedly elevated glycemic index (HbA1c {hba1c}%, FBS {fbs} mg/dL) confirming uncontrolled diabetes."

    elif category == "high_cholesterol":
        title = "BIOCHEMISTRY REPORT - LIPID PROFILE & CARDIOVASCULAR SCREEN"
        tchol = random.randint(215, 410)
        trig = random.randint(180, 490)
        ldl = random.randint(135, 260)
        hdl = random.randint(24, 38)
        vldl = int(trig / 5)
        tests = [
            ("Total Serum Cholesterol", str(tchol), "< 200", "mg/dL", "CRITICAL HIGH" if tchol > 280 else "HIGH"),
            ("Serum Triglycerides", str(trig), "< 150", "mg/dL", "VERY HIGH"),
            ("LDL Cholesterol (Calculated)", str(ldl), "< 100", "mg/dL", "HIGH ATHEROGENIC RISK"),
            ("HDL Cholesterol (Good)", str(hdl), "> 40", "mg/dL", "SUB-OPTIMAL LOW"),
            ("VLDL Cholesterol", str(vldl), "< 30", "mg/dL", "ELEVATED"),
            ("Chol / HDL Ratio", str(round(tchol / hdl, 1)), "< 4.5", "Ratio", "HIGH RISK")
        ]
        comment = f"Hyperlipidemia / Dyslipidemia pattern (Cholesterol {tchol} mg/dL, Triglycerides {trig} mg/dL). Statin evaluation."

    elif category == "thyroid":
        title = "IMMUNOASSAY & ENDOCRINOLOGY REPORT - THYROID PROFILE"
        tsh = round(random.uniform(5.8, 38.0), 2)
        t3 = round(random.uniform(0.40, 0.75), 2)
        t4 = round(random.uniform(2.8, 4.8), 1)
        ft4 = round(random.uniform(0.48, 0.78), 2)
        tests = [
            ("TSH (Ultrasensitive 3rd Gen)", str(tsh), "0.40 - 4.50", "uIU/mL", "CRITICAL HIGH" if tsh > 10 else "HIGH (HYPOTHYROID)"),
            ("Total Triiodothyronine (T3)", str(t3), "0.80 - 2.00", "ng/mL", "LOW"),
            ("Total Thyroxine (T4)", str(t4), "5.10 - 14.10", "ug/dL", "LOW"),
            ("Free T4 (FT4)", str(ft4), "0.89 - 1.76", "ng/dL", "LOW"),
            ("Anti-TPO Antibodies", str(random.randint(65, 480)), "< 35", "IU/mL", "POSITIVE")
        ]
        comment = f"Primary Hypothyroidism pattern with elevated TSH ({tsh} uIU/mL). Endocrine consultation indicated."

    return title, tests, comment

def render_single_report(category, index, save_path):
    """Render a realistic, high-quality scanned lab document."""
    width, height = 750, 1000
    # Slight paper tint variation (off-white, sterile lab blue tint)
    tint = random.choice([
        (253, 253, 254), (250, 251, 253), (254, 252, 250), (251, 253, 251)
    ])
    img = Image.new("RGB", (width, height), color=tint)
    draw = ImageDraw.Draw(img)

    # Borders
    draw.rectangle([(18, 18), (width - 18, height - 18)], outline=(190, 195, 205), width=2)
    draw.rectangle([(23, 23), (width - 23, height - 23)], outline=(225, 230, 238), width=1)

    # Header
    lab_title, lab_sub = random.choice(LABS)
    header_color = random.choice([(15, 45, 95), (20, 70, 60), (90, 30, 40), (25, 35, 70)])
    draw.rectangle([(28, 28), (width - 28, 105)], fill=(238, 243, 250))
    draw.text((45, 40), lab_title, fill=header_color)
    draw.text((45, 72), lab_sub, fill=(100, 110, 125))

    # Patient Details Strip
    p_name = f"{random.choice(['Mr.', 'Mrs.', 'Ms.'])} {random.choice(PATIENT_FIRST_NAMES)} {random.choice(PATIENT_LAST_NAMES)}"
    p_age = f"{random.randint(21, 74)} Y / {random.choice(['Male', 'Female'])}"
    doc = random.choice(DOCTORS)
    sample_id = f"SMP-{random.randint(1000000, 9999999)}"

    draw.rectangle([(28, 115), (width - 28, 190)], fill=(247, 249, 252), outline=(215, 220, 230))
    draw.text((42, 125), f"Patient Name : {p_name}", fill=(20, 20, 20))
    draw.text((42, 145), f"Age / Gender : {p_age}", fill=(20, 20, 20))
    draw.text((42, 165), f"Ref. Doctor  : {doc}", fill=(70, 70, 70))

    draw.text((450, 125), f"Lab Sample ID: {sample_id}", fill=(20, 20, 20))
    draw.text((450, 145), f"Collection   : 2026-10-25 07:45 AM", fill=(20, 20, 20))
    draw.text((450, 165), f"Verified By  : Senior Biochemist", fill=(70, 70, 70))

    # Test Section Banner
    title, tests, comment = generate_report_content(category)
    draw.rectangle([(28, 202), (width - 28, 238)], fill=header_color)
    draw.text((42, 212), title, fill=(255, 255, 255))

    # Table Header
    y = 250
    draw.rectangle([(28, y), (width - 28, y + 26)], fill=(225, 232, 242))
    draw.text((42, y + 5), "TEST DESCRIPTION", fill=(30, 30, 30))
    draw.text((340, y + 5), "RESULT", fill=(30, 30, 30))
    draw.text((450, y + 5), "BIOLOGICAL REF", fill=(30, 30, 30))
    draw.text((585, y + 5), "UNIT", fill=(30, 30, 30))
    draw.text((655, y + 5), "FLAG", fill=(30, 30, 30))

    draw.line([(28, y + 26), (width - 28, y + 26)], fill=(160, 175, 195), width=2)
    y += 32

    # Rows
    for tname, res, ref, unit, flag in tests:
        is_abnormal = any(k in flag for k in ["HIGH", "LOW", "DEFICIENT", "RISK", "ALERT", "POSITIVE", "MICROCYTIC", "HYPOCHROMIC"])
        if is_abnormal:
            draw.rectangle([(30, y - 2), (width - 30, y + 24)], fill=(255, 243, 243))
            flag_color = (195, 15, 15)
            val_color = (185, 5, 5)
        else:
            flag_color = (20, 130, 45)
            val_color = (25, 25, 25)

        draw.text((42, y + 3), tname, fill=(20, 20, 20))
        draw.text((340, y + 3), res, fill=val_color)
        draw.text((450, y + 3), ref, fill=(80, 80, 80))
        draw.text((585, y + 3), unit, fill=(80, 80, 80))
        draw.text((655, y + 3), flag, fill=flag_color)

        draw.line([(28, y + 26), (width - 28, y + 26)], fill=(232, 236, 242), width=1)
        y += 33

    # Clinical Note Box
    y = max(y + 25, 770)
    draw.rectangle([(28, y), (width - 28, y + 90)], fill=(250, 250, 252), outline=(210, 215, 225))
    draw.text((40, y + 10), "INTERPRETATION & PATHOLOGY NOTES:", fill=(40, 40, 40))
    draw.text((40, y + 35), f"- {comment}", fill=(160, 20, 20) if category != "normal_healthy" else (50, 50, 50))
    draw.text((40, y + 60), "- Tests performed on fully automated calibrated analyzers with dual controls.", fill=(110, 115, 120))

    # Footer Stamp
    y = height - 110
    draw.rectangle([(width - 260, y), (width - 40, y + 75)], outline=(170, 190, 220), width=1)
    draw.text((width - 240, y + 10), "*** ELECTRONICALLY SIGNED ***", fill=(130, 150, 185))
    draw.text((width - 240, y + 30), "Dr. S. K. Mehta, MD (Path)", fill=(30, 30, 30))
    draw.text((width - 240, y + 50), "Chief Medical Officer", fill=(90, 95, 100))

    # Save as compressed JPEG
    img.save(save_path, "JPEG", quality=88, optimize=True)

def generate_worker(args):
    cat, idx, out_path = args
    render_single_report(cat, idx, out_path)
    return cat

def main():
    COUNT_PER_CATEGORY = 1000
    print("=" * 65)
    print(f"GENERATING LARGE DATASET: {COUNT_PER_CATEGORY} REPORTS PER CATEGORY")
    print(f"Total Target Images: {COUNT_PER_CATEGORY * len(CATEGORIES)} (7 Categories)")
    print("=" * 65)

    tasks = []
    for cat in CATEGORIES:
        cat_dir = os.path.join(DATASET_ROOT, cat)
        os.makedirs(cat_dir, exist_ok=True)
        for i in range(1, COUNT_PER_CATEGORY + 1):
            file_name = f"report_{cat}_{i:04d}.jpg"
            file_path = os.path.join(cat_dir, file_name)
            tasks.append((cat, i, file_path))

    start_time = time.time()
    # Use 8 processes to utilize the Ryzen 7 4800H cores
    total_tasks = len(tasks)
    completed = 0
    print(f"[INFO] Starting generation using 8 parallel CPU processes...")

    with ProcessPoolExecutor(max_workers=8) as executor:
        for cat in executor.map(generate_worker, tasks, chunksize=50):
            completed += 1
            if completed % 500 == 0 or completed == total_tasks:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = (total_tasks - completed) / rate if rate > 0 else 0
                print(f"  Progress: {completed}/{total_tasks} images ({completed/total_tasks*100:.1f}%) | Speed: {rate:.1f} img/s | ETA: {remaining:.0f}s")

    total_time = time.time() - start_time
    print("=" * 65)
    print(f"[SUCCESS] 7,000 Blood Test Reports Generated in {total_time:.1f} seconds!")
    print(f"Dataset Root: {DATASET_ROOT}")
    print("=" * 65)

if __name__ == "__main__":
    main()
