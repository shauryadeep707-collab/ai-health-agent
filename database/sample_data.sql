-- =============================================================================
-- AI HEALTH AGENT — SAMPLE SEED DATA
-- Default Test Password for seed accounts: "Password123!"
-- BCrypt Hash: $2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge
-- =============================================================================

-- -----------------------------------------------------------------------------
-- USERS SEED
-- -----------------------------------------------------------------------------
-- Verified Doctor 1: Dr. Priya Sharma (Cardiology)
INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active, created_at)
VALUES ('u-doc-001', 'dr.priya.sharma@hospital.org', '$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge', 'DOCTOR', 'Dr. Priya Sharma', '+919876543210', 1, CURRENT_TIMESTAMP);

-- Verified Doctor 2: Dr. Rajesh K. Varma (Endocrinology)
INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active, created_at)
VALUES ('u-doc-002', 'dr.rajesh.varma@clinic.org', '$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge', 'DOCTOR', 'Dr. Rajesh K. Varma', '+919876543211', 1, CURRENT_TIMESTAMP);

-- Pending Doctor: Dr. Anita Deshmukh (General Medicine)
INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active, created_at)
VALUES ('u-doc-003', 'dr.anita.deshmukh@medcare.org', '$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge', 'DOCTOR', 'Dr. Anita Deshmukh', '+919876543212', 1, CURRENT_TIMESTAMP);

-- Patient 1: Rahul Mehta
INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active, created_at)
VALUES ('u-pat-001', 'rahul.mehta@email.com', '$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge', 'PATIENT', 'Rahul Mehta', '+919820011223', 1, CURRENT_TIMESTAMP);

-- Patient 2: Shaurya Deep
INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active, created_at)
VALUES ('u-pat-002', 'shauryadeep707@gmail.com', '$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge', 'PATIENT', 'Shaurya Deep', '+919876543299', 1, CURRENT_TIMESTAMP);

-- -----------------------------------------------------------------------------
-- DOCTOR PROFILES SEED
-- -----------------------------------------------------------------------------
INSERT INTO DOCTOR_PROFILES (doctor_id, user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years, clinic_address, consultation_fee, verification_status, verified_at, bio)
VALUES ('dp-001', 'u-doc-001', 'MBBS, MD (Cardiology), DM (Cardiology)', 'MCI-1998-04281', 'Maharashtra Medical Council', 'Maharashtra, India', 'Cardiology', 16, 'Heart Wellness Clinic, Nariman Point, Mumbai', 1200.00, 'VERIFIED', CURRENT_TIMESTAMP, 'Senior Interventional Cardiologist specializing in preventive cardiology, coronary artery disease, and hypertension management.');

INSERT INTO DOCTOR_PROFILES (doctor_id, user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years, clinic_address, consultation_fee, verification_status, verified_at, bio)
VALUES ('dp-002', 'u-doc-002', 'MBBS, MD (General Medicine), DNB (Endocrinology)', 'DMC-2005-18934', 'Delhi Medical Council', 'Delhi NCR, India', 'Endocrinology', 12, 'Metabolic Care Centre, Vasant Kunj, New Delhi', 1000.00, 'VERIFIED', CURRENT_TIMESTAMP, 'Consultant Endocrinologist specializing in Type 1 & 2 Diabetes, thyroid disorders, and metabolic health.');

INSERT INTO DOCTOR_PROFILES (doctor_id, user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years, clinic_address, consultation_fee, verification_status, verified_at, bio)
VALUES ('dp-003', 'u-doc-003', 'MBBS, DNB (Family Medicine)', 'KMC-2015-77210', 'Karnataka Medical Council', 'Karnataka, India', 'General Medicine', 7, 'Community Health Hub, Indiranagar, Bengaluru', 600.00, 'PENDING', NULL, 'Dedicated primary care physician focused on preventive health checkups and chronic illness monitoring.');

-- -----------------------------------------------------------------------------
-- DOCTOR VERIFICATIONS SEED
-- -----------------------------------------------------------------------------
INSERT INTO DOCTOR_VERIFICATIONS (verification_id, doctor_id, provider_source, oauth_state, digilocker_txn_id, doc_type, doc_uri, issuer_id, extracted_doctor_name, extracted_reg_no, extracted_council, extracted_qual, name_match_score, reg_no_match, status, review_notes)
VALUES ('dv-001', 'dp-001', 'DIGILOCKER', 'state_seed_001', 'DL-TXN-2026-99120', 'DOCREG', 'in.gov.digilocker.docreg:MCI-1998-04281', 'in.gov.nmc', 'Dr. Priya Sharma', 'MCI-1998-04281', 'Maharashtra Medical Council', 'MBBS, MD (Cardiology)', 100.00, 1, 'VERIFIED', 'Official digital certificate verified via DigiLocker API Setu issuer gateway. NMC registry cross-reference confirmed active status.');

