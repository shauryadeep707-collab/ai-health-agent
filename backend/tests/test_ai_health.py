import io
import json
import pytest
from backend.app import create_app
from backend.config import Config
from backend.database.connection import db_manager
from backend.database.repositories import UserRepository, DoctorProfileRepository, PatientProfileRepository
from backend.services.digilocker_service import DigiLockerService
from backend.services.doctor_verification_service import (
    DoctorVerificationService, calculate_name_similarity, normalize_name, normalize_reg_no
)
from backend.services.ai_health_service import AIHealthConsultationService
from backend.security.validation import validate_uploaded_file, validate_email, validate_password_strength

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

# -----------------------------------------------------------------------------
# 1. Validation & Security Unit Tests
# -----------------------------------------------------------------------------
def test_email_validation():
    assert validate_email("doctor.test@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("") is False

def test_password_strength_validation():
    valid, _ = validate_password_strength("StrongPass123#")
    assert valid is True
    short, msg = validate_password_strength("Short1")
    assert short is False
    no_num, msg = validate_password_strength("NoNumbersHerePass")
    assert no_num is False

def test_file_upload_magic_bytes_check():
    # Valid PDF Header
    pdf_bytes = io.BytesIO(b"%PDF-1.4 simulated test content")
    pdf_bytes.filename = "report.pdf"
    valid, _, ext = validate_uploaded_file(pdf_bytes)
    assert valid is True
    assert ext == "pdf"

    # Spoofed PDF (PNG bytes disguised as .pdf)
    spoofed = io.BytesIO(b"\x89PNG\r\n\x1a\n fake")
    spoofed.filename = "evil.pdf"
    valid, err, _ = validate_uploaded_file(spoofed)
    assert valid is False
    assert "header does not match" in err

    # Executable disguised as .jpg
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    fake_exe.filename = "malware.jpg"
    valid, err, _ = validate_uploaded_file(fake_exe)
    assert valid is False

# -----------------------------------------------------------------------------
# 2. Name Similarity & State Machine Unit Tests
# -----------------------------------------------------------------------------
def test_name_normalization_and_similarity():
    assert normalize_name("Dr. Priya Sharma") == "priya sharma"
    assert normalize_name("Doctor Priya K. Sharma") == "priya k sharma"

    # Exact or near-exact matches
    score_exact = calculate_name_similarity("Dr. Priya Sharma", "Priya Sharma")
    assert score_exact >= 85.0

    # Token match with middle initial
    score_middle = calculate_name_similarity("Dr. Priya Sharma", "Priya K Sharma")
    assert score_middle >= 80.0

    # Completely different names
    score_diff = calculate_name_similarity("Dr. Priya Sharma", "Dr. Rajesh Varma")
    assert score_diff < 50.0

def test_registration_number_normalization():
    assert normalize_reg_no("MCI-1998-04281") == "MCI199804281"
    assert normalize_reg_no("mci / 1998 / 04281") == "MCI199804281"

# -----------------------------------------------------------------------------
# 3. DigiLocker State Machine Transitions
# -----------------------------------------------------------------------------
def test_digilocker_state_machine_verified():
    # Using seeded doctor dp-001 (Dr. Priya Sharma, MCI-1998-04281)
    doc = DoctorProfileRepository.find_by_id("dp-001")
    assert doc is not None

    payload_match = DigiLockerService.get_sandbox_credential_payload(doc, scenario="MATCH")
    result = DoctorVerificationService.process_digilocker_document("dp-001", payload_match)

    assert result["status"] == "VERIFIED"
    assert result["reg_no_match"] is True
    assert result["name_match_score"] >= 85.0

def test_digilocker_state_machine_review_required():
    doc = DoctorProfileRepository.find_by_id("dp-001")
    # Simulate slight mismatch in name
    payload_mismatch = DigiLockerService.get_sandbox_credential_payload(doc, scenario="NAME_MISMATCH")
    result = DoctorVerificationService.process_digilocker_document("dp-001", payload_mismatch)

    assert result["status"] == "REVIEW_REQUIRED"
    assert "requires administrative confirmation" in result["review_notes"]

def test_digilocker_state_machine_rejected():
    doc = DoctorProfileRepository.find_by_id("dp-001")
    # Simulate wrong registration number
    payload_wrong_reg = DigiLockerService.get_sandbox_credential_payload(doc, scenario="REG_MISMATCH")
    result = DoctorVerificationService.process_digilocker_document("dp-001", payload_wrong_reg)

    assert result["status"] == "REJECTED"
    assert result["rejection_reason"] is not None

# -----------------------------------------------------------------------------
# 4. Authentication & RBAC Endpoint Tests
# -----------------------------------------------------------------------------
import uuid

def test_patient_registration_and_login(client):
    email = f"test.patient.{uuid.uuid4().hex[:8]}@test.org"
    reg_payload = {
        "full_name": "Test Patient",
        "email": email,
        "phone": "+919876543299",
        "password": "SecurePassword123#",
        "gender": "FEMALE",
        "blood_group": "O+",
        "consent_health": True,
        "consent_privacy": True
    }
    res = client.post("/api/auth/patient/register", json=reg_payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123#",
        "role": "PATIENT"
    })
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True

