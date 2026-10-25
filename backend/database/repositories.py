import uuid
import json
from datetime import datetime
from backend.database.connection import db_manager

# -----------------------------------------------------------------------------
# 1. User Repository
# -----------------------------------------------------------------------------
class UserRepository:
    @staticmethod
    def create(email, password_hash, role, full_name, phone_number=None, is_active=1):
        user_id = f"u-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO USERS (user_id, email, password_hash, role, full_name, phone_number, is_active)
        VALUES (:user_id, :email, :password_hash, :role, :full_name, :phone_number, :is_active)
        """
        db_manager.execute_query(query, {
            "user_id": user_id,
            "email": email.strip().lower(),
            "password_hash": password_hash,
            "role": role.upper(),
            "full_name": full_name.strip(),
            "phone_number": phone_number,
            "is_active": is_active
        })
        return UserRepository.find_by_id(user_id)

    @staticmethod
    def find_by_email(email):
        query = "SELECT * FROM USERS WHERE lower(email) = lower(:email)"
        return db_manager.execute_query(query, {"email": email.strip().lower()}, fetchone=True)

    @staticmethod
    def find_by_id(user_id):
        query = "SELECT * FROM USERS WHERE user_id = :user_id"
        return db_manager.execute_query(query, {"user_id": user_id}, fetchone=True)

    @staticmethod
    def update_last_login(user_id):
        query = "UPDATE USERS SET last_login_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
        db_manager.execute_query(query, {"user_id": user_id})

    @staticmethod
    def update_profile(user_id, full_name, phone_number):
        query = """
        UPDATE USERS 
        SET full_name = :full_name, phone_number = :phone_number, updated_at = CURRENT_TIMESTAMP 
        WHERE user_id = :user_id
        """
        db_manager.execute_query(query, {
            "user_id": user_id,
            "full_name": full_name,
            "phone_number": phone_number
        })

# -----------------------------------------------------------------------------
# 2. Patient Profile Repository
# -----------------------------------------------------------------------------
class PatientProfileRepository:
    @staticmethod
    def create(user_id, date_of_birth=None, gender=None, blood_group=None, emergency_contact=None, allergies=None, chronic_conditions=None):
        patient_id = f"pp-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO PATIENT_PROFILES 
        (patient_id, user_id, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_conditions)
        VALUES (:patient_id, :user_id, :date_of_birth, :gender, :blood_group, :emergency_contact, :allergies, :chronic_conditions)
        """
        db_manager.execute_query(query, {
            "patient_id": patient_id,
            "user_id": user_id,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "blood_group": blood_group,
            "emergency_contact": emergency_contact,
            "allergies": allergies,
            "chronic_conditions": chronic_conditions
        })
        return PatientProfileRepository.find_by_id(patient_id)

    @staticmethod
    def find_by_user_id(user_id):
        query = """
        SELECT p.*, u.email, u.full_name, u.phone_number 
        FROM PATIENT_PROFILES p 
        JOIN USERS u ON p.user_id = u.user_id 
        WHERE p.user_id = :user_id
        """
        return db_manager.execute_query(query, {"user_id": user_id}, fetchone=True)

    @staticmethod
    def find_by_id(patient_id):
        query = """
        SELECT p.*, u.email, u.full_name, u.phone_number 
        FROM PATIENT_PROFILES p 
        JOIN USERS u ON p.user_id = u.user_id 
        WHERE p.patient_id = :patient_id
        """
        return db_manager.execute_query(query, {"patient_id": patient_id}, fetchone=True)

    @staticmethod
    def update(patient_id, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_conditions):
        query = """
        UPDATE PATIENT_PROFILES
        SET date_of_birth = :date_of_birth,
            gender = :gender,
            blood_group = :blood_group,
            emergency_contact = :emergency_contact,
            allergies = :allergies,
            chronic_conditions = :chronic_conditions,
            updated_at = CURRENT_TIMESTAMP
        WHERE patient_id = :patient_id
        """
        db_manager.execute_query(query, {
            "patient_id": patient_id,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "blood_group": blood_group,
            "emergency_contact": emergency_contact,
            "allergies": allergies,
            "chronic_conditions": chronic_conditions
        })