INSERT INTO DOCTOR_VERIFICATIONS (verification_id, doctor_id, provider_source, oauth_state, digilocker_txn_id, doc_type, doc_uri, issuer_id, extracted_doctor_name, extracted_reg_no, extracted_council, extracted_qual, name_match_score, reg_no_match, status, review_notes)
VALUES ('dv-002', 'dp-002', 'DIGILOCKER', 'state_seed_002', 'DL-TXN-2026-88143', 'DOCREG', 'in.gov.digilocker.docreg:DMC-2005-18934', 'in.gov.dmc', 'Dr. Rajesh K. Varma', 'DMC-2005-18934', 'Delhi Medical Council', 'MBBS, MD', 100.00, 1, 'VERIFIED', 'DigiLocker issued credential authenticated successfully against Delhi Medical Council database.');

-- -----------------------------------------------------------------------------
-- PATIENT PROFILES SEED
-- -----------------------------------------------------------------------------
INSERT INTO PATIENT_PROFILES (patient_id, user_id, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_conditions)
VALUES ('pp-001', 'u-pat-001', TO_DATE('1988-06-15', 'YYYY-MM-DD'), 'MALE', 'B+', '+919820099887 (Spouse)', 'Penicillin', 'Mild Hypertension');

INSERT INTO PATIENT_PROFILES (patient_id, user_id, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_conditions)
VALUES ('pp-002', 'u-pat-002', TO_DATE('2002-01-01', 'YYYY-MM-DD'), 'MALE', 'O+', '+919876543299', 'None', 'None');

-- -----------------------------------------------------------------------------
-- USER CONSENTS SEED
-- -----------------------------------------------------------------------------
INSERT INTO USER_CONSENTS (consent_id, user_id, consent_type, is_granted, granted_at)
VALUES ('uc-001', 'u-pat-001', 'HEALTH_DATA_PROCESSING', 1, CURRENT_TIMESTAMP);

INSERT INTO USER_CONSENTS (consent_id, user_id, consent_type, is_granted, granted_at)
VALUES ('uc-002', 'u-pat-001', 'PRIVACY_POLICY', 1, CURRENT_TIMESTAMP);

