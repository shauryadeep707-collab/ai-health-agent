-- =============================================================================
-- AI HEALTH AGENT — FINAL SUPABASE / POSTGRESQL SCHEMA
-- Copy & paste this directly into Supabase SQL Editor and click "RUN"
-- =============================================================================

-- 1. USERS TABLE (Common Account for Doctor and Patient)
CREATE TABLE IF NOT EXISTS users (
    user_id          VARCHAR(36) PRIMARY KEY,
    role             VARCHAR(20) NOT NULL,
    full_name        VARCHAR(150) NOT NULL,
    email            VARCHAR(255) NOT NULL UNIQUE,
    phone_number     VARCHAR(25),
    password_hash    VARCHAR(255) NOT NULL,
    is_active        SMALLINT DEFAULT 1 NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_users_role CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN'))
);

-- 2. PATIENT PROFILES (Health details of Patient)
CREATE TABLE IF NOT EXISTS patient_profiles (
    patient_id         VARCHAR(36) PRIMARY KEY,
    user_id            VARCHAR(36) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    date_of_birth      DATE,
    gender             VARCHAR(20),
    blood_group        VARCHAR(10),
    has_allergies      SMALLINT DEFAULT 0 NOT NULL,
    chronic_conditions TEXT,
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. PATIENT ALLERGIES & MEDICINES (Allergy triggers & medicine details)
CREATE TABLE IF NOT EXISTS patient_allergies (
    allergy_id         VARCHAR(36) PRIMARY KEY,
    patient_id         VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    allergen_name      VARCHAR(150) NOT NULL,
    allergy_type       VARCHAR(50) DEFAULT 'DRUG' NOT NULL,
    reaction_symptoms  TEXT,
    severity           VARCHAR(20) DEFAULT 'MODERATE' NOT NULL,
    medicines_to_avoid TEXT,
    relief_medicine    TEXT,
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_allergy_sev CHECK (severity IN ('MILD', 'MODERATE', 'SEVERE'))
);

-- 4. DOCTOR PROFILES (Doctor Professional Information)
CREATE TABLE IF NOT EXISTS doctor_profiles (
    doctor_id             VARCHAR(36) PRIMARY KEY,
    user_id               VARCHAR(36) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    specialty             VARCHAR(100) NOT NULL,
    medical_qualification VARCHAR(150) NOT NULL,
    registration_number   VARCHAR(100) NOT NULL,
    experience_years      INTEGER DEFAULT 0,
    clinic_address        VARCHAR(300),
    consultation_fee      NUMERIC(10, 2) DEFAULT 0.00,
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. MEDICAL REPORTS (Uploaded blood / lab test reports)
CREATE TABLE IF NOT EXISTS medical_reports (
    report_id        VARCHAR(36) PRIMARY KEY,
    patient_id       VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    file_name        VARCHAR(255) NOT NULL,
    file_path        VARCHAR(500) NOT NULL,
    report_date      DATE,
    ai_summary       TEXT,
    risk_level       VARCHAR(20) DEFAULT 'LOW' NOT NULL,
    uploaded_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_report_risk CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

-- 6. REPORT TEST VALUES (Extracted lab test parameters)
CREATE TABLE IF NOT EXISTS report_test_values (
    value_id         VARCHAR(36) PRIMARY KEY,
    report_id        VARCHAR(36) NOT NULL REFERENCES medical_reports(report_id) ON DELETE CASCADE,
    test_name        VARCHAR(100) NOT NULL,
    measured_value   NUMERIC(10, 3) NOT NULL,
    unit             VARCHAR(30),
    reference_range  VARCHAR(50),
    flag             VARCHAR(15) DEFAULT 'NORMAL' NOT NULL,
    CONSTRAINT chk_test_flag CHECK (flag IN ('NORMAL', 'HIGH', 'LOW', 'CRITICAL'))
);

-- 7. CONSULTATIONS (AI Chat Sessions)
CREATE TABLE IF NOT EXISTS consultations (
    consultation_id  VARCHAR(36) PRIMARY KEY,
    patient_id       VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    title            VARCHAR(150) DEFAULT 'Health Consultation' NOT NULL,
    risk_category    VARCHAR(20) DEFAULT 'LOW' NOT NULL,
    red_flag_alert   SMALLINT DEFAULT 0 NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_consult_risk CHECK (risk_category IN ('LOW', 'MEDIUM', 'EMERGENCY'))
);

-- 8. CONSULTATION MESSAGES (Turn-by-turn chat history)
CREATE TABLE IF NOT EXISTS consultation_messages (
    message_id      VARCHAR(36) PRIMARY KEY,
    consultation_id VARCHAR(36) NOT NULL REFERENCES consultations(consultation_id) ON DELETE CASCADE,
    sender_type     VARCHAR(20) NOT NULL,
    message_text    TEXT NOT NULL,
    sent_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_sender_type CHECK (sender_type IN ('USER', 'AI'))
);