# -----------------------------------------------------------------------------
# 3. Doctor Profile Repository
# -----------------------------------------------------------------------------
class DoctorProfileRepository:
    @staticmethod
    def create(user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years=0, clinic_address="", consultation_fee=0.0, bio=""):
        doctor_id = f"dp-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO DOCTOR_PROFILES 
        (doctor_id, user_id, medical_qualification, registration_number, registration_council, jurisdiction, specialty, experience_years, clinic_address, consultation_fee, verification_status, bio)
        VALUES (:doctor_id, :user_id, :qualification, :reg_no, :council, :jurisdiction, :specialty, :experience_years, :clinic_address, :consultation_fee, 'PENDING', :bio)
        """
        db_manager.execute_query(query, {
            "doctor_id": doctor_id,
            "user_id": user_id,
            "qualification": medical_qualification,
            "reg_no": registration_number,
            "council": registration_council,
            "jurisdiction": jurisdiction,
            "specialty": specialty,
            "experience_years": experience_years,
            "clinic_address": clinic_address,
            "consultation_fee": consultation_fee,
            "bio": bio
        })
        return DoctorProfileRepository.find_by_id(doctor_id)

    @staticmethod
    def find_by_user_id(user_id):
        query = """
        SELECT d.*, u.email, u.full_name, u.phone_number 
        FROM DOCTOR_PROFILES d 
        JOIN USERS u ON d.user_id = u.user_id 
        WHERE d.user_id = :user_id
        """
        return db_manager.execute_query(query, {"user_id": user_id}, fetchone=True)

    @staticmethod
    def find_by_id(doctor_id):
        query = """
        SELECT d.*, u.email, u.full_name, u.phone_number 
        FROM DOCTOR_PROFILES d 
        JOIN USERS u ON d.user_id = u.user_id 
        WHERE d.doctor_id = :doctor_id
        """
        return db_manager.execute_query(query, {"doctor_id": doctor_id}, fetchone=True)

    @staticmethod
    def update_verification_status(doctor_id, status, verified_at=None):
        query = """
        UPDATE DOCTOR_PROFILES
        SET verification_status = :status,
            verified_at = :verified_at,
            updated_at = CURRENT_TIMESTAMP
        WHERE doctor_id = :doctor_id
        """
        db_manager.execute_query(query, {
            "doctor_id": doctor_id,
            "status": status,
            "verified_at": verified_at
        })

    @staticmethod
    def search(query=None, specialty=None, jurisdiction=None, verified_only=True):
        sql = """
        SELECT d.*, u.full_name, u.email, u.phone_number
        FROM DOCTOR_PROFILES d
        JOIN USERS u ON d.user_id = u.user_id
        WHERE u.is_active = 1
        """
        params = {}
        if verified_only:
            sql += " AND d.verification_status = 'VERIFIED'"
        if specialty and specialty.strip():
            sql += " AND lower(d.specialty) LIKE lower(:specialty)"
            params["specialty"] = f"%{specialty.strip()}%"
        if jurisdiction and jurisdiction.strip():
            sql += " AND (lower(d.jurisdiction) LIKE lower(:jurisdiction) OR lower(d.clinic_address) LIKE lower(:jurisdiction))"
            params["jurisdiction"] = f"%{jurisdiction.strip()}%"
        if query and query.strip():
            sql += " AND (lower(u.full_name) LIKE lower(:query) OR lower(d.medical_qualification) LIKE lower(:query) OR lower(d.specialty) LIKE lower(:query))"
            params["query"] = f"%{query.strip()}%"

        sql += " ORDER BY d.experience_years DESC"
        return db_manager.execute_query(sql, params, fetchall=True)

# -----------------------------------------------------------------------------
# 4. Doctor Verification Repository
# -----------------------------------------------------------------------------
class DoctorVerificationRepository:
    @staticmethod
    def create(doctor_id, provider_source="DIGILOCKER", oauth_state=None, doc_type="DOCREG", status="PENDING"):
        verification_id = f"dv-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO DOCTOR_VERIFICATIONS
        (verification_id, doctor_id, provider_source, oauth_state, doc_type, status)
        VALUES (:verification_id, :doctor_id, :provider_source, :oauth_state, :doc_type, :status)
        """
        db_manager.execute_query(query, {
            "verification_id": verification_id,
            "doctor_id": doctor_id,
            "provider_source": provider_source,
            "oauth_state": oauth_state,
            "doc_type": doc_type,
            "status": status
        })
        return verification_id

    @staticmethod
    def find_by_state(oauth_state):
        query = "SELECT * FROM DOCTOR_VERIFICATIONS WHERE oauth_state = :oauth_state"
        return db_manager.execute_query(query, {"oauth_state": oauth_state}, fetchone=True)

    @staticmethod
    def find_latest_by_doctor_id(doctor_id):
        query = """
        SELECT * FROM DOCTOR_VERIFICATIONS 
        WHERE doctor_id = :doctor_id 
        ORDER BY verification_date DESC
        """
        return db_manager.execute_query(query, {"doctor_id": doctor_id}, fetchone=True)

    @staticmethod
    def update(verification_id, status, digilocker_txn_id=None, doc_uri=None, issuer_id=None,
               extracted_doctor_name=None, extracted_reg_no=None, extracted_council=None,
               extracted_qual=None, name_match_score=None, reg_no_match=None,
               rejection_reason=None, review_notes=None, verified_by=None):
        query = """
        UPDATE DOCTOR_VERIFICATIONS
        SET status = :status,
            digilocker_txn_id = :digilocker_txn_id,
            doc_uri = :doc_uri,
            issuer_id = :issuer_id,
            extracted_doctor_name = :extracted_doctor_name,
            extracted_reg_no = :extracted_reg_no,
            extracted_council = :extracted_council,
            extracted_qual = :extracted_qual,
            name_match_score = :name_match_score,
            reg_no_match = :reg_no_match,
            rejection_reason = :rejection_reason,
            review_notes = :review_notes,
            verified_by = :verified_by,
            verification_date = CURRENT_TIMESTAMP
        WHERE verification_id = :verification_id
        """
        db_manager.execute_query(query, {
            "verification_id": verification_id,
            "status": status,
            "digilocker_txn_id": digilocker_txn_id,
            "doc_uri": doc_uri,
            "issuer_id": issuer_id,
            "extracted_doctor_name": extracted_doctor_name,
            "extracted_reg_no": extracted_reg_no,
            "extracted_council": extracted_council,
            "extracted_qual": extracted_qual,
            "name_match_score": name_match_score,
            "reg_no_match": reg_no_match,
            "rejection_reason": rejection_reason,
            "review_notes": review_notes,
            "verified_by": verified_by
        })

    @staticmethod
    def list_history(doctor_id):
        query = """
        SELECT * FROM DOCTOR_VERIFICATIONS 
        WHERE doctor_id = :doctor_id 
        ORDER BY verification_date DESC
        """
        return db_manager.execute_query(query, {"doctor_id": doctor_id}, fetchall=True)

