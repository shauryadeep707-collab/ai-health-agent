import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "dataset", "urine_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HOSPITALS = [
    ("Himalayan Institute of Medical Sciences", "Himalayan Central Diagnostic & Research Laboratory", "Swami Ram Nagar, P.O. Jolly Grant, Dehradun"),
    ("Dr. Lal PathLabs Clinical Diagnostics", "National Reference Pathology Laboratory", "ISO 15189:2012 Certified Lab"),
    ("Metropolis Healthcare Pathology Services", "Department of Clinical Pathology & Urinalysis", "NABL & CAP Accredited Central Lab"),
    ("Apollo Diagnostics & Clinical Laboratory", "Specialized Urine & Routine Microscopy Unit", "Apollo Hospitals Group"),
    ("Max Super Speciality Hospital Labs", "Institute of Laboratory Medicine & Pathology", "New Delhi - Central Pathology Unit")
]

PATIENTS = [
    ("Ms. KRITIKA TIWARI", "19 Y / Female", "Dr. SWATI DHAR"),
    ("Mrs. SUNITA VERMA", "34 Y / Female", "Dr. A. K. BANSAL"),
    ("Mr. RAHUL MEHRA", "28 Y / Male", "Dr. S. K. MEHTA"),
    ("Mrs. POOJA GUPTA", "25 Y / Female", "Dr. NEHA KAPOOR"),
    ("Mr. VIKRAM SINGH", "45 Y / Male", "Dr. R. K. SINGHANIA"),
    ("Mrs. ANJALI SHARMA", "22 Y / Female", "Dr. PRIYA DAS")
]