def test_doctor_registration_starts_as_pending(client):
    email = f"test.doc.{uuid.uuid4().hex[:8]}@hospital.org"
    reg_payload = {
        "full_name": "Dr. Vikas Rao",
        "email": email,
        "phone": "+919876543288",
        "medical_qualification": "MBBS, MS (Orthopedics)",
        "registration_number": f"TMC-2018-{uuid.uuid4().hex[:4].upper()}",
        "registration_council": "Tamil Nadu Medical Council",
        "jurisdiction": "Tamil Nadu, India",
        "specialty": "Orthopedics",
        "password": "DoctorPassword123#",
        "consent_verification": True
    }
    res = client.post("/api/auth/doctor/register", json=reg_payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["verification_status"] == "PENDING"

# -----------------------------------------------------------------------------
# 5. DigiLocker OAuth Callback Security
# -----------------------------------------------------------------------------
def test_digilocker_callback_invalid_state(client):
    res = client.get("/api/doctor/digilocker/callback?code=mock_code&state=non_existent_fake_state")
    # Redirects to dashboard with error
    assert res.status_code == 302
    assert "INVALID_OR_EXPIRED_OAUTH_STATE" in res.location

# -----------------------------------------------------------------------------
# 6. Medical Safety & Emergency Triage Tests
# -----------------------------------------------------------------------------
def test_emergency_red_flag_screening():
    # Chest pain emergency
    is_red, desc = AIHealthConsultationService.screen_emergency_red_flags("I have crushing chest pain radiating to my left arm")
    assert is_red is True
    assert "Chest pain" in desc

    # Stroke warning sign
    is_red, desc = AIHealthConsultationService.screen_emergency_red_flags("Sudden weakness on one side and slurred speech")
    assert is_red is True
    assert "Stroke" in desc

    # Routine non-emergency query
    is_red, _ = AIHealthConsultationService.screen_emergency_red_flags("I have a mild runny nose and sneezing")
    assert is_red is False

def test_health_consultation_response_structure():
    guidance = AIHealthConsultationService.generate_health_guidance("I have mild joint stiffness in the morning")
    assert "message" in guidance
    assert guidance["risk_category"] in ("LOW", "MODERATE", "HIGH")
    assert "disclaimer" in guidance
    assert "educational purposes only" in guidance["disclaimer"].lower()

# -----------------------------------------------------------------------------
# 7. Medicine & Drug Interaction Tests
# -----------------------------------------------------------------------------
def test_medicine_search_and_interaction(client):
    # Search
    res = client.get("/api/medicines/search?query=paracetamol")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["medicines"]) >= 1

    # Check known interaction between med-003 (Atorvastatin) and med-004 (Augmentin)
    inter_res = client.post("/api/medicines/check-interactions", json={
        "medicine_ids": ["med-003", "med-004"]
    })
    assert inter_res.status_code == 200
    inter_data = inter_res.get_json()
    assert inter_data["has_interactions"] is True
    assert inter_data["count"] >= 1

# -----------------------------------------------------------------------------
# 8. Role Authorization & Privacy Access Control Tests
# -----------------------------------------------------------------------------
def test_unauthenticated_request_rejected(client):
    res = client.get("/api/patient/reports")
    assert res.status_code == 401
    assert res.get_json()["code"] == "AUTH_REQUIRED"

def test_patient_forbidden_from_doctor_endpoint(client):
    # Log in as patient
    login_res = client.post("/api/auth/login", json={
        "email": "rahul.mehta@email.com",
        "password": "Password123!",
        "role": "PATIENT"
    })
    assert login_res.status_code == 200
    token = login_res.get_json()["token"]

    # Attempt to access doctor-only dashboard endpoint
    doc_res = client.get("/api/doctor/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
    assert doc_res.status_code == 403
    assert doc_res.get_json()["code"] == "FORBIDDEN_ROLE"

def test_unverified_doctor_forbidden_from_patient_records(client):
    # Dr. Anita Deshmukh (u-doc-003) is PENDING verification
    login_res = client.post("/api/auth/login", json={
        "email": "dr.anita.deshmukh@medcare.org",
        "password": "Password123!",
        "role": "DOCTOR"
    })
    assert login_res.status_code == 200
    token = login_res.get_json()["token"]

    # Doctor attempts to access patient consultations
    consult_res = client.get("/api/doctor/dashboard/consultations", headers={"Authorization": f"Bearer {token}"})
    assert consult_res.status_code == 403
    assert consult_res.get_json()["code"] == "VERIFICATION_REQUIRED"

def test_medical_report_upload_and_extraction(client):
    # Log in as patient
    login_res = client.post("/api/auth/login", json={
        "email": "rahul.mehta@email.com",
        "password": "Password123!",
        "role": "PATIENT"
    })
    token = login_res.get_json()["token"]

    # Upload simulated blood chemistry report with genuine PDF header
    fake_pdf = io.BytesIO(b"%PDF-1.4\nTest: Total Cholesterol 245 mg/dL\nFasting Blood Sugar 115 mg/dL\nHbA1c 6.8 %\n%%EOF")
    data = {
        "file": (fake_pdf, "test_blood_panel.pdf"),
        "test_type": "Metabolic & Lipid Panel",
        "report_date": "2026-10-20"
    }

    res = client.post(
        "/api/patient/reports/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    resp_data = res.get_json()
    assert resp_data["success"] is True
    assert "report_id" in resp_data
    assert len(resp_data["test_values"]) >= 1
    assert "ai_analysis" in resp_data
    assert "summary_plain_en" in resp_data["ai_analysis"]
