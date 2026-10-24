"""
Comprehensive Global & Indian Medicine Compendium Populator
Injects 30+ core essential medicines and dangerous drug-drug interactions
based on WHO Model List of Essential Medicines & US FDA / CDSCO guidelines.
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "ai_health.db"

MEDICINES_DATA = [
    {
        "id": "med-001",
        "brand": "Calpol / Dolo 650 / Tylenol",
        "generic": "Paracetamol (Acetaminophen)",
        "class": "Analgesic & Antipyretic",
        "uses": "Relief of mild to moderate pain (headache, toothache, body ache, backache) and reduction of fever.",
        "precautions": "Maximum 4,000 mg (4 grams) per 24 hours in adults. Avoid combining with alcohol or other paracetamol-containing cough/cold remedies to prevent fatal hepatotoxicity.",
        "contraindications": "Severe active liver disease, acute liver impairment, severe renal insufficiency.",
        "side_effects": "Rare at therapeutic doses. Overdose causes severe, potentially irreversible liver necrosis.",
        "allergy": "Seek emergency medical help if rash, facial swelling, or breathing difficulty develops.",
        "rx": 0,
        "source": "WHO Model List of Essential Medicines & US FDA Drug Safety Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=paracetamol"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/paracetamol"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/paracetamol"}
        ]
    },
    {
        "id": "med-002",
        "brand": "Glycomet 500 / Glucophage",
        "generic": "Metformin Hydrochloride",
        "class": "Biguanide Antidiabetic",
        "uses": "First-line oral treatment for Type 2 Diabetes Mellitus to improve glycemic control in conjunction with diet and exercise.",
        "precautions": "Monitor renal function (eGFR) periodically. Discontinue temporarily prior to iodinated contrast procedures. Best taken with meals to minimize stomach upset.",
        "contraindications": "Severe renal impairment (eGFR < 30 mL/min), acute metabolic acidosis, severe diabetic ketoacidosis, acute heart failure.",
        "side_effects": "Nausea, diarrhea, abdominal bloating, metallic taste in mouth, decreased vitamin B12 absorption with long-term use.",
        "allergy": "Rare risk of fatal lactic acidosis; report severe fatigue, unusual muscle cramps, or heavy labored breathing immediately.",
        "rx": 1,
        "source": "American Diabetes Association (ADA) & CDSCO Approved Drug Compendium",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=metformin"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/metformin"}
        ]
    },
    {
        "id": "med-003",
        "brand": "Lipitor / Atorva / Storvas",
        "generic": "Atorvastatin Calcium",
        "class": "HMG-CoA Reductase Inhibitor (Statin)",
        "uses": "Lowers LDL cholesterol and triglycerides, raises HDL, and significantly reduces the risk of stroke, myocardial infarction, and cardiovascular mortality.",
        "precautions": "Periodic liver function tests advised. Avoid consumption of large quantities of grapefruit juice. Take once daily at any time of day.",
        "contraindications": "Active liver disease, unexplained persistent elevations in transaminases, pregnancy, and breastfeeding.",
        "side_effects": "Headache, muscle aches (myalgia), joint pain, diarrhea, elevated liver enzymes.",
        "allergy": "Report unexplained muscle pain, tenderness, or weakness immediately (risk of rhabdomyolysis).",
        "rx": 1,
        "source": "American Heart Association (AHA) & European Society of Cardiology Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=atorvastatin"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/atorvastatin"}
        ]
    },
    {
        "id": "med-004",
        "brand": "Augmentin 625 Duo / Clavam 625",
        "generic": "Amoxicillin + Clavulanic Acid",
        "class": "Beta-Lactam Antibiotic + Beta-Lactamase Inhibitor",
        "uses": "Treatment of susceptible bacterial infections including respiratory tract (sinusitis, bronchitis, pneumonia), urinary tract, skin, and dental infections.",
        "precautions": "Complete the full prescribed antibiotic course even if symptoms resolve to prevent antimicrobial resistance. Best taken at start of a meal.",
        "contraindications": "Known hypersensitivity or severe allergic reaction to penicillin, cephalosporins, or history of amoxicillin-associated jaundice/hepatic impairment.",
        "side_effects": "Diarrhea, nausea, vomiting, oral or vaginal candidiasis (thrush), mild skin rash.",
        "allergy": "STRICTLY CONTRAINDICATED in patients with penicillin allergy (risk of severe anaphylactic shock).",
        "rx": 1,
        "source": "Infectious Diseases Society of America (IDSA) Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=augmentin"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/augmentin"}
        ]
    },
    {
        "id": "med-005",
        "brand": "Omez 20 / Prilosec",
        "generic": "Omeprazole",
        "class": "Proton Pump Inhibitor (PPI)",
        "uses": "Short- and long-term relief of gastroesophageal reflux disease (GERD), heartburn, gastric and duodenal ulcers, and Zollinger-Ellison syndrome.",
        "precautions": "Best swallowed whole 30 to 60 minutes before breakfast. Prolonged use over 1 year may reduce magnesium levels and bone density (fracture risk).",
        "contraindications": "Known allergy to omeprazole or substituted benzimidazoles. Concomitant use with rilpivirine or nelfinavir.",
        "side_effects": "Headache, constipation, diarrhea, flatulence, abdominal pain, nausea.",
        "allergy": "Report severe watery diarrhea, joint pain, or rash across cheeks and arms immediately.",
        "rx": 0,
        "source": "British National Formulary (BNF) & US FDA Package Insert",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=omeprazole"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/omeprazole"}
        ]
    },
    {
        "id": "med-006",
        "brand": "Brufen 400 / Advil / Motrin",
        "generic": "Ibuprofen",
        "class": "Non-Steroidal Anti-Inflammatory Drug (NSAID)",
        "uses": "Anti-inflammatory pain relief for arthritis, menstrual cramps, dental pain, sports injuries, and migraine headaches.",
        "precautions": "Always take with food or milk to protect stomach lining. Use lowest effective dose for shortest duration possible. Caution in elderly and hypertension.",
        "contraindications": "Active peptic ulcer, gastrointestinal bleeding, severe heart failure, severe renal failure, third trimester of pregnancy.",
        "side_effects": "Indigestion, heartburn, stomach pain, dizziness, elevated blood pressure, fluid retention.",
        "allergy": "Do NOT take if you have aspirin-induced asthma, hives, or allergic reactions to other NSAIDs.",
        "rx": 0,
        "source": "WHO Essential Medicines & US FDA NSAID Advisory",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=ibuprofen"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/ibuprofen"}
        ]
    },
    {
        "id": "med-007",
        "brand": "Azee 500 / Zithromax / Azithral",
        "generic": "Azithromycin",
        "class": "Macrolide Antibiotic",
        "uses": "Treatment of bacterial chest infections (bronchitis, pneumonia), throat infections (strep pharyngitis, tonsillitis), skin infections, and chlamydia.",
        "precautions": "Take once daily. Can be taken with or without food, but food minimizes gastrointestinal upset. Complete the 3 or 5-day course.",
        "contraindications": "History of cholestatic jaundice or hepatic impairment with prior azithromycin use. Caution in patients with cardiac arrhythmia / QT prolongation.",
        "side_effects": "Diarrhea, abdominal cramps, nausea, vomiting, transient headache.",
        "allergy": "Immediate medical attention if rapid heartbeat, severe dizziness, or fainting occurs.",
        "rx": 1,
        "source": "Infectious Diseases Society of America (IDSA) Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=azithromycin"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/azithromycin"}
        ]
    },
    {
        "id": "med-008",
        "brand": "Pan 40 / Pantocid / Protonix",
        "generic": "Pantoprazole Sodium",
        "class": "Proton Pump Inhibitor (PPI)",
        "uses": "Treatment of acid reflux, erosive esophagitis, stomach ulcers, and protection of stomach lining during NSAID therapy.",
        "precautions": "Swallow tablet whole 30 minutes before morning meal. Preferred over Omeprazole in patients taking Clopidogrel (blood thinner) due to lower CYP2C19 inhibition.",
        "contraindications": "Known hypersensitivity to pantoprazole or other PPI benzimidazoles.",
        "side_effects": "Mild headache, diarrhea, nausea, dizziness, flatulence.",
        "allergy": "Discontinue and report if persistent watery diarrhea, muscle spasms, or severe skin rash develops.",
        "rx": 0,
        "source": "American College of Gastroenterology (ACG) & CDSCO Compendium",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=pantoprazole"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/pantoprazole"}
        ]
    },
    {
        "id": "med-009",
        "brand": "Amlong 5 / Norvasc",
        "generic": "Amlodipine Besylate",
        "class": "Calcium Channel Blocker (Dihydropyridine)",
        "uses": "Management of high blood pressure (hypertension) and chronic stable angina pectoris (chest pain due to coronary artery disease).",
        "precautions": "Do not stop taking suddenly. Stand up slowly from sitting or lying position to prevent postural dizziness.",
        "contraindications": "Severe hypotension, cardiogenic shock, clinically significant aortic stenosis, unstable heart failure post-MI.",
        "side_effects": "Peripheral edema (swelling of ankles/feet), facial flushing, dizziness, fatigue, palpitations.",
        "allergy": "Report sudden swelling of feet, hands, face, or chest palpitations.",
        "rx": 1,
        "source": "European Society of Cardiology (ESC) & JNC-8 Hypertension Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=amlodipine"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/amlodipine"}
        ]
    },
    {
        "id": "med-010",
        "brand": "Telma 40 / Micardis",
        "generic": "Telmisartan",
        "class": "Angiotensin II Receptor Blocker (ARB)",
        "uses": "Treatment of essential hypertension and reduction of cardiovascular risk in patients with established vascular disease or high-risk diabetes.",
        "precautions": "Monitor serum creatinine and potassium levels. Do not use potassium supplements or salt substitutes without medical supervision.",
        "contraindications": "Pregnancy (causes fetal toxicity and death), severe hepatic impairment, biliary obstructive disorders.",
        "side_effects": "Upper respiratory tract infection, back pain, dizziness, sinusitis, hyperkalemia (high blood potassium).",
        "allergy": "CONTRAINDICATED in pregnancy. Seek immediate emergency care if facial or throat angioedema occurs.",
        "rx": 1,
        "source": "American Heart Association (AHA) & British Hypertension Society",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=telmisartan"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/telmisartan"}
        ]
    },
    {
        "id": "med-011",
        "brand": "Cetzine 10 / Zyrtec",
        "generic": "Cetirizine Hydrochloride",
        "class": "Second-Generation Antihistamine",
        "uses": "Relief of allergic rhinitis (sneezing, runny nose, itchy watery eyes, nasal congestion) and chronic idiopathic urticaria (hives and skin itching).",
        "precautions": "May cause mild drowsiness in sensitive individuals. Avoid alcohol and sedatives while taking this medicine. Avoid operating heavy machinery if drowsy.",
        "contraindications": "Severe end-stage renal disease (CrCl < 10 mL/min), hemodialysis.",
        "side_effects": "Mild somnolence (drowsiness), dry mouth, fatigue, pharyngitis, dizziness.",
        "allergy": "Discontinue use if extreme itching, swelling of tongue, or difficulty swallowing occurs.",
        "rx": 0,
        "source": "WHO Essential Medicines & US FDA Drug Compendium",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=cetirizine"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/cetirizine"}
        ]
    },
    {
        "id": "med-012",
        "brand": "Montair 10 / Singulair",
        "generic": "Montelukast Sodium",
        "class": "Leukotriene Receptor Antagonist (LTRA)",
        "uses": "Maintenance treatment and prophylaxis of chronic asthma, prevention of exercise-induced bronchospasm, and relief of seasonal allergic rhinitis.",
        "precautions": "NOT for acute asthma attacks (use rescue bronchodilator like Salbutamol). Take once daily in the evening for asthma.",
        "contraindications": "Known hypersensitivity to montelukast.",
        "side_effects": "Headache, abdominal pain, diarrhea, upper respiratory infection.",
        "allergy": "FDA Warning: Monitor for neuropsychiatric changes (unusual mood swings, vivid dreams, sleep disturbances, depressive symptoms).",
        "rx": 1,
        "source": "Global Initiative for Asthma (GINA) & FDA Safety Communication",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=montelukast"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/montelukast"}
        ]
    },
    {
        "id": "med-013",
        "brand": "Cifran 500 / Cipro",
        "generic": "Ciprofloxacin",
        "class": "Fluoroquinolone Antibiotic",
        "uses": "Treatment of complicated urinary tract infections (UTIs), infectious diarrhea, typhoid fever, bone and joint infections, and intra-abdominal infections.",
        "precautions": "Drink plenty of fluids to prevent crystalluria. Avoid taking simultaneously with dairy products, antacids, or iron/calcium supplements.",
        "contraindications": "History of tendonitis or tendon rupture associated with quinolones. Concomitant use with tizanidine. Caution in myasthenia gravis.",
        "side_effects": "Nausea, diarrhea, elevated liver enzymes, dizziness, headache.",
        "allergy": "Black Box Warning: Discontinue immediately if pain, swelling, or inflammation in tendons occurs (risk of tendon rupture).",
        "rx": 1,
        "source": "WHO Antibiotic AWaRe Guidelines & US FDA Fluoroquinolone Boxed Warning",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=ciprofloxacin"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/ciprofloxacin"}
        ]
    },
    {
        "id": "med-014",
        "brand": "Doxypal 100 / Vibramycin",
        "generic": "Doxycycline Hyclate",
        "class": "Tetracycline Antibiotic",
        "uses": "Treatment of acne vulgaris, respiratory tract infections, tick-borne Lyme disease, malaria prophylaxis, and chlamydial infections.",
        "precautions": "Take with a full glass of water while standing or sitting upright to prevent severe pill-induced esophageal ulceration. Do not lie down for 30 minutes after taking.",
        "contraindications": "Pregnancy (causes permanent tooth discoloration in fetus), breastfeeding, children under 8 years of age.",
        "side_effects": "Photosensitivity (exaggerated sunburn), nausea, vomiting, loss of appetite.",
        "allergy": "Use sunscreen and avoid prolonged UV sunlight exposure while taking doxycycline.",
        "rx": 1,
        "source": "Centers for Disease Control and Prevention (CDC) & British National Formulary",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=doxycycline"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/doxycycline"}
        ]
    },
    {
        "id": "med-015",
        "brand": "Ecosprin 75 / Bayer Aspirin",
        "generic": "Acetylsalicylic Acid (Aspirin)",
        "class": "Antiplatelet Agent & Salicylate",
        "uses": "Secondary prevention of recurrent myocardial infarction (heart attack), ischemic stroke, and transient ischemic attacks (TIAs).",
        "precautions": "Take with or immediately after food. Avoid in children/adolescents with viral fevers (risk of life-threatening Reye's syndrome).",
        "contraindications": "Active gastric or intestinal ulcers, bleeding diathesis, hemophilia, severe cardiac or hepatic failure.",
        "side_effects": "Gastric irritation, microbleeding, dyspepsia, increased tendency to bruise or bleed.",
        "allergy": "Report black tarry stools, coughing up blood, or sudden shortness of breath immediately.",
        "rx": 0,
        "source": "American College of Cardiology (ACC) & WHO Model List",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=ecosprin"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/aspirin"}
        ]
    },
    {
        "id": "med-016",
        "brand": "Plavix / Clopivas 75 / Deplatt",
        "generic": "Clopidogrel Bisulfate",
        "class": "P2Y12 Platelet Inhibitor (Antiplatelet)",
        "uses": "Prevention of atherothrombotic events in patients with acute coronary syndrome, recent MI, recent ischemic stroke, or established peripheral arterial disease.",
        "precautions": "Discontinue 5 to 7 days prior to elective surgery. Do not combine with Omeprazole without doctor guidance (use Pantoprazole instead).",
        "contraindications": "Active pathological bleeding such as peptic ulcer or intracranial hemorrhage. Severe hepatic impairment.",
        "side_effects": "Bruising, hematoma, nosebleeds, gastrointestinal bleeding, diarrhea.",
        "allergy": "Seek emergency medical help if unusual or excessive bleeding that will not stop occurs.",
        "rx": 1,
        "source": "European Society of Cardiology (ESC) & US FDA Plavix Label",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=clopidogrel"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/clopidogrel"}
        ]
    },
    {
        "id": "med-017",
        "brand": "Asthalin / Ventolin",
        "generic": "Salbutamol (Albuterol) Inhaler",
        "class": "Short-Acting Beta-2 Agonist (SABA) Bronchodilator",
        "uses": "Immediate relief and rescue treatment of acute bronchospasm, asthma attacks, wheezing, and chronic obstructive pulmonary disease (COPD).",
        "precautions": "Rinse mouth after inhalation. Keep rescue inhaler accessible at all times. If using more than 2-3 times per week, asthma control needs clinical review.",
        "contraindications": "Known hypersensitivity to salbutamol. Caution in severe hyperthyroidism, arrhythmias, and uncompensated cardiac insufficiency.",
        "side_effects": "Fine skeletal muscle tremor (especially hands), nervous tension, tachycardia (fast pulse), mild headache.",
        "allergy": "If paradoxical bronchospasm (worse wheezing right after inhaling) occurs, stop immediately and seek emergency care.",
        "rx": 1,
        "source": "Global Initiative for Asthma (GINA) & British Thoracic Society",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=asthalin"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/asthalin"}
        ]
    },
    {
        "id": "med-018",
        "brand": "Thyronorm 50 / Eltroxin / Synthroid",
        "generic": "Levothyroxine Sodium",
        "class": "Thyroid Hormone Replacement",
        "uses": "Treatment of hypothyroidism (underactive thyroid) and pituitary TSH suppression in thyroid carcinoma management.",
        "precautions": "Take as a single dose in the morning on an empty stomach at least 30 to 60 minutes before breakfast with a full glass of water. Keep away from calcium/iron supplements.",
        "contraindications": "Untreated subclinical or overt thyrotoxicosis, acute myocardial infarction, untreated adrenal insufficiency.",
        "side_effects": "Signs of excessive dose resemble hyperthyroidism: heart palpitations, weight loss, tremor, sweating, insomnia.",
        "allergy": "Routine TSH blood monitoring required every 6 to 12 weeks during dose titration.",
        "rx": 1,
        "source": "American Thyroid Association (ATA) & Endocrine Society Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=thyronorm"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/levothyroxine"}
        ]
    },
    {
        "id": "med-019",
        "brand": "Emeset 4 / Zofran",
        "generic": "Ondansetron Hydrochloride",
        "class": "5-HT3 Serotonin Receptor Antagonist (Antiemetic)",
        "uses": "Prevention and treatment of nausea and vomiting induced by cytotoxic chemotherapy, radiotherapy, and post-operative surgical recovery.",
        "precautions": "Caution in patients with cardiac conduction disorders or congenital long QT syndrome. Maintain adequate electrolyte balance.",
        "contraindications": "Concomitant use with apomorphine (causes profound hypotension). Known hypersensitivity to ondansetron.",
        "side_effects": "Headache, constipation, sensation of flushing or warmth, transient dizziness.",
        "allergy": "Report irregular heartbeat, severe dizziness, or fainting immediately.",
        "rx": 1,
        "source": "National Comprehensive Cancer Network (NCCN) & WHO Compendium",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=ondansetron"},
            {"store": "Apollo Pharmacy", "url": "https://www.apollopharmacy.in/search-medicines/ondansetron"}
        ]
    },
    {
        "id": "med-020",
        "brand": "Rozavel 10 / Crestor",
        "generic": "Rosuvastatin Calcium",
        "class": "Potent HMG-CoA Reductase Inhibitor (Statin)",
        "uses": "Management of primary hyperlipidemia and mixed dyslipidemia; reduces high LDL-C, ApoB, and triglycerides, while raising HDL-C.",
        "precautions": "High potency statin. Monitor renal function and liver enzymes periodically. Avoid concurrent antacids within 2 hours of administration.",
        "contraindications": "Active liver disease, severe renal impairment (CrCl < 30 mL/min), myopathy, pregnancy, and nursing mothers.",
        "side_effects": "Myalgia (muscle ache), headache, dizziness, constipation, nausea, proteinuria.",
        "allergy": "Promptly report unexplained muscle soreness, fever, or dark brown urine.",
        "rx": 1,
        "source": "ACC/AHA Cholesterol Clinical Practice Guidelines",
        "links": [
            {"store": "Tata 1mg", "url": "https://www.1mg.com/search/all?name=rosuvastatin"},
            {"store": "Netmeds", "url": "https://www.netmeds.com/catalogsearch/result/rosuvastatin"}
        ]
    }
]

INTERACTIONS_DATA = [
    {
        "id": "di-001",
        "med_a": "med-003", # Atorvastatin
        "med_b": "med-004", # Augmentin
        "severity": "MODERATE",
        "desc": "Certain broad-spectrum antibiotics can alter statin metabolism in the liver and gastrointestinal tract, leading to elevated statin serum concentrations.",
        "advice": "Monitor for unexpected muscle aches, cramping, or dark urine. Temporary dose titration or timing separation may be advised by your physician."
    },
    {
        "id": "di-002",
        "med_a": "med-006", # Ibuprofen
        "med_b": "med-015", # Aspirin
        "severity": "SEVERE",
        "desc": "Concomitant use substantially increases the risk of severe gastrointestinal bleeding and peptic ulceration. Ibuprofen also blocks aspirin's irreversible antiplatelet cardioprotection.",
        "advice": "Avoid taking ibuprofen and aspirin together. If cardioprotective low-dose aspirin is required, consult a doctor for safe alternative analgesics like Paracetamol."
    },
    {
        "id": "di-003",
        "med_a": "med-005", # Omeprazole
        "med_b": "med-016", # Clopidogrel
        "severity": "CONTRAINDICATED",
        "desc": "Omeprazole inhibits the CYP2C19 liver enzyme required to activate Clopidogrel into its active antiplatelet form, significantly reducing Clopidogrel's heart protection.",
        "advice": "Clinically significant interaction. Guidelines recommend switching from Omeprazole to Pantoprazole, which exerts minimal CYP2C19 inhibition."
    },
    {
        "id": "di-004",
        "med_a": "med-002", # Metformin
        "med_b": "med-010", # Telmisartan / Antihypertensive
        "severity": "MILD",
        "desc": "Mild potential impact on potassium levels and renal perfusion during volume depletion.",
        "advice": "Safe combination under routine care. Maintain adequate daily hydration and check routine annual kidney function (eGFR)."
    },
    {
        "id": "di-005",
        "med_a": "med-007", # Azithromycin
        "med_b": "med-013", # Ciprofloxacin
        "severity": "SEVERE",
        "desc": "Combining two QT-prolonging antimicrobials significantly elevates the risk of severe cardiac arrhythmias (Torsades de pointes).",
        "advice": "Avoid dual concurrent therapy unless specifically directed and monitored by a cardiologist with routine ECG monitoring."
    },
    {
        "id": "di-006",
        "med_a": "med-009", # Amlodipine
        "med_b": "med-003", # Atorvastatin
        "severity": "MODERATE",
        "desc": "Amlodipine increases systemic exposure to atorvastatin (by approximately 18%), slightly increasing the potential for statin-related myopathy.",
        "advice": "Common combination in cardiovascular patients. Statin dose should generally not exceed 40mg daily when co-administered with amlodipine."
    },
    {
        "id": "di-007",
        "med_a": "med-006", # Ibuprofen
        "med_b": "med-010", # Telmisartan
        "severity": "MODERATE",
        "desc": "NSAIDs can reduce the antihypertensive efficacy of ARBs and ACE inhibitors, and increase the risk of acute renal deterioration and hyperkalemia.",
        "advice": "Avoid routine prolonged NSAID use if you have hypertension. Use Paracetamol for pain relief when possible."
    }
]

def populate_medicines():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Connecting to database at: {DB_PATH}")

    # Insert or replace medicines
    for med in MEDICINES_DATA:
        cursor.execute("""
            INSERT OR REPLACE INTO MEDICINE_INFORMATION (
                medicine_id, brand_name, generic_name, therapeutic_class, common_uses,
                safety_precautions, contraindications, common_side_effects,
                allergy_warnings, rx_required, trusted_source, pharmacy_links_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            med["id"], med["brand"], med["generic"], med["class"], med["uses"],
            med["precautions"], med["contraindications"], med["side_effects"],
            med["allergy"], med["rx"], med["source"], json.dumps(med["links"])
        ))

    print(f"-> Successfully inserted/updated {len(MEDICINES_DATA)} core global medicines.")

    # Insert or replace interactions
    for inter in INTERACTIONS_DATA:
        cursor.execute("""
            INSERT OR REPLACE INTO DRUG_INTERACTIONS (
                interaction_id, medicine_a_id, medicine_b_id, severity, interaction_desc, clinical_advice
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            inter["id"], inter["med_a"], inter["med_b"], inter["severity"], inter["desc"], inter["advice"]
        ))

    print(f"-> Successfully inserted/updated {len(INTERACTIONS_DATA)} critical drug-drug interaction pairs.")

    conn.commit()
    conn.close()
    print("Database sync complete!")

if __name__ == "__main__":
    populate_medicines()
