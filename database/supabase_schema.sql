-- =============================================================================
-- AI HEALTH AGENT — SUPABASE / POSTGRESQL SCHEMA (supabase_schema.sql)
-- Copy and paste this directly into Supabase SQL Editor and click "RUN"
-- =============================================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id          VARCHAR(36) PRIMARY KEY,
    email            VARCHAR(255) NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,
    role             VARCHAR(20) NOT NULL,
    full_name        VARCHAR(150) NOT NULL,
    phone_number     VARCHAR(25),
    is_active        SMALLINT DEFAULT 1 NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at    TIMESTAMPTZ,
    CONSTRAINT chk_users_role CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN'))
);

-- 2. PATIENT PROFILES
CREATE TABLE IF NOT EXISTS patient_profiles (
    patient_id       VARCHAR(36) PRIMARY KEY,
    user_id          VARCHAR(36) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    date_of_birth    DATE,
    gender           VARCHAR(20),
    blood_group      VARCHAR(10),
    emergency_contact VARCHAR(50),
    allergies        TEXT,
    chronic_conditions TEXT,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. DOCTOR PROFILES
CREATE TABLE IF NOT EXISTS doctor_profiles (
    doctor_id            VARCHAR(36) PRIMARY KEY,
    user_id              VARCHAR(36) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    medical_qualification VARCHAR(150) NOT NULL,
    registration_number  VARCHAR(100) NOT NULL,
    registration_council VARCHAR(150) NOT NULL,
    jurisdiction         VARCHAR(100) NOT NULL,
    specialty            VARCHAR(100) NOT NULL,
    experience_years     INTEGER DEFAULT 0,
    clinic_address       VARCHAR(300),
    consultation_fee     NUMERIC(10, 2) DEFAULT 0.00,
    verification_status  VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
    verified_at          TIMESTAMPTZ,
    bio                  TEXT,
    created_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_doc_status CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED'))
);

-- 4. DOCTOR VERIFICATIONS (DigiLocker Audit Trail)
CREATE TABLE IF NOT EXISTS doctor_verifications (
    verification_id       VARCHAR(36) PRIMARY KEY,
    doctor_id             VARCHAR(36) NOT NULL REFERENCES doctor_profiles(doctor_id) ON DELETE CASCADE,
    provider_source       VARCHAR(50) DEFAULT 'DIGILOCKER' NOT NULL,
    oauth_state           VARCHAR(100),
    digilocker_txn_id     VARCHAR(100),
    doc_type              VARCHAR(50),
    doc_uri               VARCHAR(255),
    issuer_id             VARCHAR(100),
    extracted_doctor_name VARCHAR(150),
    extracted_reg_no      VARCHAR(100),
    extracted_council     VARCHAR(150),
    extracted_qual        VARCHAR(150),
    name_match_score      NUMERIC(5, 2),
    reg_no_match          SMALLINT DEFAULT 0,
    status                VARCHAR(20) NOT NULL,
    review_notes          TEXT,
    verified_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. MEDICAL REPORTS
CREATE TABLE IF NOT EXISTS medical_reports (
    report_id        VARCHAR(36) PRIMARY KEY,
    patient_id       VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename   VARCHAR(255) NOT NULL,
    file_path        VARCHAR(500) NOT NULL,
    file_size_bytes  BIGINT NOT NULL,
    file_type        VARCHAR(50) NOT NULL,
    test_type        VARCHAR(100),
    report_date      DATE,
    upload_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ocr_raw_text     TEXT,
    is_confirmed     SMALLINT DEFAULT 0 NOT NULL,
    confirmed_at     TIMESTAMPTZ
);

-- 6. REPORT ANALYSES
CREATE TABLE IF NOT EXISTS report_analyses (
    analysis_id      VARCHAR(36) PRIMARY KEY,
    report_id        VARCHAR(36) NOT NULL UNIQUE REFERENCES medical_reports(report_id) ON DELETE CASCADE,
    ai_provider      VARCHAR(50) NOT NULL,
    summary_plain_en TEXT NOT NULL,
    clinical_notes   TEXT,
    abnormal_count   INTEGER DEFAULT 0 NOT NULL,
    urgent_flags     TEXT,
    risk_level       VARCHAR(20) DEFAULT 'LOW' NOT NULL,
    recommendations  TEXT,
    analyzed_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 7. REPORT TEST VALUES
CREATE TABLE IF NOT EXISTS report_test_values (
    value_id         VARCHAR(36) PRIMARY KEY,
    report_id        VARCHAR(36) NOT NULL REFERENCES medical_reports(report_id) ON DELETE CASCADE,
    parameter_name   VARCHAR(100) NOT NULL,
    measured_value   NUMERIC(10, 3) NOT NULL,
    measured_text    VARCHAR(50),
    unit             VARCHAR(30),
    ref_range_min    NUMERIC(10, 3),
    ref_range_max    NUMERIC(10, 3),
    ref_range_text   VARCHAR(50),
    flag             VARCHAR(15) DEFAULT 'NORMAL' NOT NULL
);

-- 8. CONSULTATIONS
CREATE TABLE IF NOT EXISTS consultations (
    consultation_id       VARCHAR(36) PRIMARY KEY,
    patient_id            VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    assigned_doctor_id    VARCHAR(36) REFERENCES doctor_profiles(doctor_id),
    title                 VARCHAR(150) DEFAULT 'Health Consultation' NOT NULL,
    consult_type          VARCHAR(30) DEFAULT 'AI_ASSISTANT' NOT NULL,
    risk_category         VARCHAR(20) DEFAULT 'LOW' NOT NULL,
    red_flag_alert        SMALLINT DEFAULT 0 NOT NULL,
    is_shared_with_doctor SMALLINT DEFAULT 0 NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 9. CONSULTATION MESSAGES
CREATE TABLE IF NOT EXISTS consultation_messages (
    message_id      VARCHAR(36) PRIMARY KEY,
    consultation_id VARCHAR(36) NOT NULL REFERENCES consultations(consultation_id) ON DELETE CASCADE,
    sender_type     VARCHAR(20) NOT NULL,
    sender_id       VARCHAR(36) NOT NULL,
    message_text    TEXT NOT NULL,
    disclaimer_note TEXT,
    sent_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 10. MEDICINE INFORMATION
CREATE TABLE IF NOT EXISTS medicine_information (
    medicine_id         VARCHAR(36) PRIMARY KEY,
    brand_name          VARCHAR(150) NOT NULL,
    generic_name        VARCHAR(150) NOT NULL,
    therapeutic_class   VARCHAR(100),
    common_uses         TEXT NOT NULL,
    safety_precautions  TEXT NOT NULL,
    contraindications   TEXT NOT NULL,
    common_side_effects TEXT,
    allergy_warnings    TEXT,
    rx_required         SMALLINT DEFAULT 0 NOT NULL,
    trusted_source      VARCHAR(200),
    pharmacy_links_json TEXT
);

-- 11. DRUG INTERACTIONS
CREATE TABLE IF NOT EXISTS drug_interactions (
    interaction_id   VARCHAR(36) PRIMARY KEY,
    medicine_a_id    VARCHAR(36) NOT NULL REFERENCES medicine_information(medicine_id) ON DELETE CASCADE,
    medicine_b_id    VARCHAR(36) NOT NULL REFERENCES medicine_information(medicine_id) ON DELETE CASCADE,
    severity         VARCHAR(20) NOT NULL,
    interaction_desc TEXT NOT NULL,
    clinical_advice  TEXT NOT NULL,
    CONSTRAINT chk_inter_sev CHECK (severity IN ('MILD', 'MODERATE', 'SEVERE', 'CONTRAINDICATED'))
);

-- 12. APPOINTMENTS
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id   VARCHAR(36) PRIMARY KEY,
    patient_id       VARCHAR(36) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    doctor_id        VARCHAR(36) NOT NULL REFERENCES doctor_profiles(doctor_id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    slot_time        VARCHAR(20) NOT NULL,
    status           VARCHAR(20) DEFAULT 'BOOKED' NOT NULL,
    reason_for_visit VARCHAR(500),
    doctor_notes     TEXT,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_apt_status CHECK (status IN ('BOOKED', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'NO_SHOW'))
);

-- 13. USER CONSENTS
CREATE TABLE IF NOT EXISTS user_consents (
    consent_id       VARCHAR(36) PRIMARY KEY,
    user_id          VARCHAR(36) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    consent_type     VARCHAR(100) NOT NULL,
    is_granted       SMALLINT NOT NULL,
    ip_address       VARCHAR(45),
    user_agent       VARCHAR(255),
    granted_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    revoked_at       TIMESTAMPTZ
);

-- 14. AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id           VARCHAR(36) PRIMARY KEY,
    actor_user_id    VARCHAR(36),
    event_type       VARCHAR(100) NOT NULL,
    target_resource  VARCHAR(100) NOT NULL,
    resource_id      VARCHAR(100),
    event_status     VARCHAR(20) NOT NULL,
    details_json     TEXT,
    ip_address       VARCHAR(45),
    timestamp        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_log_status CHECK (event_status IN ('SUCCESS', 'FAILURE', 'WARNING', 'ALERT'))
);