def render_urine_report(index, save_path):
    width, height = 750, 1000
    tint = random.choice([(255, 255, 255), (252, 253, 255), (254, 254, 252)])
    img = Image.new("RGB", (width, height), color=tint)
    draw = ImageDraw.Draw(img)

    # Document border
    draw.rectangle([(15, 15), (width - 15, height - 15)], outline=(190, 195, 205), width=2)
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(225, 230, 238), width=1)

    # Hospital Header
    h_name, h_dept, h_addr = random.choice(HOSPITALS)
    draw.rectangle([(25, 25), (width - 25, 100)], fill=(240, 245, 252))
    draw.text((45, 36), h_name, fill=(20, 50, 100))
    draw.text((45, 58), h_dept, fill=(90, 100, 115))
    draw.text((45, 78), h_addr, fill=(110, 120, 130))

    # Patient info box
    p_name, p_age, p_doc = random.choice(PATIENTS)
    draw.rectangle([(25, 108), (width - 25, 185)], fill=(248, 250, 253), outline=(215, 220, 230))
    draw.text((40, 118), f"Patient Name: {p_name}", fill=(20, 20, 20))
    draw.text((40, 138), f"Age / Gender: {p_age}", fill=(20, 20, 20))
    draw.text((40, 158), f"Referred By : {p_doc}", fill=(60, 60, 60))

    draw.text((440, 118), f"UHID/IP No   : {random.randint(3000000, 9999999)}", fill=(20, 20, 20))
    draw.text((440, 138), f"Sample Date  : 2026-10-26 {random.randint(10, 12)}:{random.randint(10, 59)} AM", fill=(20, 20, 20))
    draw.text((440, 158), f"Report Status: Final", fill=(20, 120, 40))

    # Section Banner
    draw.rectangle([(25, 195), (width - 25, 230)], fill=(25, 60, 120))
    draw.text((40, 205), "CLINICAL PATHOLOGY - URINE COMPLETE (ROUTINE & MICROSCOPY)", fill=(255, 255, 255))

    # Table Header
    y = 240
    draw.rectangle([(25, y), (width - 25, y + 26)], fill=(225, 232, 245))
    draw.text((40, y + 5), "TEST NAME", fill=(30, 30, 30))
    draw.text((330, y + 5), "RESULT", fill=(30, 30, 30))
    draw.text((450, y + 5), "UNIT", fill=(30, 30, 30))
    draw.text((540, y + 5), "BIOLOGICAL REF. RANGE", fill=(30, 30, 30))
    draw.line([(25, y + 26), (width - 25, y + 26)], fill=(160, 175, 195), width=2)
    y += 32

    # Group 1: Physical Examination
    draw.text((40, y), "-- PHYSICAL EXAMINATION --", fill=(100, 110, 130))
    y += 20
    draw.text((40, y), "Colour", fill=(20, 20, 20))
    draw.text((330, y), random.choice(["Pale Yellow", "Yellow", "Turbid Yellow", "Hazy Yellow"]), fill=(20, 20, 20))
    draw.text((540, y), "Pale Yellow", fill=(90, 90, 90))
    y += 24

    draw.text((40, y), "pH", fill=(20, 20, 20))
    draw.text((330, y), str(round(random.uniform(5.5, 7.5), 1)), fill=(20, 20, 20))
    draw.text((540, y), "5.0 - 8.0", fill=(90, 90, 90))
    y += 24

    draw.text((40, y), "Specific Gravity", fill=(20, 20, 20))
    draw.text((330, y), f"1.{random.randint(10, 30):03d}", fill=(20, 20, 20))
    draw.text((540, y), "1.000 - 1.030", fill=(90, 90, 90))
    y += 28

    # Group 2: Chemical Examination
    draw.text((40, y), "-- CHEMICAL EXAMINATION --", fill=(100, 110, 130))
    y += 20
    draw.text((40, y), "Protein", fill=(20, 20, 20))
    draw.text((330, y), random.choice(["1+", "2+", "Negative", "Trace"]), fill=(180, 20, 20))
    draw.text((540, y), "Negative", fill=(90, 90, 90))
    y += 24

    draw.text((40, y), "Nitrite", fill=(20, 20, 20))
    draw.text((330, y), random.choice(["1+ (Positive)", "Positive", "Negative"]), fill=(190, 10, 10))
    draw.text((540, y), "Negative", fill=(90, 90, 90))
    y += 24

    draw.text((40, y), "Leucocyte Esterase", fill=(20, 20, 20))
    draw.text((330, y), random.choice(["3+ (Positive)", "2+ (Positive)", "1+"]), fill=(190, 10, 10))
    draw.text((540, y), "Negative", fill=(90, 90, 90))
    y += 24

    draw.text((40, y), "Glucose", fill=(20, 20, 20))
    draw.text((330, y), "Negative", fill=(20, 20, 20))
    draw.text((540, y), "Negative", fill=(90, 90, 90))
    y += 28

    # Group 3: Microscopic Examination
    draw.text((40, y), "-- MICROSCOPIC EXAMINATION (Centrifuged Deposit) --", fill=(100, 110, 130))
    y += 20

    # Pus cells
    pus_val = random.choice(["250-300", "150-200", "80-100", "40-60", "20-30"])
    draw.rectangle([(28, y - 2), (width - 28, y + 22)], fill=(255, 242, 242))
    draw.text((40, y + 2), "Pus Cells (Leukocytes)", fill=(20, 20, 20))
    draw.text((330, y + 2), pus_val, fill=(195, 10, 10))
    draw.text((450, y + 2), "/HPF", fill=(80, 80, 80))
    draw.text((540, y + 2), "< 5 Cells / HPF (CRITICAL HIGH)", fill=(195, 10, 10))
    y += 26

    # Epithelial cells
    draw.text((40, y), "Epithelial Cells", fill=(20, 20, 20))
    draw.text((330, y), f"{random.randint(3, 8)}-{random.randint(9, 15)}", fill=(20, 20, 20))
    draw.text((450, y), "/HPF", fill=(80, 80, 80))
    draw.text((540, y), "< 5 Cells / HPF", fill=(90, 90, 90))
    y += 24

    # RBCs
    draw.text((40, y), "R.B.Cs", fill=(20, 20, 20))
    draw.text((330, y), f"{random.randint(1, 4)}-{random.randint(5, 8)}", fill=(20, 20, 20))
    draw.text((450, y), "/HPF", fill=(80, 80, 80))
    draw.text((540, y), "< 3 Cells / HPF", fill=(90, 90, 90))
    y += 24

    # Bacteria
    draw.text((40, y), "Bacteria", fill=(20, 20, 20))
    draw.text((330, y), random.choice(["Bacteria 1+", "Bacteria 2+", "Bacteria 3+", "Present"]), fill=(190, 15, 15))
    draw.text((540, y), "Non seen / Absent", fill=(90, 90, 90))
    y += 24

    # Crystals & Casts
    draw.text((40, y), "Casts / Crystals", fill=(20, 20, 20))
    draw.text((330, y), "Nil / None seen", fill=(20, 20, 20))
    draw.text((540, y), "None seen", fill=(90, 90, 90))
    y += 35

    # Clinical Comments
    draw.rectangle([(25, y), (width - 25, y + 75)], fill=(250, 251, 254), outline=(210, 215, 225))
    draw.text((38, y + 8), "CLINICAL INTERPRETATION / PATHOLOGY REMARKS:", fill=(30, 30, 30))
    draw.text((38, y + 30), f"- Significant pyuria ({pus_val} pus cells/HPF) with bacteriuria and positive nitrite.", fill=(180, 15, 15))
    draw.text((38, y + 50), "- Picture highly suggestive of active Urinary Tract Infection (UTI). Clinical correlation advised.", fill=(180, 15, 15))

    # Doctor Sign
    y = height - 100
    draw.rectangle([(width - 250, y), (width - 35, y + 65)], outline=(175, 190, 215), width=1)
    draw.text((width - 235, y + 8), "Dr. MEGHNA TYAGI, MD", fill=(30, 30, 30))
    draw.text((width - 235, y + 28), "Consultant Pathologist", fill=(80, 80, 80))
    draw.text((width - 235, y + 46), "[Himalayan Hospital Lab]", fill=(120, 140, 175))

    img.save(save_path, "JPEG", quality=88, optimize=True)

def worker(i):
    path = os.path.join(OUTPUT_DIR, f"report_urine_{i:04d}.jpg")
    render_urine_report(i, path)
    return i

def main():
    COUNT = 1000
    print("=" * 65)
    print(f"GENERATING 1,000 REALISTIC URINE TEST REPORTS")
    print(f"Destination: {OUTPUT_DIR}")
    print("=" * 65)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as ex:
        done = 0
        for _ in ex.map(worker, range(1, COUNT + 1), chunksize=25):
            done += 1
            if done % 200 == 0 or done == COUNT:
                print(f"  [OK] Generated {done}/{COUNT} Urine Reports ({done/COUNT*100:.0f}%)")

    print(f"[SUCCESS] 1,000 Urine Reports generated in {time.time() - t0:.1f}s!")

if __name__ == "__main__":
    main()
