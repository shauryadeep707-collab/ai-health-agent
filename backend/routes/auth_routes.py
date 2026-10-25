from flask import Blueprint, request, jsonify, make_response
from backend.security.auth import (
    hash_password, check_password, generate_jwt_token, jwt_required
)
from backend.security.validation import (
    validate_email, validate_password_strength, validate_phone, sanitize_input
)
from backend.security.rate_limiter import rate_limit
from backend.security.audit import log_audit_event
from backend.database.repositories import (
    UserRepository, PatientProfileRepository, DoctorProfileRepository, ConsentRepository
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/patient/register", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60)
def register_patient():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = sanitize_input(data.get("full_name", ""))
    phone = data.get("phone", "")
    dob = data.get("dob", None)
    gender = data.get("gender", "PREFER_NOT_TO_SAY")
    blood_group = data.get("blood_group", None)
    consent_health = data.get("consent_health", False)
    consent_privacy = data.get("consent_privacy", False)

    # Validations
    if not validate_email(email):
        return jsonify({"success": False, "error": "Invalid email address format."}), 400

    if not full_name:
        return jsonify({"success": False, "error": "Full name is required."}), 400

    is_strong, pass_err = validate_password_strength(password)
    if not is_strong:
        return jsonify({"success": False, "error": pass_err}), 400

    if not consent_health or not consent_privacy:
        return jsonify({
            "success": False,
            "error": "You must provide explicit consent for health data processing and privacy policy."
        }), 400

    if UserRepository.find_by_email(email):
        return jsonify({"success": False, "error": "An account with this email address already exists."}), 409

    # Create User
    pwd_hash = hash_password(password)
    user = UserRepository.create(
        email=email,
        password_hash=pwd_hash,
        role="PATIENT",
        full_name=full_name,
        phone_number=phone
    )

    # Create Patient Profile
    patient = PatientProfileRepository.create(
        user_id=user["user_id"],
        date_of_birth=dob,
        gender=gender,
        blood_group=blood_group,
        allergies=sanitize_input(data.get("allergies", "")),
        chronic_conditions=sanitize_input(data.get("chronic_conditions", ""))
    )

    # Record User Consents
    ip = request.remote_addr or "127.0.0.1"
    ua = request.headers.get("User-Agent", "")
    ConsentRepository.record_consent(user["user_id"], "HEALTH_DATA_PROCESSING", 1, ip, ua)
    ConsentRepository.record_consent(user["user_id"], "PRIVACY_POLICY", 1, ip, ua)

    log_audit_event("PATIENT_REGISTERED", "USERS", user["user_id"], "SUCCESS", {"email": email}, user["user_id"])

    token = generate_jwt_token(user)
    resp = make_response(jsonify({
        "success": True,
        "message": "Patient registered successfully.",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "patient_id": patient["patient_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }), 201)
    resp.set_cookie("auth_token", token, httponly=True, samesite="Lax")
    return resp

@auth_bp.route("/doctor/register", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60)
def register_doctor():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = sanitize_input(data.get("full_name", ""))
    phone = data.get("phone", "")
    qualification = sanitize_input(data.get("medical_qualification", ""))
    reg_no = sanitize_input(data.get("registration_number", "")).upper()
    council = sanitize_input(data.get("registration_council", ""))
    jurisdiction = sanitize_input(data.get("jurisdiction", ""))
    specialty = sanitize_input(data.get("specialty", "General Medicine"))
    consent_verification = data.get("consent_verification", False)

    if not validate_email(email):
        return jsonify({"success": False, "error": "Invalid email address format."}), 400

    if not full_name:
        return jsonify({"success": False, "error": "Full name is required."}), 400

    if not qualification or not reg_no or not council:
        return jsonify({"success": False, "error": "Medical qualification, registration number, and council are mandatory."}), 400

    is_strong, pass_err = validate_password_strength(password)
    if not is_strong:
        return jsonify({"success": False, "error": pass_err}), 400

    if not consent_verification:
        return jsonify({
            "success": False,
            "error": "Consent to identity and medical credential verification via DigiLocker / Medical Council is mandatory."
        }), 400

    if UserRepository.find_by_email(email):
        return jsonify({"success": False, "error": "An account with this email address already exists."}), 409

    pwd_hash = hash_password(password)
    user = UserRepository.create(
        email=email,
        password_hash=pwd_hash,
        role="DOCTOR",
        full_name=full_name,
        phone_number=phone
    )

    doc_profile = DoctorProfileRepository.create(
        user_id=user["user_id"],
        medical_qualification=qualification,
        registration_number=reg_no,
        registration_council=council,
        jurisdiction=jurisdiction,
        specialty=specialty,
        experience_years=int(data.get("experience_years", 0) or 0),
        clinic_address=sanitize_input(data.get("clinic_address", "")),
        consultation_fee=float(data.get("consultation_fee", 500.0) or 500.0),
        bio=sanitize_input(data.get("bio", ""))
    )

    ip = request.remote_addr or "127.0.0.1"
    ua = request.headers.get("User-Agent", "")
    ConsentRepository.record_consent(user["user_id"], "DOCTOR_VERIFICATION_CONSENT", 1, ip, ua)

    log_audit_event("DOCTOR_REGISTERED", "USERS", user["user_id"], "SUCCESS", {
        "email": email, "reg_no": reg_no, "council": council
    }, user["user_id"])

    token = generate_jwt_token(user)
    resp = make_response(jsonify({
        "success": True,
        "message": "Doctor registered successfully. Please proceed with DigiLocker verification.",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "doctor_id": doc_profile["doctor_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "verification_status": "PENDING"
        }
    }), 201)
    resp.set_cookie("auth_token", token, httponly=True, samesite="Lax")
    return resp

@auth_bp.route("/login", methods=["POST"])
@rate_limit(max_requests=15, window_seconds=60)
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    expected_role = data.get("role", None)

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    user = UserRepository.find_by_email(email)
    if not user:
        log_audit_event("LOGIN_FAILED", "USERS", email, "FAILURE", {"reason": "User not found"})
        return jsonify({
            "success": False,
            "error": f"No account found with '{email}'. Please check your email or click 'Create Patient Account' below."
        }), 404

    if not check_password(password, user["password_hash"]):
        log_audit_event("LOGIN_FAILED", "USERS", email, "FAILURE", {"reason": "Incorrect password"})
        return jsonify({
            "success": False,
            "error": "Incorrect password. Please verify your password and try again."
        }), 401

    if not user.get("is_active"):
        return jsonify({"success": False, "error": "This account has been deactivated. Please contact support."}), 403

    if expected_role and user["role"].upper() != expected_role.upper():
        return jsonify({
            "success": False,
            "error": f"Role mismatch. This account is registered as a {user['role']}. Please use the {user['role'].lower()} portal."
        }), 403

    UserRepository.update_last_login(user["user_id"])

    profile_data = {}
    if user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if doc:
            profile_data["doctor_id"] = doc["doctor_id"]
            profile_data["verification_status"] = doc.get("verification_status", "PENDING")
            profile_data["specialty"] = doc.get("specialty")
    elif user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if pat:
            profile_data["patient_id"] = pat["patient_id"]

    token = generate_jwt_token(user)
    log_audit_event("LOGIN_SUCCESS", "USERS", user["user_id"], "SUCCESS", {"role": user["role"]}, user["user_id"])

    resp = make_response(jsonify({
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            **profile_data
        }
    }))
    resp.set_cookie("auth_token", token, httponly=True, samesite="Lax")
    return resp

@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user_info():
    user = request.current_user
    profile_info = {}
    if user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if doc:
            profile_info = {
                "doctor_id": doc["doctor_id"],
                "qualification": doc["medical_qualification"],
                "registration_number": doc["registration_number"],
                "registration_council": doc["registration_council"],
                "jurisdiction": doc["jurisdiction"],
                "specialty": doc["specialty"],
                "experience_years": doc["experience_years"],
                "consultation_fee": doc["consultation_fee"],
                "verification_status": doc["verification_status"],
                "verified_at": doc["verified_at"]
            }
    elif user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if pat:
            profile_info = {
                "patient_id": pat["patient_id"],
                "date_of_birth": pat["date_of_birth"],
                "gender": pat["gender"],
                "blood_group": pat["blood_group"],
                "allergies": pat["allergies"],
                "chronic_conditions": pat["chronic_conditions"]
            }

    consents = ConsentRepository.get_consents_by_user(user["user_id"])

    return jsonify({
        "success": True,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "phone_number": user["phone_number"],
            "role": user["role"],
            **profile_info,
            "consents": [{"type": c["consent_type"], "granted_at": c["granted_at"]} for c in consents]
        }
    })

@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"success": True, "message": "Logged out successfully."}))
    resp.delete_cookie("auth_token")
    return resp