# -----------------------------------------------------------------------------
# 5. Medical Report & Analysis Repository
# -----------------------------------------------------------------------------
class MedicalReportRepository:
    @staticmethod
    def create_report(patient_id, original_filename, stored_filename, file_path, file_size_bytes, file_type, test_type="General Lab Report", report_date=None, ocr_raw_text=""):
        report_id = f"rep-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO MEDICAL_REPORTS
        (report_id, patient_id, original_filename, stored_filename, file_path, file_size_bytes, file_type, test_type, report_date, ocr_raw_text)
        VALUES (:report_id, :patient_id, :original_filename, :stored_filename, :file_path, :file_size_bytes, :file_type, :test_type, :report_date, :ocr_raw_text)
        """
        db_manager.execute_query(query, {
            "report_id": report_id,
            "patient_id": patient_id,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": file_path,
            "file_size_bytes": file_size_bytes,
            "file_type": file_type,
            "test_type": test_type,
            "report_date": report_date or datetime.utcnow().strftime("%Y-%m-%d"),
            "ocr_raw_text": ocr_raw_text
        })
        return report_id

    @staticmethod
    def find_by_id(report_id):
        query = "SELECT * FROM MEDICAL_REPORTS WHERE report_id = :report_id"
        return db_manager.execute_query(query, {"report_id": report_id}, fetchone=True)

    @staticmethod
    def list_by_patient(patient_id, sort_by="date_desc"):
        if sort_by == "date_asc":
            order_clause = "ORDER BY COALESCE(r.report_date, '1970-01-01') ASC, r.upload_timestamp ASC"
        elif sort_by == "upload_desc":
            order_clause = "ORDER BY r.upload_timestamp DESC"
        else:  # default: date_desc (arranged according to test date, newest first)
            order_clause = "ORDER BY COALESCE(r.report_date, '1970-01-01') DESC, r.upload_timestamp DESC"

        query = f"""
        SELECT r.*, a.risk_level, a.abnormal_count, a.summary_plain_en, a.recommendations,
               (SELECT COUNT(*) FROM REPORT_TEST_VALUES v WHERE v.report_id = r.report_id) as test_count
        FROM MEDICAL_REPORTS r
        LEFT JOIN REPORT_ANALYSES a ON r.report_id = a.report_id
        WHERE r.patient_id = :patient_id
        {order_clause}
        """
        return db_manager.execute_query(query, {"patient_id": patient_id}, fetchall=True)

    @staticmethod
    def set_confirmed(report_id, is_confirmed=1):
        query = "UPDATE MEDICAL_REPORTS SET is_confirmed_by_patient = :confirmed WHERE report_id = :report_id"
        db_manager.execute_query(query, {"confirmed": is_confirmed, "report_id": report_id})

    @staticmethod
    def save_analysis(report_id, ai_provider, summary_plain_en, clinical_notes="", abnormal_count=0, urgent_flags="", risk_level="LOW", recommendations=""):
        analysis_id = f"ana-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO REPORT_ANALYSES
        (analysis_id, report_id, ai_provider, summary_plain_en, clinical_notes, abnormal_count, urgent_flags, risk_level, recommendations)
        VALUES (:analysis_id, :report_id, :ai_provider, :summary_plain_en, :clinical_notes, :abnormal_count, :urgent_flags, :risk_level, :recommendations)
        """
        db_manager.execute_query(query, {
            "analysis_id": analysis_id,
            "report_id": report_id,
            "ai_provider": ai_provider,
            "summary_plain_en": summary_plain_en,
            "clinical_notes": clinical_notes,
            "abnormal_count": abnormal_count,
            "urgent_flags": urgent_flags,
            "risk_level": risk_level,
            "recommendations": recommendations
        })
        return analysis_id

    @staticmethod
    def get_analysis(report_id):
        query = "SELECT * FROM REPORT_ANALYSES WHERE report_id = :report_id"
        return db_manager.execute_query(query, {"report_id": report_id}, fetchone=True)

    @staticmethod
    def save_test_values(report_id, values):
        """values is a list of dicts: parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag"""
        for item in values:
            val_id = f"val-{uuid.uuid4().hex[:12]}"
            query = """
            INSERT INTO REPORT_TEST_VALUES
            (value_id, report_id, parameter_name, measured_value, measured_text, unit, ref_range_min, ref_range_max, ref_range_text, flag)
            VALUES (:value_id, :report_id, :parameter_name, :measured_value, :measured_text, :unit, :ref_range_min, :ref_range_max, :ref_range_text, :flag)
            """
            db_manager.execute_query(query, {
                "value_id": val_id,
                "report_id": report_id,
                "parameter_name": item.get("parameter_name"),
                "measured_value": item.get("measured_value"),
                "measured_text": str(item.get("measured_text") or item.get("measured_value")),
                "unit": item.get("unit"),
                "ref_range_min": item.get("ref_range_min"),
                "ref_range_max": item.get("ref_range_max"),
                "ref_range_text": item.get("ref_range_text"),
                "flag": item.get("flag", "NORMAL")
            })

    @staticmethod
    def get_test_values(report_id):
        query = "SELECT * FROM REPORT_TEST_VALUES WHERE report_id = :report_id"
        return db_manager.execute_query(query, {"report_id": report_id}, fetchall=True)

    @staticmethod
    def get_parameter_history(patient_id, parameter_name):
        query = """
        SELECT v.*, r.report_date, r.original_filename, r.upload_timestamp
        FROM REPORT_TEST_VALUES v
        JOIN MEDICAL_REPORTS r ON v.report_id = r.report_id
        WHERE r.patient_id = :patient_id AND lower(v.parameter_name) LIKE lower(:param_name)
        ORDER BY r.report_date ASC, r.upload_timestamp ASC
        """
        return db_manager.execute_query(query, {
            "patient_id": patient_id,
            "param_name": f"%{parameter_name.strip()}%"
        }, fetchall=True)

