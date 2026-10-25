import os
import re
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from backend.config import Config

logger = logging.getLogger(__name__)

# Check if oracledb is available
try:
    import oracledb
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    logger.warning("oracledb module not installed. Running in SQLite/Postgres mode.")

# Check if psycopg2 (PostgreSQL / Supabase) is available
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("psycopg2 module not installed.")

class DatabaseManager:
    """
    Manages database connections for Supabase / PostgreSQL, Oracle Database, and SQLite local fallback.
    Provides uniform execution with named parameter binding (:param_name).
    """
    def __init__(self, config=None):
        self.config = config or Config
        self.db_type = self.config.DB_TYPE
        self.oracle_pool = None
        self.pg_pool = None
        self._init_backend()

    def _init_backend(self):
        if self.db_type in ("postgres", "postgresql", "supabase"):
            if not POSTGRES_AVAILABLE:
                logger.error("Supabase/PostgreSQL configured but psycopg2 is not installed. Falling back to SQLite.")
                self.db_type = "sqlite"
                self._init_sqlite()
                return

            try:
                conn_str = getattr(self.config, "SUPABASE_DB_URL", "") or os.getenv("DATABASE_URL", "")
                if not conn_str:
                    logger.warning("SUPABASE_DB_URL not set in .env. Falling back to SQLite.")
                    self.db_type = "sqlite"
                    self._init_sqlite()
                    return
                self.pg_pool = psycopg2.pool.SimpleConnectionPool(1, 10, conn_str)
                logger.info("Successfully connected to Supabase / PostgreSQL database.")
            except Exception as e:
                logger.warning("Failed to connect to Supabase/PostgreSQL (%s). Falling back to SQLite.", e)
                self.db_type = "sqlite"
                self._init_sqlite()

        elif self.db_type == "oracle":
            if not ORACLE_AVAILABLE:
                logger.error("Oracle database configured but python-oracledb is not installed. Falling back to SQLite.")
                self.db_type = "sqlite"
                self._init_sqlite()
                return

            try:
                # Oracle Thin mode initialization
                pool_args = {
                    "user": self.config.ORACLE_USER,
                    "password": self.config.ORACLE_PASSWORD,
                    "dsn": self.config.ORACLE_DSN,
                    "min": 1,
                    "max": 10,
                    "increment": 1
                }
                if self.config.ORACLE_CONFIG_DIR:
                    pool_args["config_dir"] = self.config.ORACLE_CONFIG_DIR
                if self.config.ORACLE_WALLET_PASSWORD:
                    pool_args["wallet_password"] = self.config.ORACLE_WALLET_PASSWORD

                self.oracle_pool = oracledb.create_pool(**pool_args)
                logger.info("Successfully connected to Oracle Database pool: %s", self.config.ORACLE_DSN)
            except Exception as e:
                logger.warning(
                    "Failed to connect to Oracle Database (%s). Falling back to SQLite local database for development.", e
                )
                self.db_type = "sqlite"
                self._init_sqlite()
        else:
            self._init_sqlite()

    def _init_sqlite(self):
        db_path = Path(self.config.SQLITE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        should_seed = not db_path.exists() or db_path.stat().st_size == 0
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        with conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON;")
            if should_seed:
                self._bootstrap_sqlite_schema(conn)
        conn.close()
        logger.info("SQLite database initialized at: %s", db_path)

    def _bootstrap_sqlite_schema(self, conn):
        """Creates SQLite schema matching the Oracle SQL specification."""
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS USERS (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('PATIENT', 'DOCTOR', 'ADMIN')),
            full_name TEXT NOT NULL,
            phone_number TEXT,
            is_active INTEGER DEFAULT 1 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_login_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS PATIENT_PROFILES (
            patient_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES USERS(user_id) ON DELETE CASCADE,
            date_of_birth DATE,
            gender TEXT,
            blood_group TEXT,
            emergency_contact TEXT,
            allergies TEXT,
            chronic_conditions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DOCTOR_PROFILES (
            doctor_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES USERS(user_id) ON DELETE CASCADE,
            medical_qualification TEXT NOT NULL,
            registration_number TEXT NOT NULL,
            registration_council TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            specialty TEXT NOT NULL,
            experience_years INTEGER DEFAULT 0,
            clinic_address TEXT,
            consultation_fee REAL DEFAULT 0.00,
            verification_status TEXT DEFAULT 'PENDING' NOT NULL CHECK(verification_status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED')),
            verified_at TIMESTAMP,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DOCTOR_VERIFICATIONS (
            verification_id TEXT PRIMARY KEY,
            doctor_id TEXT NOT NULL REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE CASCADE,
            provider_source TEXT DEFAULT 'DIGILOCKER' NOT NULL,
            oauth_state TEXT,
            digilocker_txn_id TEXT,
            doc_type TEXT,
            doc_uri TEXT,
            issuer_id TEXT,
            extracted_doctor_name TEXT,
            extracted_reg_no TEXT,
            extracted_council TEXT,
            extracted_qual TEXT,
            name_match_score REAL,
            reg_no_match INTEGER,
            status TEXT NOT NULL CHECK(status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED')),
            rejection_reason TEXT,
            review_notes TEXT,
            verified_by TEXT,
            verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS MEDICAL_REPORTS (
            report_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            test_type TEXT,
            report_date DATE,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            ocr_raw_text TEXT,
            is_confirmed_by_patient INTEGER DEFAULT 0 NOT NULL
        );

        CREATE TABLE IF NOT EXISTS REPORT_ANALYSES (
            analysis_id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL UNIQUE REFERENCES MEDICAL_REPORTS(report_id) ON DELETE CASCADE,
            ai_provider TEXT NOT NULL,
            summary_plain_en TEXT NOT NULL,
            clinical_notes TEXT,
            abnormal_count INTEGER DEFAULT 0 NOT NULL,
            urgent_flags TEXT,
            risk_level TEXT DEFAULT 'LOW' NOT NULL CHECK(risk_level IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY')),
            recommendations TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS REPORT_TEST_VALUES (
            value_id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL REFERENCES MEDICAL_REPORTS(report_id) ON DELETE CASCADE,
            parameter_name TEXT NOT NULL,
            measured_value REAL,
            measured_text TEXT,
            unit TEXT,
            ref_range_min REAL,
            ref_range_max REAL,
            ref_range_text TEXT,
            flag TEXT DEFAULT 'NORMAL' NOT NULL CHECK(flag IN ('NORMAL', 'LOW', 'HIGH', 'CRITICAL', 'INDETERMINATE'))
        );

        CREATE TABLE IF NOT EXISTS CONSULTATIONS (
            consultation_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE,
            assigned_doctor_id TEXT REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE SET NULL,
            title TEXT DEFAULT 'Health Inquiry' NOT NULL,
            consult_type TEXT DEFAULT 'AI_ASSISTANT' NOT NULL CHECK(consult_type IN ('AI_ASSISTANT', 'DOCTOR_CONSULT')),
            risk_category TEXT DEFAULT 'LOW' NOT NULL CHECK(risk_category IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY')),
            red_flag_alert INTEGER DEFAULT 0 NOT NULL,
            is_shared_with_doctor INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS CONSULTATION_MESSAGES (
            message_id TEXT PRIMARY KEY,
            consultation_id TEXT NOT NULL REFERENCES CONSULTATIONS(consultation_id) ON DELETE CASCADE,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('PATIENT', 'AI_ASSISTANT', 'DOCTOR', 'SYSTEM')),
            sender_id TEXT,
            message_text TEXT NOT NULL,
            disclaimer_note TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS MEDICINE_INFORMATION (
            medicine_id TEXT PRIMARY KEY,
            brand_name TEXT NOT NULL,
            generic_name TEXT NOT NULL,
            therapeutic_class TEXT,
            common_uses TEXT NOT NULL,
            safety_precautions TEXT NOT NULL,
            contraindications TEXT NOT NULL,
            common_side_effects TEXT,
            allergy_warnings TEXT,
            rx_required INTEGER DEFAULT 0 NOT NULL,
            trusted_source TEXT DEFAULT 'WHO & FDA Drug Compendium' NOT NULL,
            pharmacy_links_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DRUG_INTERACTIONS (
            interaction_id TEXT PRIMARY KEY,
            medicine_a_id TEXT NOT NULL REFERENCES MEDICINE_INFORMATION(medicine_id) ON DELETE CASCADE,
            medicine_b_id TEXT NOT NULL REFERENCES MEDICINE_INFORMATION(medicine_id) ON DELETE CASCADE,
            severity TEXT NOT NULL CHECK(severity IN ('MILD', 'MODERATE', 'SEVERE', 'CONTRAINDICATED')),
            interaction_desc TEXT NOT NULL,
            clinical_advice TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS HEALTH_PRODUCTS (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL,
            currency TEXT DEFAULT 'INR',
            is_in_stock INTEGER DEFAULT 1 NOT NULL,
            image_url TEXT,
            seller_name TEXT,
            product_url TEXT,
            is_demo_data INTEGER DEFAULT 1 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS APPOINTMENTS (
            appointment_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE,
            doctor_id TEXT NOT NULL REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE CASCADE,
            appointment_date DATE NOT NULL,
            slot_time TEXT NOT NULL,
            status TEXT DEFAULT 'BOOKED' NOT NULL CHECK(status IN ('BOOKED', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'RESCHEDULED')),
            reason_for_visit TEXT,
            doctor_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS USER_CONSENTS (
            consent_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
            consent_type TEXT NOT NULL,
            is_granted INTEGER NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS AUDIT_LOGS (
            log_id TEXT PRIMARY KEY,
            actor_user_id TEXT,
            event_type TEXT NOT NULL,
            target_resource TEXT NOT NULL,
            resource_id TEXT,
            event_status TEXT NOT NULL CHECK(event_status IN ('SUCCESS', 'FAILURE', 'WARNING', 'ALERT')),
            details_json TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """)

        # Seed initial data
        self._seed_sqlite_initial_data(cursor)
        conn.commit()

    def _seed_sqlite_initial_data(self, cursor):
        """Populates seed data into SQLite for out-of-the-box demonstration."""
        pwd_hash = "$2b$10$K9ZmQi9b.oWDyKh5ytB.pO6X9nBSgiRdTqAh7Y5hHXNbpY.s7c/ge"

        # Users
        cursor.execute("""
        INSERT OR IGNORE INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active)
        VALUES 
        ('u-doc-001', 'dr.priya.sharma@hospital.org', ?, 'DOCTOR', 'Dr. Priya Sharma', '+919876543210', 1),
        ('u-doc-002', 'dr.rajesh.varma@clinic.org', ?, 'DOCTOR', 'Dr. Rajesh K. Varma', '+919876543211', 1),
        ('u-doc-003', 'dr.anita.deshmukh@medcare.org', ?, 'DOCTOR', 'Dr. Anita Deshmukh', '+919876543212', 1),
        ('u-pat-001', 'rahul.mehta@email.com', ?, 'PATIENT', 'Rahul Mehta', '+919820011223', 1);
        """, (pwd_hash, pwd_hash, pwd_hash, pwd_hash))

        # Doctor Profiles
        cursor.execute("""
        INSERT OR IGNORE INTO DOCTOR_PROFILES 
        (doctor_id, user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years, clinic_address, consultation_fee, verification_status, verified_at, bio)
        VALUES 
        ('dp-001', 'u-doc-001', 'MBBS, MD (Cardiology), DM (Cardiology)', 'MCI-1998-04281', 'Maharashtra Medical Council', 'Maharashtra, India', 'Cardiology', 16, 'Heart Wellness Clinic, Nariman Point, Mumbai', 1200.00, 'VERIFIED', CURRENT_TIMESTAMP, 'Senior Interventional Cardiologist specializing in preventive cardiology and hypertension management.'),
        ('dp-002', 'u-doc-002', 'MBBS, MD (General Medicine), DNB (Endocrinology)', 'DMC-2005-18934', 'Delhi Medical Council', 'Delhi NCR, India', 'Endocrinology', 12, 'Metabolic Care Centre, Vasant Kunj, New Delhi', 1000.00, 'VERIFIED', CURRENT_TIMESTAMP, 'Consultant Endocrinologist specializing in Type 1 & 2 Diabetes and metabolic health.'),
        ('dp-003', 'u-doc-003', 'MBBS, DNB (Family Medicine)', 'KMC-2015-77210', 'Karnataka Medical Council', 'Karnataka, India', 'General Medicine', 7, 'Community Health Hub, Indiranagar, Bengaluru', 600.00, 'PENDING', NULL, 'Dedicated primary care physician focused on preventive health checkups and chronic illness monitoring.');
        """)

        # Doctor Verifications
        cursor.execute("""
        INSERT OR IGNORE INTO DOCTOR_VERIFICATIONS
        (verification_id, doctor_id, provider_source, oauth_state, digilocker_txn_id, doc_type, doc_uri, issuer_id, extracted_doctor_name, extracted_reg_no, extracted_council, extracted_qual, name_match_score, reg_no_match, status, review_notes)
        VALUES
        ('dv-001', 'dp-001', 'DIGILOCKER', 'state_seed_001', 'DL-TXN-2026-99120', 'DOCREG', 'in.gov.digilocker.docreg:MCI-1998-04281', 'in.gov.nmc', 'Dr. Priya Sharma', 'MCI-1998-04281', 'Maharashtra Medical Council', 'MBBS, MD (Cardiology)', 100.00, 1, 'VERIFIED', 'Official digital certificate verified via DigiLocker API Setu issuer gateway. NMC registry cross-reference confirmed active status.'),
        ('dv-002', 'dp-002', 'DIGILOCKER', 'state_seed_002', 'DL-TXN-2026-88143', 'DOCREG', 'in.gov.digilocker.docreg:DMC-2005-18934', 'in.gov.dmc', 'Dr. Rajesh K. Varma', 'DMC-2005-18934', 'Delhi Medical Council', 'MBBS, MD', 100.00, 1, 'VERIFIED', 'DigiLocker issued credential authenticated successfully against Delhi Medical Council database.');
        """)

        # Patient Profile
        cursor.execute("""
        INSERT OR IGNORE INTO PATIENT_PROFILES
        (patient_id, user_id, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_conditions)
        VALUES
        ('pp-001', 'u-pat-001', '1988-06-15', 'MALE', 'B+', '+919820099887 (Spouse)', 'Penicillin', 'Mild Hypertension');
        """)

        # User Consents
        cursor.execute("""
        INSERT OR IGNORE INTO USER_CONSENTS (consent_id, user_id, consent_type, is_granted)
        VALUES 
        ('uc-001', 'u-pat-001', 'HEALTH_DATA_PROCESSING', 1),
        ('uc-002', 'u-pat-001', 'PRIVACY_POLICY', 1);
        """)

        # Medicines
        cursor.execute("""
        INSERT OR IGNORE INTO MEDICINE_INFORMATION
        (medicine_id, brand_name, generic_name, therapeutic_class, common_uses, safety_precautions, contraindications, common_side_effects, allergy_warnings, rx_required, trusted_source, pharmacy_links_json)
        VALUES
        ('med-001', 'Crocin / Dolo 650', 'Paracetamol (Acetaminophen)', 'Analgesic & Antipyretic',
         'Relief of mild to moderate pain (headache, body ache) and reduction of fever.',
         'Do not exceed 4,000 mg in 24 hours. Avoid alcohol consumption during therapy.',
         'Severe active liver disease, acute liver impairment, severe renal insufficiency.',
         'Nausea, rash, rare allergic reactions. Hepatotoxicity in overdose.',
         'Immediate medical attention required if rash, swelling of lips/face occurs.',
         0, 'WHO Model List of Essential Medicines & US FDA Drug Safety Guidelines',
         '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=paracetamol"},{"store":"Apollo Pharmacy","url":"https://www.apollopharmacy.in/search-medicines/paracetamol"}]'),
        ('med-002', 'Glycomet 500', 'Metformin Hydrochloride', 'Biguanide Antidiabetic',
         'Management of Type 2 Diabetes Mellitus to improve glycemic control.',
         'Monitor renal function (eGFR) regularly. Temporarily discontinue prior to iodinated radiocontrast procedures.',
         'Severe renal impairment (eGFR < 30 mL/min), acute metabolic acidosis, severe diabetic ketoacidosis.',
         'Gastrointestinal discomfort, diarrhea, nausea, metallic taste.',
         'Rare risk of lactic acidosis; report unusual muscle pain or severe drowsiness immediately.',
         1, 'American Diabetes Association & CDSCO Approved Drug Compendium',
         '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=metformin"},{"store":"Apollo Pharmacy","url":"https://www.apollopharmacy.in/search-medicines/metformin"}]'),
        ('med-003', 'Lipitor / Atorva', 'Atorvastatin Calcium', 'HMG-CoA Reductase Inhibitor (Statin)',
         'Lowers LDL cholesterol and triglycerides, reduces the risk of stroke and cardiac events.',
         'Periodic liver function tests advised. Report unexplained muscle aches or weakness.',
         'Active liver disease, unexplained persistent elevations of serum transaminases, pregnancy.',
         'Headache, myalgia, diarrhea, elevated transaminases, dyspepsia.',
         'Hypersensitivity reactions including anaphylaxis, angioedema, and bullous rashes.',
         1, 'NIH & European Society of Cardiology Guidelines',
         '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=atorvastatin"},{"store":"Netmeds","url":"https://www.netmeds.com/catalogsearch/result/atorvastatin"}]'),
        ('med-004', 'Augmentin 625 Duo', 'Amoxicillin + Clavulanic Acid', 'Beta-Lactam Antibiotic',
         'Treatment of bacterial infections including respiratory tract, urinary tract, and dental infections.',
         'Complete the entire prescribed course even if symptoms improve to prevent antimicrobial resistance.',
         'History of penicillin allergy, history of amoxicillin-associated cholestatic jaundice.',
         'Diarrhea, nausea, vomiting, candidiasis, mild rash.',
         'CONTRAINDICATED in patients with known hypersensitivity to penicillins or beta-lactam antibiotics.',
         1, 'Infectious Diseases Society of America (IDSA) Treatment Protocols',
         '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=amoxicillin+clavulanate"}]'),
        ('med-005', 'Omez 20', 'Omeprazole', 'Proton Pump Inhibitor (PPI)',
         'Treatment of gastroesophageal reflux disease (GERD) and peptic ulcer disease.',
         'Long-term use may reduce magnesium levels. Best taken 30-60 minutes before breakfast.',
         'Known hypersensitivity to omeprazole; concomitant use with rilpivirine.',
         'Headache, abdominal pain, constipation, flatulence, nausea.',
         'Report severe watery diarrhea or signs of hypomagnesemia immediately.',
         0, 'British National Formulary (BNF) & FDA Package Insert',
         '[{"store":"Tata 1mg","url":"https://www.1mg.com/search/all?name=omeprazole"}]');
        """)

        # Drug Interactions
        cursor.execute("""
        INSERT OR IGNORE INTO DRUG_INTERACTIONS (interaction_id, medicine_a_id, medicine_b_id, severity, interaction_desc, clinical_advice)
        VALUES 
        ('di-001', 'med-003', 'med-004', 'MODERATE',
         'Concurrent administration of certain antibiotics with statins may alter statin metabolism.',
         'Monitor for symptoms of statin-induced myopathy (muscle pain or weakness). Clinician consultation recommended.');
        """)

        # Health Products
        cursor.execute("""
        INSERT OR IGNORE INTO HEALTH_PRODUCTS 
        (product_id, product_name, category, description, price, currency, is_in_stock, seller_name, product_url, is_demo_data)
        VALUES
        ('prod-001', 'Omron HEM-7120 Fully Automatic Digital Blood Pressure Monitor', 'Diagnostic Devices',
         'Clinically validated upper arm BP monitor with Intellisense Technology, hypertension indicator, and cuff wrapping guide.',
         2249.00, 'INR', 1, 'Omron Official Healthcare Store', 'https://www.amazon.in/dp/B00J3C2424', 1),
        ('prod-002', 'Accu-Chek Active Blood Glucose Glucometer Kit with 10 Strips', 'Diabetes Care',
         'Accurate blood sugar monitoring system with 5-second test time, pre/post-meal markers, and ISO 15197 compliance.',
         1449.00, 'INR', 1, 'Roche Diabetes Care', 'https://www.amazon.in/dp/B008VUN45Y', 1),
        ('prod-003', 'Beurer PO 30 Fingertip Pulse Oximeter', 'Respiratory & Vitals',
         'Measures arterial oxygen saturation (SpO2) and heart rate. Easy-to-read color display with 4 view options.',
         1899.00, 'INR', 1, 'Beurer Medical GmbH', 'https://www.amazon.in/dp/B004323ZLE', 1),
        ('prod-004', 'Philips Respironics Sami the Seal Pediatric Compressor Nebulizer', 'Respiratory Care',
         'Child-friendly pediatric nebulizer delivering fast and effective aerosol medication treatment.',
         3290.00, 'INR', 1, 'Philips Healthcare', 'https://www.amazon.in/dp/B007X64B4Q', 1),
        ('prod-005', 'Dr. Morepen Digital Flexi-Tip Clinical Thermometer', 'Diagnostic Devices',
         'Accurate oral and underarm temperature measurement with fever alarm and waterproof tip.',
         249.00, 'INR', 1, 'Dr. Morepen Health Store', 'https://www.amazon.in/dp/B00J65A5L0', 1);
        """)

        # Sample Report
        cursor.execute("""
        INSERT OR IGNORE INTO MEDICAL_REPORTS 
        (report_id, patient_id, original_filename, stored_filename, file_path, file_size_bytes, file_type, test_type, report_date, is_confirmed_by_patient)
        VALUES
        ('rep-001', 'pp-001', 'Complete_Lipid_Profile_2026.pdf', 'rep-001_seed_lipid.pdf', 'uploads/rep-001_seed_lipid.pdf', 245760, 'application/pdf', 'Comprehensive Lipid Profile', '2026-09-15', 1);
        """)

        cursor.execute("""
        INSERT OR IGNORE INTO REPORT_ANALYSES
        (analysis_id, report_id, ai_provider, summary_plain_en, clinical_notes, abnormal_count, urgent_flags, risk_level, recommendations)
        VALUES
        ('ana-001', 'rep-001', 'Gemini AI Health Engine',
         'Your comprehensive lipid panel shows an elevated Total Cholesterol (238 mg/dL) and LDL "Bad" Cholesterol (154 mg/dL). HDL "Good" Cholesterol and Triglycerides are within safe normal ranges. Note: Slightly elevated cholesterol does not automatically constitute a diagnosis of heart disease, but indicates a need for proactive lifestyle optimizations.',
         'Mild-to-moderate hypercholesterolemia. ASCVD risk calculation indicated in context of blood pressure history.',
         2, 'No acute or critical laboratory findings requiring emergency medical intervention.', 'MODERATE',
         '1. Consult your primary physician or cardiologist regarding cardiovascular risk evaluation.
2. Adopt a heart-healthy diet low in saturated fats and refined sugars.
3. Maintain 150 minutes of moderate aerobic physical activity per week.
4. Repeat fasting lipid panel in 3 months.');
        """)

        cursor.execute("""
        INSERT OR IGNORE INTO REPORT_TEST_VALUES
        (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
        VALUES
        ('val-001', 'rep-001', 'Total Cholesterol', 238.0, '238', 'mg/dL', 125.0, 200.0, '< 200 mg/dL', 'HIGH'),
        ('val-002', 'rep-001', 'LDL Cholesterol (Direct)', 154.0, '154', 'mg/dL', 0.0, 100.0, '< 100 mg/dL', 'HIGH'),
        ('val-003', 'rep-001', 'HDL Cholesterol', 48.0, '48', 'mg/dL', 40.0, 60.0, '> 40 mg/dL', 'NORMAL'),
        ('val-004', 'rep-001', 'Serum Triglycerides', 138.0, '138', 'mg/dL', 50.0, 150.0, '< 150 mg/dL', 'NORMAL');
        """)

        # Sample Appointment
        cursor.execute("""
        INSERT OR IGNORE INTO APPOINTMENTS 
        (appointment_id, patient_id, doctor_id, appointment_date, slot_time, status, reason_for_visit, doctor_notes)
        VALUES
        ('apt-001', 'pp-001', 'dp-001', '2026-11-05', '10:30 AM', 'CONFIRMED', 'Follow-up evaluation on recent lipid profile report and lifestyle guidance.', 'Patient has brought recent lab report rep-001.');
        """)

    @contextmanager
    def get_connection(self):
        """Context manager yielding a database connection."""
        if self.db_type in ("postgres", "postgresql", "supabase") and self.pg_pool:
            conn = self.pg_pool.getconn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self.pg_pool.putconn(conn)
        elif self.db_type == "oracle" and self.oracle_pool:
            conn = self.oracle_pool.acquire()
            try:
                yield conn
            finally:
                self.oracle_pool.release(conn)
        else:
            conn = sqlite3.connect(str(self.config.SQLITE_DB_PATH))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute_query(self, query, params=None, fetchone=False, fetchall=False):
        """
        Executes query safely using named parameters (:param_name).
        Works seamlessly on Supabase/PostgreSQL, Oracle, and SQLite.
        """
        params = params or {}

        # Handle Supabase / PostgreSQL query translation
        if self.db_type in ("postgres", "postgresql", "supabase"):
            pg_query = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', query)
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(pg_query, params)
                if fetchone:
                    res = cursor.fetchone()
                    return dict(res) if res else None
                if fetchall:
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
                return cursor.rowcount

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetchone:
                row = cursor.fetchone()
                if row is None:
                    return None
                if hasattr(row, "_mapping"):
                    return dict(row._mapping)
                if hasattr(cursor, "description"):
                    columns = [col[0].lower() for col in cursor.description]
                    return dict(zip(columns, row))
                return dict(row)
            if fetchall:
                rows = cursor.fetchall()
                if hasattr(cursor, "description"):
                    columns = [col[0].lower() for col in cursor.description]
                    return [dict(zip(columns, r)) if not hasattr(r, "_mapping") else dict(r._mapping) for r in rows]
                return [dict(r) for r in rows]
            return cursor.rowcount

# Singleton instance
db_manager = DatabaseManager()
