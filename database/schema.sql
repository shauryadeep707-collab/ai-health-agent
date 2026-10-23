-- =============================================================================
-- AI HEALTH AGENT — ORACLE SQL DATABASE SCHEMA
-- Target Database: Oracle Database 19c / 21c / 23ai / Autonomous DB / XE
-- Compatibility: Standard Oracle SQL DDL
-- =============================================================================

-- Clean up existing tables in reverse dependency order (optional for clean re-install)
BEGIN
    FOR cur_rec IN (
        SELECT object_name, object_type 
        FROM user_objects 
        WHERE object_type = 'TABLE' 
          AND object_name IN (
            'AUDIT_LOGS', 'USER_CONSENTS', 'APPOINTMENTS', 'HEALTH_PRODUCTS',
            'DRUG_INTERACTIONS', 'MEDICINE_INFORMATION', 'CONSULTATION_MESSAGES',
            'CONSULTATIONS', 'REPORT_TEST_VALUES', 'REPORT_ANALYSES',
            'MEDICAL_REPORTS', 'DOCTOR_VERIFICATIONS', 'DOCTOR_PROFILES',
            'PATIENT_PROFILES', 'USERS'
          )
    ) LOOP
        BEGIN
            EXECUTE IMMEDIATE 'DROP TABLE ' || cur_rec.object_name || ' CASCADE CONSTRAINTS PURGE';
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;
    END LOOP;
END;
/

-- -----------------------------------------------------------------------------
-- 1. USERS: Core authentication and identity table
-- -----------------------------------------------------------------------------
CREATE TABLE USERS (
    user_id          VARCHAR2(36) PRIMARY KEY,
    email            VARCHAR2(255) NOT NULL UNIQUE,
    password_hash    VARCHAR2(255) NOT NULL,
    role             VARCHAR2(20) NOT NULL,
    full_name        VARCHAR2(150) NOT NULL,
    phone_number     VARCHAR2(25),
    is_active        NUMBER(1) DEFAULT 1 NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at    TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_users_role CHECK (role IN ('PATIENT', 'DOCTOR', 'ADMIN')),
    CONSTRAINT chk_users_active CHECK (is_active IN (0, 1))
);

CREATE INDEX idx_users_email ON USERS(email);
CREATE INDEX idx_users_role ON USERS(role);

-- -----------------------------------------------------------------------------
-- 2. PATIENT_PROFILES: Specific medical demographic data for patients
-- -----------------------------------------------------------------------------
CREATE TABLE PATIENT_PROFILES (
    patient_id       VARCHAR2(36) PRIMARY KEY,
    user_id          VARCHAR2(36) NOT NULL UNIQUE,
    date_of_birth    DATE,
    gender           VARCHAR2(20),
    blood_group      VARCHAR2(10),
    emergency_contact VARCHAR2(50),
    allergies        CLOB,
    chronic_conditions CLOB,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_pat_user FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_pat_gender CHECK (gender IN ('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY'))
);

CREATE INDEX idx_pat_user_id ON PATIENT_PROFILES(user_id);

-- -----------------------------------------------------------------------------
-- 3. DOCTOR_PROFILES: Professional details for medical practitioners
-- -----------------------------------------------------------------------------
CREATE TABLE DOCTOR_PROFILES (
    doctor_id            VARCHAR2(36) PRIMARY KEY,
    user_id              VARCHAR2(36) NOT NULL UNIQUE,
    medical_qualification VARCHAR2(150) NOT NULL,
    registration_number  VARCHAR2(100) NOT NULL,
    registration_council VARCHAR2(150) NOT NULL,
    jurisdiction         VARCHAR2(100) NOT NULL,
    specialty            VARCHAR2(100) NOT NULL,
    experience_years     NUMBER(3) DEFAULT 0,
    clinic_address       VARCHAR2(300),
    consultation_fee     NUMBER(10, 2) DEFAULT 0.00,
    verification_status  VARCHAR2(25) DEFAULT 'PENDING' NOT NULL,
    verified_at          TIMESTAMP WITH TIME ZONE,
    bio                  CLOB,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at           TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_doc_user FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_doc_vstatus CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED')),
    CONSTRAINT uq_doc_regno UNIQUE (registration_number, registration_council)
);

CREATE INDEX idx_doc_vstatus ON DOCTOR_PROFILES(verification_status);
CREATE INDEX idx_doc_specialty ON DOCTOR_PROFILES(specialty);