# -----------------------------------------------------------------------------
# 6. Consultation Repository
# -----------------------------------------------------------------------------
class ConsultationRepository:
    @staticmethod
    def create(patient_id, title="Health Inquiry", consult_type="AI_ASSISTANT", risk_category="LOW", red_flag_alert=0, assigned_doctor_id=None):
        consultation_id = f"cons-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO CONSULTATIONS 
        (consultation_id, patient_id, assigned_doctor_id, title, consult_type, risk_category, red_flag_alert)
        VALUES (:consultation_id, :patient_id, :assigned_doctor_id, :title, :consult_type, :risk_category, :red_flag_alert)
        """
        db_manager.execute_query(query, {
            "consultation_id": consultation_id,
            "patient_id": patient_id,
            "assigned_doctor_id": assigned_doctor_id,
            "title": title,
            "consult_type": consult_type,
            "risk_category": risk_category,
            "red_flag_alert": red_flag_alert
        })
        return consultation_id

    @staticmethod
    def find_by_id(consultation_id):
        query = "SELECT * FROM CONSULTATIONS WHERE consultation_id = :consultation_id"
        return db_manager.execute_query(query, {"consultation_id": consultation_id}, fetchone=True)

    @staticmethod
    def list_by_patient(patient_id):
        query = """
        SELECT c.*, d.specialty, u.full_name as doctor_name 
        FROM CONSULTATIONS c
        LEFT JOIN DOCTOR_PROFILES d ON c.assigned_doctor_id = d.doctor_id
        LEFT JOIN USERS u ON d.user_id = u.user_id
        WHERE c.patient_id = :patient_id
        ORDER BY c.updated_at DESC
        """
        return db_manager.execute_query(query, {"patient_id": patient_id}, fetchall=True)

    @staticmethod
    def list_by_doctor(doctor_id):
        query = """
        SELECT c.*, p.gender, p.blood_group, u.full_name as patient_name, u.email as patient_email
        FROM CONSULTATIONS c
        JOIN PATIENT_PROFILES p ON c.patient_id = p.patient_id
        JOIN USERS u ON p.user_id = u.user_id
        WHERE c.assigned_doctor_id = :doctor_id AND c.is_shared_with_doctor = 1
        ORDER BY c.updated_at DESC
        """
        return db_manager.execute_query(query, {"doctor_id": doctor_id}, fetchall=True)

    @staticmethod
    def add_message(consultation_id, sender_type, message_text, sender_id=None, disclaimer_note=""):
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO CONSULTATION_MESSAGES
        (message_id, consultation_id, sender_type, sender_id, message_text, disclaimer_note)
        VALUES (:message_id, :consultation_id, :sender_type, :sender_id, :message_text, :disclaimer_note)
        """
        db_manager.execute_query(query, {
            "message_id": msg_id,
            "consultation_id": consultation_id,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "message_text": message_text,
            "disclaimer_note": disclaimer_note
        })
        db_manager.execute_query(
            "UPDATE CONSULTATIONS SET updated_at = CURRENT_TIMESTAMP WHERE consultation_id = :id",
            {"id": consultation_id}
        )
        return msg_id

    @staticmethod
    def get_messages(consultation_id):
        query = "SELECT * FROM CONSULTATION_MESSAGES WHERE consultation_id = :consultation_id ORDER BY sent_at ASC"
        return db_manager.execute_query(query, {"consultation_id": consultation_id}, fetchall=True)

    @staticmethod
    def share_with_doctor(consultation_id, doctor_id):
        query = """
        UPDATE CONSULTATIONS 
        SET assigned_doctor_id = :doctor_id, is_shared_with_doctor = 1, updated_at = CURRENT_TIMESTAMP
        WHERE consultation_id = :consultation_id
        """
        db_manager.execute_query(query, {"consultation_id": consultation_id, "doctor_id": doctor_id})

