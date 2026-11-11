-- =============================================================================
-- AI HEALTH AGENT — COMPLETE SUPABASE / POSTGRESQL SCHEMA
-- Clean, production-ready schema matching backend repositories & auto-bootstrap
-- =============================================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id          VARCHAR(64) PRIMARY KEY,
    email            VARCHAR(255) NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,
    role             VARCHAR(20) NOT NULL,
    full_name        VARCHAR(200) NOT NULL,
    phone_number     VARCHAR(50),
    is_active        SMALLINT DEFAULT 1 NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at    TIMESTAMPTZ,
    CONSTRAINT chk_users_role CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN'))
);

-- 2. PATIENT PROFILES
CREATE TABLE IF NOT EXISTS patient_profiles (
    patient_id         VARCHAR(64) PRIMARY KEY,
    user_id            VARCHAR(64) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    date_of_birth      DATE,
    gender             VARCHAR(30),
    blood_group        VARCHAR(20),
    emergency_contact  VARCHAR(100),
    allergies          TEXT,
    chronic_conditions TEXT,
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. PATIENT ALLERGIES & MEDICINES
CREATE TABLE IF NOT EXISTS patient_allergies (
    allergy_id         VARCHAR(64) PRIMARY KEY,
    patient_id         VARCHAR(64) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    allergen_name      VARCHAR(150) NOT NULL,
    allergy_type       VARCHAR(50) DEFAULT 'DRUG' NOT NULL,
    reaction_symptoms  TEXT,
    severity           VARCHAR(20) DEFAULT 'MODERATE' NOT NULL,
    medicines_to_avoid TEXT,
    relief_medicine    TEXT,
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_allergy_sev CHECK (severity IN ('MILD', 'MODERATE', 'SEVERE'))
);

-- 4. DOCTOR PROFILES
CREATE TABLE IF NOT EXISTS doctor_profiles (
    doctor_id             VARCHAR(64) PRIMARY KEY,
    user_id               VARCHAR(64) NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    medical_qualification VARCHAR(255) NOT NULL,
    registration_number   VARCHAR(100) NOT NULL,
    registration_council  VARCHAR(200) NOT NULL,
    jurisdiction          VARCHAR(150) NOT NULL,
    specialty             VARCHAR(150) NOT NULL,
    experience_years      INTEGER DEFAULT 0,
    clinic_address        TEXT,
    consultation_fee      NUMERIC(10, 2) DEFAULT 0.00,
    verification_status   VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
    verified_at           TIMESTAMPTZ,
    bio                   TEXT,
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_doc_status CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED'))
);

-- 5. DOCTOR VERIFICATIONS (DigiLocker Audit Trail)
CREATE TABLE IF NOT EXISTS doctor_verifications (
    verification_id       VARCHAR(64) PRIMARY KEY,
    doctor_id             VARCHAR(64) NOT NULL REFERENCES doctor_profiles(doctor_id) ON DELETE CASCADE,
    provider_source       VARCHAR(50) DEFAULT 'DIGILOCKER' NOT NULL,
    oauth_state           VARCHAR(150),
    digilocker_txn_id     VARCHAR(150),
    doc_type              VARCHAR(50),
    doc_uri               TEXT,
    issuer_id             VARCHAR(150),
    extracted_doctor_name VARCHAR(200),
    extracted_reg_no      VARCHAR(100),
    extracted_council     VARCHAR(200),
    extracted_qual        VARCHAR(255),
    name_match_score      NUMERIC(6, 2),
    reg_no_match          SMALLINT DEFAULT 0,
    status                VARCHAR(30) NOT NULL CHECK (status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED')),
    rejection_reason      TEXT,
    review_notes          TEXT,
    verified_by           VARCHAR(100),
    verification_date     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 6. MEDICAL REPORTS
CREATE TABLE IF NOT EXISTS medical_reports (
    report_id               VARCHAR(64) PRIMARY KEY,
    patient_id              VARCHAR(64) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    original_filename       VARCHAR(255) NOT NULL,
    stored_filename         VARCHAR(255) NOT NULL,
    file_path               TEXT NOT NULL,
    file_size_bytes         BIGINT DEFAULT 0 NOT NULL,
    file_type               VARCHAR(100) NOT NULL,
    test_type               VARCHAR(150),
    report_date             DATE,
    upload_timestamp        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ocr_raw_text            TEXT,
    is_confirmed_by_patient SMALLINT DEFAULT 0 NOT NULL
);

-- 7. REPORT ANALYSES
CREATE TABLE IF NOT EXISTS report_analyses (
    analysis_id      VARCHAR(64) PRIMARY KEY,
    report_id        VARCHAR(64) NOT NULL UNIQUE REFERENCES medical_reports(report_id) ON DELETE CASCADE,
    ai_provider      VARCHAR(100) NOT NULL,
    summary_plain_en TEXT NOT NULL,
    clinical_notes   TEXT,
    abnormal_count   INTEGER DEFAULT 0 NOT NULL,
    urgent_flags     TEXT,
    risk_level       VARCHAR(20) DEFAULT 'LOW' NOT NULL CHECK (risk_level IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY')),
    recommendations  TEXT,
    analyzed_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 8. REPORT TEST VALUES
CREATE TABLE IF NOT EXISTS report_test_values (
    value_id         VARCHAR(64) PRIMARY KEY,
    report_id        VARCHAR(64) NOT NULL REFERENCES medical_reports(report_id) ON DELETE CASCADE,
    parameter_name   VARCHAR(200) NOT NULL,
    measured_value   NUMERIC(12, 3),
    measured_text    VARCHAR(100),
    unit             VARCHAR(50),
    ref_range_min    NUMERIC(12, 3),
    ref_range_max    NUMERIC(12, 3),
    ref_range_text   VARCHAR(100),
    flag             VARCHAR(20) DEFAULT 'NORMAL' NOT NULL CHECK (flag IN ('NORMAL', 'LOW', 'HIGH', 'CRITICAL', 'INDETERMINATE'))
);

-- 9. CONSULTATIONS
CREATE TABLE IF NOT EXISTS consultations (
    consultation_id       VARCHAR(64) PRIMARY KEY,
    patient_id            VARCHAR(64) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    assigned_doctor_id    VARCHAR(64) REFERENCES doctor_profiles(doctor_id) ON DELETE SET NULL,
    title                 VARCHAR(255) DEFAULT 'Health Inquiry' NOT NULL,
    consult_type          VARCHAR(30) DEFAULT 'AI_ASSISTANT' NOT NULL CHECK (consult_type IN ('AI_ASSISTANT', 'DOCTOR_CONSULT')),
    risk_category         VARCHAR(20) DEFAULT 'LOW' NOT NULL CHECK (risk_category IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY')),
    red_flag_alert        SMALLINT DEFAULT 0 NOT NULL,
    is_shared_with_doctor SMALLINT DEFAULT 0 NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 10. CONSULTATION MESSAGES
CREATE TABLE IF NOT EXISTS consultation_messages (
    message_id      VARCHAR(64) PRIMARY KEY,
    consultation_id VARCHAR(64) NOT NULL REFERENCES consultations(consultation_id) ON DELETE CASCADE,
    sender_type     VARCHAR(30) NOT NULL CHECK (sender_type IN ('PATIENT', 'AI_ASSISTANT', 'DOCTOR', 'SYSTEM')),
    sender_id       VARCHAR(64),
    message_text    TEXT NOT NULL,
    disclaimer_note TEXT,
    sent_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 11. MEDICINE INFORMATION
CREATE TABLE IF NOT EXISTS medicine_information (
    medicine_id         VARCHAR(64) PRIMARY KEY,
    brand_name          VARCHAR(255) NOT NULL,
    generic_name        VARCHAR(255) NOT NULL,
    therapeutic_class   VARCHAR(255),
    common_uses         TEXT NOT NULL,
    safety_precautions  TEXT NOT NULL,
    contraindications   TEXT NOT NULL,
    common_side_effects TEXT,
    allergy_warnings    TEXT,
    rx_required         SMALLINT DEFAULT 0 NOT NULL,
    trusted_source      VARCHAR(255) DEFAULT 'WHO & FDA Drug Compendium' NOT NULL,
    pharmacy_links_json TEXT,
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 12. DRUG INTERACTIONS
CREATE TABLE IF NOT EXISTS drug_interactions (
    interaction_id   VARCHAR(64) PRIMARY KEY,
    medicine_a_id    VARCHAR(64) NOT NULL REFERENCES medicine_information(medicine_id) ON DELETE CASCADE,
    medicine_b_id    VARCHAR(64) NOT NULL REFERENCES medicine_information(medicine_id) ON DELETE CASCADE,
    severity         VARCHAR(30) NOT NULL CHECK (severity IN ('MILD', 'MODERATE', 'SEVERE', 'CONTRAINDICATED')),
    interaction_desc TEXT NOT NULL,
    clinical_advice  TEXT NOT NULL
);

-- 13. HEALTH PRODUCTS
CREATE TABLE IF NOT EXISTS health_products (
    product_id   VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    description  TEXT NOT NULL,
    price        NUMERIC(10, 2),
    currency     VARCHAR(10) DEFAULT 'INR',
    is_in_stock  SMALLINT DEFAULT 1 NOT NULL,
    image_url    TEXT,
    seller_name  VARCHAR(200),
    product_url  TEXT,
    is_demo_data SMALLINT DEFAULT 1 NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 14. APPOINTMENTS
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id   VARCHAR(64) PRIMARY KEY,
    patient_id       VARCHAR(64) NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    doctor_id        VARCHAR(64) NOT NULL REFERENCES doctor_profiles(doctor_id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    slot_time        VARCHAR(50) NOT NULL,
    status           VARCHAR(30) DEFAULT 'BOOKED' NOT NULL,
    reason_for_visit TEXT,
    doctor_notes     TEXT,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_apt_status CHECK (status IN ('BOOKED', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'RESCHEDULED'))
);

-- 15. USER CONSENTS
CREATE TABLE IF NOT EXISTS user_consents (
    consent_id       VARCHAR(64) PRIMARY KEY,
    user_id          VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    consent_type     VARCHAR(100) NOT NULL,
    is_granted       SMALLINT NOT NULL,
    ip_address       VARCHAR(64),
    user_agent       TEXT,
    granted_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    revoked_at       TIMESTAMPTZ
);

-- 16. AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id           VARCHAR(64) PRIMARY KEY,
    actor_user_id    VARCHAR(64),
    event_type       VARCHAR(100) NOT NULL,
    target_resource  VARCHAR(100) NOT NULL,
    resource_id      VARCHAR(100),
    event_status     VARCHAR(20) NOT NULL,
    details_json     TEXT,
    ip_address       VARCHAR(64),
    timestamp        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_log_status CHECK (event_status IN ('SUCCESS', 'FAILURE', 'WARNING', 'ALERT'))
);