-- -----------------------------------------------------------------------------
-- 4. DOCTOR_VERIFICATIONS: Detailed DigiLocker/API Setu audit trail & state machine
-- -----------------------------------------------------------------------------
CREATE TABLE DOCTOR_VERIFICATIONS (
    verification_id       VARCHAR2(36) PRIMARY KEY,
    doctor_id             VARCHAR2(36) NOT NULL,
    provider_source       VARCHAR2(50) DEFAULT 'DIGILOCKER' NOT NULL,
    oauth_state           VARCHAR2(100),
    digilocker_txn_id     VARCHAR2(100),
    doc_type              VARCHAR2(50),
    doc_uri               VARCHAR2(255),
    issuer_id             VARCHAR2(100),
    extracted_doctor_name VARCHAR2(150),
    extracted_reg_no      VARCHAR2(100),
    extracted_council     VARCHAR2(150),
    extracted_qual        VARCHAR2(150),
    name_match_score      NUMBER(5, 2),
    reg_no_match          NUMBER(1),
    status                VARCHAR2(25) NOT NULL,
    rejection_reason      VARCHAR2(500),
    review_notes          CLOB,
    verified_by           VARCHAR2(50),
    verification_date     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_verif_doc FOREIGN KEY (doctor_id) REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE CASCADE,
    CONSTRAINT chk_verif_status CHECK (status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED'))
);

CREATE INDEX idx_verif_doc_id ON DOCTOR_VERIFICATIONS(doctor_id);
CREATE INDEX idx_verif_status ON DOCTOR_VERIFICATIONS(status);
CREATE INDEX idx_verif_oauth_state ON DOCTOR_VERIFICATIONS(oauth_state);

-- -----------------------------------------------------------------------------
-- 5. MEDICAL_REPORTS: Uploaded lab tests, scans, blood work
-- -----------------------------------------------------------------------------
CREATE TABLE MEDICAL_REPORTS (
    report_id        VARCHAR2(36) PRIMARY KEY,
    patient_id       VARCHAR2(36) NOT NULL,
    original_filename VARCHAR2(255) NOT NULL,
    stored_filename   VARCHAR2(255) NOT NULL,
    file_path        VARCHAR2(500) NOT NULL,
    file_size_bytes  NUMBER(15) NOT NULL,
    file_type        VARCHAR2(50) NOT NULL,
    test_type        VARCHAR2(100),
    report_date      DATE,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ocr_raw_text     CLOB,
    is_confirmed_by_patient NUMBER(1) DEFAULT 0 NOT NULL,
    CONSTRAINT fk_rep_patient FOREIGN KEY (patient_id) REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE
);

CREATE INDEX idx_rep_patient_id ON MEDICAL_REPORTS(patient_id);
CREATE INDEX idx_rep_upload_time ON MEDICAL_REPORTS(upload_timestamp);

-- -----------------------------------------------------------------------------
-- 6. REPORT_ANALYSES: AI explanations, risk classification, structured findings
-- -----------------------------------------------------------------------------
CREATE TABLE REPORT_ANALYSES (
    analysis_id      VARCHAR2(36) PRIMARY KEY,
    report_id        VARCHAR2(36) NOT NULL UNIQUE,
    ai_provider      VARCHAR2(50) NOT NULL,
    summary_plain_en CLOB NOT NULL,
    clinical_notes   CLOB,
    abnormal_count   NUMBER(4) DEFAULT 0 NOT NULL,
    urgent_flags     CLOB,
    risk_level       VARCHAR2(20) DEFAULT 'LOW' NOT NULL,
    recommendations  CLOB,
    analyzed_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_analysis_rep FOREIGN KEY (report_id) REFERENCES MEDICAL_REPORTS(report_id) ON DELETE CASCADE,
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY'))
);

-- -----------------------------------------------------------------------------
-- 7. REPORT_TEST_VALUES: Granular test parameters extracted from reports
-- -----------------------------------------------------------------------------
CREATE TABLE REPORT_TEST_VALUES (
    value_id         VARCHAR2(36) PRIMARY KEY,
    report_id        VARCHAR2(36) NOT NULL,
    parameter_name   VARCHAR2(150) NOT NULL,
    measured_value   NUMBER(12, 4),
    measured_text    VARCHAR2(100),
    unit             VARCHAR2(50),
    ref_range_min    NUMBER(12, 4),
    ref_range_max    NUMBER(12, 4),
    ref_range_text   VARCHAR2(100),
    flag             VARCHAR2(20) DEFAULT 'NORMAL' NOT NULL,
    CONSTRAINT fk_val_rep FOREIGN KEY (report_id) REFERENCES MEDICAL_REPORTS(report_id) ON DELETE CASCADE,
    CONSTRAINT chk_val_flag CHECK (flag IN ('NORMAL', 'LOW', 'HIGH', 'CRITICAL', 'INDETERMINATE'))
);

CREATE INDEX idx_val_report_id ON REPORT_TEST_VALUES(report_id);
CREATE INDEX idx_val_param ON REPORT_TEST_VALUES(parameter_name);

-- -----------------------------------------------------------------------------
-- 8. CONSULTATIONS: Patient-AI and Patient-Doctor Consultation Sessions
-- -----------------------------------------------------------------------------
CREATE TABLE CONSULTATIONS (
    consultation_id  VARCHAR2(36) PRIMARY KEY,
    patient_id       VARCHAR2(36) NOT NULL,
    assigned_doctor_id VARCHAR2(36),
    title            VARCHAR2(200) DEFAULT 'Health Inquiry' NOT NULL,
    consult_type     VARCHAR2(20) DEFAULT 'AI_ASSISTANT' NOT NULL,
    risk_category    VARCHAR2(20) DEFAULT 'LOW' NOT NULL,
    red_flag_alert   NUMBER(1) DEFAULT 0 NOT NULL,
    is_shared_with_doctor NUMBER(1) DEFAULT 0 NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_cons_patient FOREIGN KEY (patient_id) REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE,
    CONSTRAINT fk_cons_doctor FOREIGN KEY (assigned_doctor_id) REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE SET NULL,
    CONSTRAINT chk_cons_type CHECK (consult_type IN ('AI_ASSISTANT', 'DOCTOR_CONSULT')),
    CONSTRAINT chk_cons_risk CHECK (risk_category IN ('LOW', 'MODERATE', 'HIGH', 'EMERGENCY'))
);

CREATE INDEX idx_cons_pat_id ON CONSULTATIONS(patient_id);
CREATE INDEX idx_cons_doc_id ON CONSULTATIONS(assigned_doctor_id);

-- -----------------------------------------------------------------------------
-- 9. CONSULTATION_MESSAGES: Dialogue history with sender attribution
-- -----------------------------------------------------------------------------
CREATE TABLE CONSULTATION_MESSAGES (
    message_id       VARCHAR2(36) PRIMARY KEY,
    consultation_id  VARCHAR2(36) NOT NULL,
    sender_type      VARCHAR2(20) NOT NULL,
    sender_id        VARCHAR2(36),
    message_text     CLOB NOT NULL,
    disclaimer_note  VARCHAR2(300),
    sent_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_cmsg_cons FOREIGN KEY (consultation_id) REFERENCES CONSULTATIONS(consultation_id) ON DELETE CASCADE,
    CONSTRAINT chk_sender_type CHECK (sender_type IN ('PATIENT', 'AI_ASSISTANT', 'DOCTOR', 'SYSTEM'))
);

CREATE INDEX idx_cmsg_cons_id ON CONSULTATION_MESSAGES(consultation_id);

-- -----------------------------------------------------------------------------
-- 10. MEDICINE_INFORMATION: Medical reference directory
-- -----------------------------------------------------------------------------
CREATE TABLE MEDICINE_INFORMATION (
    medicine_id      VARCHAR2(36) PRIMARY KEY,
    brand_name       VARCHAR2(150) NOT NULL,
    generic_name     VARCHAR2(150) NOT NULL,
    therapeutic_class VARCHAR2(100),
    common_uses      CLOB NOT NULL,
    safety_precautions CLOB NOT NULL,
    contraindications CLOB NOT NULL,
    common_side_effects CLOB,
    allergy_warnings CLOB,
    rx_required      NUMBER(1) DEFAULT 0 NOT NULL,
    trusted_source   VARCHAR2(200) DEFAULT 'WHO Model List & FDA Drug Reference' NOT NULL,
    pharmacy_links_json CLOB,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_med_brand ON MEDICINE_INFORMATION(brand_name);
CREATE INDEX idx_med_generic ON MEDICINE_INFORMATION(generic_name);

-- -----------------------------------------------------------------------------
-- 11. DRUG_INTERACTIONS: Known contraindications between medicines
-- -----------------------------------------------------------------------------
CREATE TABLE DRUG_INTERACTIONS (
    interaction_id   VARCHAR2(36) PRIMARY KEY,
    medicine_a_id    VARCHAR2(36) NOT NULL,
    medicine_b_id    VARCHAR2(36) NOT NULL,
    severity         VARCHAR2(20) NOT NULL,
    interaction_desc CLOB NOT NULL,
    clinical_advice  CLOB NOT NULL,
    CONSTRAINT fk_inter_med_a FOREIGN KEY (medicine_a_id) REFERENCES MEDICINE_INFORMATION(medicine_id) ON DELETE CASCADE,
    CONSTRAINT fk_inter_med_b FOREIGN KEY (medicine_b_id) REFERENCES MEDICINE_INFORMATION(medicine_id) ON DELETE CASCADE,
    CONSTRAINT chk_inter_sev CHECK (severity IN ('MILD', 'MODERATE', 'SEVERE', 'CONTRAINDICATED'))
);

CREATE INDEX idx_inter_meds ON DRUG_INTERACTIONS(medicine_a_id, medicine_b_id);

-- -----------------------------------------------------------------------------
-- 12. HEALTH_PRODUCTS: Over-the-counter medical devices and wellness catalogue
-- -----------------------------------------------------------------------------
CREATE TABLE HEALTH_PRODUCTS (
    product_id       VARCHAR2(36) PRIMARY KEY,
    product_name     VARCHAR2(200) NOT NULL,
    category         VARCHAR2(100) NOT NULL,
    description      CLOB NOT NULL,
    price            NUMBER(10, 2),
    currency         VARCHAR2(10) DEFAULT 'INR',
    is_in_stock      NUMBER(1) DEFAULT 1 NOT NULL,
    image_url        VARCHAR2(500),
    seller_name      VARCHAR2(150),
    product_url      VARCHAR2(500),
    is_demo_data     NUMBER(1) DEFAULT 1 NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_prod_name ON HEALTH_PRODUCTS(product_name);
CREATE INDEX idx_prod_cat ON HEALTH_PRODUCTS(category);

-- -----------------------------------------------------------------------------
-- 13. APPOINTMENTS: Doctor-patient booking records
-- -----------------------------------------------------------------------------
CREATE TABLE APPOINTMENTS (
    appointment_id   VARCHAR2(36) PRIMARY KEY,
    patient_id       VARCHAR2(36) NOT NULL,
    doctor_id        VARCHAR2(36) NOT NULL,
    appointment_date DATE NOT NULL,
    slot_time        VARCHAR2(20) NOT NULL,
    status           VARCHAR2(20) DEFAULT 'BOOKED' NOT NULL,
    reason_for_visit VARCHAR2(500),
    doctor_notes     CLOB,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_apt_pat FOREIGN KEY (patient_id) REFERENCES PATIENT_PROFILES(patient_id) ON DELETE CASCADE,
    CONSTRAINT fk_apt_doc FOREIGN KEY (doctor_id) REFERENCES DOCTOR_PROFILES(doctor_id) ON DELETE CASCADE,
    CONSTRAINT chk_apt_status CHECK (status IN ('BOOKED', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'RESCHEDULED'))
);

CREATE INDEX idx_apt_pat_id ON APPOINTMENTS(patient_id);
CREATE INDEX idx_apt_doc_id ON APPOINTMENTS(doctor_id);
CREATE INDEX idx_apt_date ON APPOINTMENTS(appointment_date);

-- -----------------------------------------------------------------------------
-- 14. USER_CONSENTS: Patient explicit privacy and data processing records
-- -----------------------------------------------------------------------------
CREATE TABLE USER_CONSENTS (
    consent_id       VARCHAR2(36) PRIMARY KEY,
    user_id          VARCHAR2(36) NOT NULL,
    consent_type     VARCHAR2(100) NOT NULL,
    is_granted       NUMBER(1) NOT NULL,
    ip_address       VARCHAR2(45),
    user_agent       VARCHAR2(255),
    granted_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    revoked_at       TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_consent_user FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_consent_granted CHECK (is_granted IN (0, 1))
);

CREATE INDEX idx_consent_user_id ON USER_CONSENTS(user_id);

-- -----------------------------------------------------------------------------
-- 15. AUDIT_LOGS: Immutable security, access and verification event trail
-- -----------------------------------------------------------------------------
CREATE TABLE AUDIT_LOGS (
    log_id           VARCHAR2(36) PRIMARY KEY,
    actor_user_id    VARCHAR2(36),
    event_type       VARCHAR2(100) NOT NULL,
    target_resource  VARCHAR2(100) NOT NULL,
    resource_id      VARCHAR2(100),
    event_status     VARCHAR2(20) NOT NULL,
    details_json     CLOB,
    ip_address       VARCHAR2(45),
    timestamp        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_log_status CHECK (event_status IN ('SUCCESS', 'FAILURE', 'WARNING', 'ALERT'))
);

CREATE INDEX idx_audit_time ON AUDIT_LOGS(timestamp);
CREATE INDEX idx_audit_event ON AUDIT_LOGS(event_type);
CREATE INDEX idx_audit_actor ON AUDIT_LOGS(actor_user_id);

COMMIT;