# -----------------------------------------------------------------------------
# 7. Medicine & Drug Interaction Repository
# -----------------------------------------------------------------------------
class MedicineRepository:
    @staticmethod
    def search(query=None, limit=20):
        if not query or not query.strip():
            sql = "SELECT * FROM MEDICINE_INFORMATION ORDER BY brand_name ASC LIMIT :limit"
            return db_manager.execute_query(sql, {"limit": limit}, fetchall=True)

        sql = """
        SELECT * FROM MEDICINE_INFORMATION
        WHERE lower(brand_name) LIKE lower(:query)
           OR lower(generic_name) LIKE lower(:query)
           OR lower(common_uses) LIKE lower(:query)
        ORDER BY brand_name ASC LIMIT :limit
        """
        return db_manager.execute_query(sql, {"query": f"%{query.strip()}%", "limit": limit}, fetchall=True)

    @staticmethod
    def find_by_id(medicine_id):
        query = "SELECT * FROM MEDICINE_INFORMATION WHERE medicine_id = :medicine_id"
        return db_manager.execute_query(query, {"medicine_id": medicine_id}, fetchone=True)

    @staticmethod
    def check_interactions(medicine_ids):
        if len(medicine_ids) < 2:
            return []
        interactions = []
        for i in range(len(medicine_ids)):
            for j in range(i + 1, len(medicine_ids)):
                id_a, id_b = medicine_ids[i], medicine_ids[j]
                query = """
                SELECT di.*, ma.brand_name as med_a_name, mb.brand_name as med_b_name
                FROM DRUG_INTERACTIONS di
                JOIN MEDICINE_INFORMATION ma ON di.medicine_a_id = ma.medicine_id
                JOIN MEDICINE_INFORMATION mb ON di.medicine_b_id = mb.medicine_id
                WHERE (di.medicine_a_id = :id_a AND di.medicine_b_id = :id_b)
                   OR (di.medicine_a_id = :id_b AND di.medicine_b_id = :id_a)
                """
                results = db_manager.execute_query(query, {"id_a": id_a, "id_b": id_b}, fetchall=True)
                interactions.extend(results)
        return interactions