-- -----------------------------------------------------------------------------
-- MEDICINE INFORMATION SEED
-- -----------------------------------------------------------------------------
INSERT INTO MEDICINE_INFORMATION (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
VALUES (
    'med-001', 'Crocin / Dolo 650', 'Paracetamol (Acetaminophen)', 'Analgesic & Antipyretic',
    'Relief of mild to moderate pain (headache, body ache, toothache) and reduction of fever.',
    'Do not exceed 4,000 mg in 24 hours. Avoid alcohol consumption during therapy to minimize hepatic risk.',
    'Severe active liver disease, acute liver impairment, severe renal insufficiency.',
    'Nausea, rash, rare allergic reactions. Hepatotoxicity in overdose.',
    'Immediate medical attention required if rash, swelling of lips/face, or breathing difficulty occurs.',
    0, 'WHO Model List of Essential Medicines & US FDA Drug Safety Guidelines',
    '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=paracetamol"},{"store":"Apollo Pharmacy","url":"https://www.apollopharmacy.in/search-medicines/paracetamol"},{"store":"Netmeds","url":"https://www.netmeds.com/catalogsearch/result/paracetamol"}]'
);

INSERT INTO MEDICINE_INFORMATION (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
VALUES (
    'med-002', 'Glycomet 500', 'Metformin Hydrochloride', 'Biguanide Antidiabetic',
    'Management of Type 2 Diabetes Mellitus to improve glycemic control in conjunction with diet and exercise.',
    'Monitor renal function (eGFR) regularly. Temporarily discontinue prior to iodinated radiocontrast procedures.',
    'Severe renal impairment (eGFR < 30 mL/min), acute metabolic acidosis, severe diabetic ketoacidosis, chronic heart failure.',
    'Gastrointestinal discomfort, diarrhea, nausea, metallic taste, decreased vitamin B12 absorption.',
    'Rare risk of lactic acidosis; report unusual muscle pain, severe drowsiness, or heavy breathing.',
    1, 'American Diabetes Association & CDSCO Approved Drug Compendium',
    '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=metformin"},{"store":"Apollo Pharmacy","url":"https://www.apollopharmacy.in/search-medicines/metformin"}]'
);

INSERT INTO MEDICINE_INFORMATION (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
VALUES (
    'med-003', 'Lipitor / Atorva', 'Atorvastatin Calcium', 'HMG-CoA Reductase Inhibitor (Statin)',
    'Lowers LDL cholesterol and triglycerides, reduces the risk of stroke, myocardial infarction, and cardiac events.',
    'Periodic liver function tests advised. Report unexplained muscle aches, tenderness, or weakness immediately.',
    'Active liver disease, unexplained persistent elevations of serum transaminases, pregnancy, lactation.',
    'Headache, myalgia, diarrhea, elevated transaminases, dyspepsia.',
    'Hypersensitivity reactions including anaphylaxis, angioedema, and bullous rashes.',
    1, 'National Institutes of Health (NIH) & European Society of Cardiology Guidelines',
    '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=atorvastatin"},{"store":"Netmeds","url":"https://www.netmeds.com/catalogsearch/result/atorvastatin"}]'
);

INSERT INTO MEDICINE_INFORMATION (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
VALUES (
    'med-004', 'Augmentin 625 Duo', 'Amoxicillin + Clavulanic Acid', 'Beta-Lactam Antibiotic',
    'Treatment of bacterial infections including respiratory tract, urinary tract, skin, and dental infections.',
    'Complete the entire prescribed course even if symptoms improve to prevent antimicrobial resistance.',
    'History of penicillin allergy, history of amoxicillin-associated cholestatic jaundice/hepatic dysfunction.',
    'Diarrhea, nausea, vomiting, candidiasis, mild rash.',
    'CONTRAINDICATED in patients with known hypersensitivity to penicillins or beta-lactam antibiotics.',
    1, 'Infectious Diseases Society of America (IDSA) Treatment Protocols',
    '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=amoxicillin+clavulanate"},{"store":"Apollo Pharmacy","url":"https://www.apollopharmacy.in/search-medicines/augmentin"}]'
);

INSERT INTO MEDICINE_INFORMATION (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
VALUES (
    'med-005', 'Omez 20', 'Omeprazole', 'Proton Pump Inhibitor (PPI)',
    'Treatment of gastroesophageal reflux disease (GERD), peptic ulcer disease, and Zollinger-Ellison syndrome.',
    'Long-term use may reduce magnesium levels and bone density. Best taken 30-60 minutes before breakfast.',
    'Known hypersensitivity to omeprazole or substituted benzimidazoles; concomitant use with rilpivirine.',
    'Headache, abdominal pain, constipation, flatulence, nausea.',
    'Report severe watery diarrhea or signs of hypomagnesemia immediately.',
    0, 'British National Formulary (BNF) & FDA Package Insert',
    '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=omeprazole"},{"store":"Netmeds","url":"https://www.netmeds.com/catalogsearch/result/omeprazole"}]'
);

-- -----------------------------------------------------------------------------
-- DRUG INTERACTIONS SEED
-- -----------------------------------------------------------------------------
INSERT INTO DRUG_INTERACTIONS (interaction_id, medicine_a_id, medicine_b_id, severity, interaction_desc, clinical_advice)
VALUES (
    'di-001', 'med-003', 'med-004', 'MODERATE',
    'Concurrent administration of certain antibiotics with statins may alter statin metabolism or increase serum concentrations.',
    'Monitor for symptoms of statin-induced myopathy (muscle pain or weakness). Clinician consultation recommended.'
);

-- -----------------------------------------------------------------------------
-- HEALTH PRODUCTS SEED
-- -----------------------------------------------------------------------------
INSERT INTO HEALTH_PRODUCTS (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
VALUES (
    'prod-001', 'Omron HEM-7120 Fully Automatic Digital Blood Pressure Monitor', 'Diagnostic Devices',
    'Clinically validated upper arm BP monitor with Intellisense Technology, hypertension indicator, and cuff wrapping guide.',
    2249.00, 'INR', 1, 'Omron Official Healthcare Store', 'https://www.amazon.in/dp/B00J3C2424', 1
);

INSERT INTO HEALTH_PRODUCTS (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
VALUES (
    'prod-002', 'Accu-Chek Active Blood Glucose Glucometer Kit with 10 Strips', 'Diabetes Care',
    'Accurate blood sugar monitoring system with 5-second test time, pre/post-meal markers, and ISO 15197 compliance.',
    1449.00, 'INR', 1, 'Roche Diabetes Care', 'https://www.amazon.in/dp/B008VUN45Y', 1
);

INSERT INTO HEALTH_PRODUCTS (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
VALUES (
    'prod-003', 'Beurer PO 30 Fingertip Pulse Oximeter', 'Respiratory & Vitals',
    'Measures arterial oxygen saturation (SpO2) and heart rate (pulse). Easy-to-read color display with 4 view options.',
    1899.00, 'INR', 1, 'Beurer Medical GmbH', 'https://www.amazon.in/dp/B004323ZLE', 1
);

INSERT INTO HEALTH_PRODUCTS (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
VALUES (
    'prod-004', 'Philips Respironics Sami the Seal Pediatric Compressor Nebulizer', 'Respiratory Care',
    'Child-friendly pediatric nebulizer delivering fast and effective aerosol medication treatment with SideStream technology.',
    3290.00, 'INR', 1, 'Philips Healthcare', 'https://www.amazon.in/dp/B007X64B4Q', 1
);

INSERT INTO HEALTH_PRODUCTS (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
VALUES (
    'prod-005', 'Dr. Morepen Digital Flexi-Tip Clinical Thermometer', 'Diagnostic Devices',
    'Accurate oral, rectal, and underarm temperature measurement with fever alarm, auto turn-off, and waterproof tip.',
    249.00, 'INR', 1, 'Dr. Morepen Health Store', 'https://www.amazon.in/dp/B00J65A5L0', 1
);

-- -----------------------------------------------------------------------------
-- MEDICAL REPORT & ANALYSIS SEED
-- -----------------------------------------------------------------------------
INSERT INTO MEDICAL_REPORTS (report_id, patient_id, original_filename, stored_filename, file_path, file_size_bytes, file_type, test_type, report_date, upload_timestamp, is_confirmed_by_patient)
VALUES (
    'rep-001', 'pp-001', 'Complete_Lipid_Profile_2026.pdf', 'rep-001_seed_lipid.pdf', 'uploads/rep-001_seed_lipid.pdf',
    245760, 'application/pdf', 'Comprehensive Lipid Profile', TO_DATE('2026-09-15', 'YYYY-MM-DD'), CURRENT_TIMESTAMP, 1
);

INSERT INTO REPORT_ANALYSES (analysis_id, report_id, ai_provider, summary_plain_en, clinical_notes, abnormal_count, urgent_flags, risk_level, recommendations)
VALUES (
    'ana-001', 'rep-001', 'Gemini AI Health Engine',
    'Your comprehensive lipid panel shows an elevated Total Cholesterol (238 mg/dL) and LDL "Bad" Cholesterol (154 mg/dL). HDL "Good" Cholesterol and Triglycerides are within safe normal ranges. Note: Slightly elevated cholesterol does not automatically constitute a diagnosis of heart disease, but indicates a need for proactive lifestyle optimizations.',
    'Mild-to-moderate hypercholesterolemia. ASCVD risk calculation indicated in context of blood pressure history.',
    2, 'No acute or critical laboratory findings requiring emergency medical intervention.', 'MODERATE',
    '1. Consult your primary physician or cardiologist regarding cardiovascular risk evaluation.\n2. Adopt a heart-healthy diet low in saturated fats and refined sugars.\n3. Maintain 150 minutes of moderate aerobic physical activity per week.\n4. Repeat fasting lipid panel in 3 months.'
);

INSERT INTO REPORT_TEST_VALUES (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
VALUES ('val-001', 'rep-001', 'Total Cholesterol', 238.0, '238', 'mg/dL', 125.0, 200.0, '< 200 mg/dL', 'HIGH');

INSERT INTO REPORT_TEST_VALUES (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
VALUES ('val-002', 'rep-001', 'LDL Cholesterol (Direct)', 154.0, '154', 'mg/dL', 0.0, 100.0, '< 100 mg/dL', 'HIGH');

INSERT INTO REPORT_TEST_VALUES (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
VALUES ('val-003', 'rep-001', 'HDL Cholesterol', 48.0, '48', 'mg/dL', 40.0, 60.0, '> 40 mg/dL', 'NORMAL');

INSERT INTO REPORT_TEST_VALUES (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
VALUES ('val-004', 'rep-001', 'Serum Triglycerides', 138.0, '138', 'mg/dL', 50.0, 150.0, '< 150 mg/dL', 'NORMAL');

-- -----------------------------------------------------------------------------
-- APPOINTMENTS SEED
-- -----------------------------------------------------------------------------
INSERT INTO APPOINTMENTS (appointment_id, patient_id, doctor_id, appointment_date, slot_time, status, reason_for_visit, doctor_notes)
VALUES (
    'apt-001', 'pp-001', 'dp-001', TO_DATE('2026-11-05', 'YYYY-MM-DD'), '10:30 AM', 'CONFIRMED',
    'Follow-up evaluation on recent lipid profile report and lifestyle guidance.', 'Patient has brought recent lab report rep-001.'
);

-- -----------------------------------------------------------------------------
-- AUDIT LOGS SEED
-- -----------------------------------------------------------------------------
INSERT INTO AUDIT_LOGS (log_id, actor_user_id, event_type, target_resource, resource_id, event_status, details_json, ip_address)
VALUES (
    'aud-001', 'u-doc-001', 'DIGILOCKER_DOCTOR_VERIFIED', 'DOCTOR_PROFILES', 'dp-001', 'SUCCESS',
    '{"issuer":"in.gov.nmc","doc_type":"DOCREG","reg_no":"MCI-1998-04281","match_score":100}', '127.0.0.1'
);

COMMIT;