# -----------------------------------------------------------------------------
# 8. Health Product Repository
# -----------------------------------------------------------------------------
class ProductRepository:
    @staticmethod
    def search(query=None, category=None, limit=20):
        sql = "SELECT * FROM HEALTH_PRODUCTS WHERE 1=1"
        params = {"limit": limit}
        if category and category.strip():
            sql += " AND lower(category) = lower(:category)"
            params["category"] = category.strip()
        if query and query.strip():
            sql += " AND (lower(product_name) LIKE lower(:query) OR lower(description) LIKE lower(:query))"
            params["query"] = f"%{query.strip()}%"
        sql += " ORDER BY product_name ASC LIMIT :limit"
        return db_manager.execute_query(sql, params, fetchall=True)

    @staticmethod
    def get_categories():
        query = "SELECT DISTINCT category FROM HEALTH_PRODUCTS ORDER BY category ASC"
        rows = db_manager.execute_query(query, fetchall=True)
        return [r["category"] for r in rows if r.get("category")]

    @staticmethod
    def find_by_id(product_id):
        query = "SELECT * FROM HEALTH_PRODUCTS WHERE product_id = :product_id"
        return db_manager.execute_query(query, {"product_id": product_id}, fetchone=True)

# -----------------------------------------------------------------------------
# 9. Appointment Repository
# -----------------------------------------------------------------------------
class AppointmentRepository:
    @staticmethod
    def create(patient_id, doctor_id, appointment_date, slot_time, reason_for_visit=""):
        apt_id = f"apt-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO APPOINTMENTS 
        (appointment_id, patient_id, doctor_id, appointment_date, slot_time, status, reason_for_visit)
        VALUES (:apt_id, :patient_id, :doctor_id, :appointment_date, :slot_time, 'BOOKED', :reason_for_visit)
        """
        db_manager.execute_query(query, {
            "apt_id": apt_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": appointment_date,
            "slot_time": slot_time,
            "reason_for_visit": reason_for_visit
        })
        return apt_id

    @staticmethod
    def find_by_id(appointment_id):
        query = "SELECT * FROM APPOINTMENTS WHERE appointment_id = :appointment_id"
        return db_manager.execute_query(query, {"appointment_id": appointment_id}, fetchone=True)

    @staticmethod
    def list_by_patient(patient_id):
        query = """
        SELECT a.*, d.specialty, d.clinic_address, d.consultation_fee, u.full_name as doctor_name
        FROM APPOINTMENTS a
        JOIN DOCTOR_PROFILES d ON a.doctor_id = d.doctor_id
        JOIN USERS u ON d.user_id = u.user_id
        WHERE a.patient_id = :patient_id
        ORDER BY a.appointment_date DESC, a.slot_time ASC
        """
        return db_manager.execute_query(query, {"patient_id": patient_id}, fetchall=True)

    @staticmethod
    def list_by_doctor(doctor_id):
        query = """
        SELECT a.*, p.gender, p.blood_group, u.full_name as patient_name, u.phone_number as patient_phone, u.email as patient_email
        FROM APPOINTMENTS a
        JOIN PATIENT_PROFILES p ON a.patient_id = p.patient_id
        JOIN USERS u ON p.user_id = u.user_id
        WHERE a.doctor_id = :doctor_id
        ORDER BY a.appointment_date DESC, a.slot_time ASC
        """
        return db_manager.execute_query(query, {"doctor_id": doctor_id}, fetchall=True)

    @staticmethod
    def update_status(appointment_id, status, doctor_notes=None):
        query = """
        UPDATE APPOINTMENTS
        SET status = :status,
            doctor_notes = COALESCE(:doctor_notes, doctor_notes),
            updated_at = CURRENT_TIMESTAMP
        WHERE appointment_id = :appointment_id
        """
        db_manager.execute_query(query, {
            "appointment_id": appointment_id,
            "status": status,
            "doctor_notes": doctor_notes
        })

# -----------------------------------------------------------------------------
# 10. Consent & Audit Repositories
# -----------------------------------------------------------------------------
class ConsentRepository:
    @staticmethod
    def record_consent(user_id, consent_type, is_granted=1, ip_address=None, user_agent=None):
        consent_id = f"uc-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO USER_CONSENTS (consent_id, user_id, consent_type, is_granted, ip_address, user_agent)
        VALUES (:consent_id, :user_id, :consent_type, :is_granted, :ip_address, :user_agent)
        """
        db_manager.execute_query(query, {
            "consent_id": consent_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "is_granted": is_granted,
            "ip_address": ip_address,
            "user_agent": user_agent
        })
        return consent_id

    @staticmethod
    def get_consents_by_user(user_id):
        query = "SELECT * FROM USER_CONSENTS WHERE user_id = :user_id ORDER BY granted_at DESC"
        return db_manager.execute_query(query, {"user_id": user_id}, fetchall=True)

class AuditRepository:
    @staticmethod
    def log(actor_user_id, event_type, target_resource, resource_id=None, event_status="SUCCESS", details_json=None, ip_address=None):
        log_id = f"aud-{uuid.uuid4().hex[:12]}"
        query = """
        INSERT INTO AUDIT_LOGS 
        (log_id, actor_user_id, event_type, target_resource, resource_id, event_status, details_json, ip_address)
        VALUES (:log_id, :actor_user_id, :event_type, :target_resource, :resource_id, :event_status, :details_json, :ip_address)
        """
        db_manager.execute_query(query, {
            "log_id": log_id,
            "actor_user_id": actor_user_id,
            "event_type": event_type,
            "target_resource": target_resource,
            "resource_id": resource_id,
            "event_status": event_status,
            "details_json": details_json if isinstance(details_json, str) else json.dumps(details_json or {}),
            "ip_address": ip_address
        })
        return log_id

    @staticmethod
    def list_recent(limit=50):
        query = "SELECT * FROM AUDIT_LOGS ORDER BY timestamp DESC LIMIT :limit"
        return db_manager.execute_query(query, {"limit": limit}, fetchall=True)
