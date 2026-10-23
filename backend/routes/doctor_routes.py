from flask import Blueprint, request, jsonify, redirect
from backend.security.auth import jwt_required, role_required, verified_doctor_required
from backend.services.digilocker_service import DigiLockerService
from backend.services.doctor_verification_service import DoctorVerificationService
from backend.database.repositories import (
    DoctorProfileRepository, DoctorVerificationRepository, AppointmentRepository,
    ConsultationRepository, MedicalReportRepository, UserRepository
)
from backend.security.audit import log_audit_event

doctor_bp = Blueprint("doctor", __name__, url_prefix="/api/doctor")

@doctor_bp.route("/digilocker/initiate", methods=["GET", "POST"])
@jwt_required
@role_required(["DOCTOR"])
def initiate_digilocker_flow():
    """
    Step 1: Doctor clicks 'Verify with DigiLocker'.
    Generates anti-CSRF state and authorized redirect URL.
    """
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    is_demo = request.args.get("demo", "false").lower() in ("true", "1")
    flow_info = DigiLockerService.generate_authorization_url(doc["doctor_id"], is_demo=is_demo)

    # Record initial pending verification entry
    verification_id = DoctorVerificationRepository.create(
        doctor_id=doc["doctor_id"],
        provider_source="DIGILOCKER",
        oauth_state=flow_info["state"],
        doc_type="DOCREG",
        status="PENDING"
    )

    log_audit_event(
        "DIGILOCKER_FLOW_INITIATED", "DOCTOR_PROFILES", doc["doctor_id"], "SUCCESS",
        {"oauth_state": flow_info["state"], "mode": flow_info["mode"]}
    )

    return jsonify({
        "success": True,
        "verification_id": verification_id,
        "auth_url": flow_info["auth_url"],
        "state": flow_info["state"],
        "mode": flow_info["mode"],
        "message": flow_info["message"]
    })

@doctor_bp.route("/digilocker/sandbox-authorize", methods=["GET"])
def sandbox_authorization_page():
    """
    Sandbox / Development gateway simulating DigiLocker authorization screen.
    Opens the interactive DigiLocker consent gateway screen.
    """
    state = request.args.get("state")
    doctor_id = request.args.get("doctor_id")

    # Render official DigiLocker consent screen
    return redirect(f"/digilocker-auth.html?state={state}&doctor_id={doctor_id}")

@doctor_bp.route("/digilocker/callback", methods=["GET"])
def digilocker_callback():
    """
    Official OAuth2 callback endpoint:
    1. Validates 'state' parameter against active OAuth sessions (prevents CSRF).
    2. Exchanges 'code' for access token (or loads sandbox payload).
    3. Fetches issued medical registration certificate.
    4. Runs multi-tier verification state machine.
    5. Redirects to doctor-dashboard.html with status query param.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    scenario = request.args.get("scenario", "MATCH")

    if error:
        return redirect(f"/doctor-dashboard.html?verification_status=REJECTED&error={error}")

    state_data = DigiLockerService.validate_state(state)
    if not state_data:
        # Invalid or expired state
        return redirect("/doctor-dashboard.html?verification_status=REJECTED&error=INVALID_OR_EXPIRED_OAUTH_STATE")

    doctor_id = state_data["doctor_id"]
    doctor = DoctorProfileRepository.find_by_id(doctor_id)
    if not doctor:
        return redirect("/doctor-dashboard.html?verification_status=REJECTED&error=DOCTOR_PROFILE_NOT_FOUND")

    # Fetch existing pending verification record
    v_rec = DoctorVerificationRepository.find_by_state(state)
    v_id = v_rec["verification_id"] if v_rec else None

    # Step: Document fetching
    doc_payload = None
    if state_data.get("is_demo") or "DL_AUTH_CODE_" in (code or ""):
        # Sandbox simulated document payload
        doc_payload = DigiLockerService.get_sandbox_credential_payload(doctor, scenario=scenario)
    else:
        # Production Live DigiLocker token exchange and document retrieval
        success, token_data, err_msg = DigiLockerService.exchange_code_for_token(code)
        if not success:
            DoctorVerificationRepository.update(
                verification_id=v_id,
                status="REVIEW_REQUIRED",
                rejection_reason=err_msg,
                review_notes="DigiLocker token exchange failed. Flagged for manual review."
            )
            return redirect(f"/doctor-dashboard.html?verification_status=REVIEW_REQUIRED&message=TOKEN_EXCHANGE_FAILED")

        access_token = token_data.get("access_token")
        doc_success, doc_payload, doc_err = DigiLockerService.fetch_doctor_registration_doc(access_token)
        if not doc_success:
            DoctorVerificationRepository.update(
                verification_id=v_id,
                status="REVIEW_REQUIRED",
                rejection_reason=doc_err,
                review_notes="Doctor registration certificate not found in user's DigiLocker. Flagged for manual review."
            )
            return redirect("/doctor-dashboard.html?verification_status=REVIEW_REQUIRED&message=DOC_NOT_FOUND")

    # Step: Verification Evaluation via State Machine
    result = DoctorVerificationService.process_digilocker_document(
        doctor_id=doctor_id,
        doc_payload=doc_payload,
        verification_id=v_id
    )

    return redirect(f"/doctor-dashboard.html?verification_status={result['status']}&score={result['name_match_score']}")

@doctor_bp.route("/digilocker/sandbox-verify", methods=["POST"])
@jwt_required
@role_required(["DOCTOR"])
def sandbox_trigger_scenario():
    """
    Dedicated endpoint for testing different verification outcomes:
    'MATCH' -> VERIFIED
    'NAME_MISMATCH' -> REVIEW_REQUIRED
    'REG_MISMATCH' -> REJECTED
    """
    data = request.get_json() or {}
    scenario = data.get("scenario", "MATCH").upper()

    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    payload = DigiLockerService.get_sandbox_credential_payload(doc, scenario=scenario)
    result = DoctorVerificationService.process_digilocker_document(
        doctor_id=doc["doctor_id"],
        doc_payload=payload
    )

    return jsonify({
        "success": True,
        "scenario_tested": scenario,
        "verification_result": result,
        "is_sandbox_simulation": True
    })

@doctor_bp.route("/verification/status", methods=["GET"])
@jwt_required
@role_required(["DOCTOR"])
def get_verification_status():
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    v_rec = DoctorVerificationRepository.find_latest_by_doctor_id(doc["doctor_id"])

    return jsonify({
        "success": True,
        "doctor_id": doc["doctor_id"],
        "verification_status": doc["verification_status"],
        "verified_at": doc["verified_at"],
        "verification_record": v_rec,
        "registration_details": {
            "name": doc["full_name"],
            "registration_number": doc["registration_number"],
            "registration_council": doc["registration_council"],
            "jurisdiction": doc["jurisdiction"],
            "specialty": doc["specialty"]
        }
    })

@doctor_bp.route("/verification/request-review", methods=["POST"])
@jwt_required
@role_required(["DOCTOR"])
def request_manual_review():
    """
    If a doctor's medical council is not on DigiLocker or if name mismatch occurred,
    allows them to request official administrative manual review.
    """
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    data = request.get_json() or {}
    notes = data.get("notes", "Doctor requested manual council verification.")

    DoctorProfileRepository.update_verification_status(doc["doctor_id"], "REVIEW_REQUIRED")
    DoctorVerificationRepository.create(
        doctor_id=doc["doctor_id"],
        provider_source="MANUAL_COUNCIL_REVIEW",
        doc_type="DOCREG",
        status="REVIEW_REQUIRED"
    )

    log_audit_event("MANUAL_REVIEW_REQUESTED", "DOCTOR_PROFILES", doc["doctor_id"], "WARNING", {"notes": notes})

    return jsonify({
        "success": True,
        "message": "Manual review request submitted. Verification status is now REVIEW_REQUIRED.",
        "verification_status": "REVIEW_REQUIRED"
    })

@doctor_bp.route("/dashboard/stats", methods=["GET"])
@jwt_required
@role_required(["DOCTOR"])
def get_doctor_dashboard_stats():
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor not found."}), 404

    appointments = AppointmentRepository.list_by_doctor(doc["doctor_id"])
    consultations = ConsultationRepository.list_by_doctor(doc["doctor_id"])

    pending_apts = sum(1 for a in appointments if a.get("status") in ("BOOKED", "CONFIRMED"))

    return jsonify({
        "success": True,
        "doctor_profile": doc,
        "stats": {
            "total_appointments": len(appointments),
            "pending_appointments": pending_apts,
            "shared_consultations": len(consultations),
            "verification_status": doc["verification_status"]
        }
    })

@doctor_bp.route("/dashboard/appointments", methods=["GET"])
@jwt_required
@role_required(["DOCTOR"])
def get_doctor_appointments():
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    if not doc:
        return jsonify({"success": False, "error": "Doctor not found."}), 404

    appointments = AppointmentRepository.list_by_doctor(doc["doctor_id"])
    return jsonify({"success": True, "appointments": appointments})

@doctor_bp.route("/dashboard/consultations", methods=["GET"])
@jwt_required
@role_required(["DOCTOR"])
@verified_doctor_required
def get_doctor_shared_consultations():
    """
    CRITICAL PRIVACY CHECK: Only verified doctors can access patient consultations
    specifically authorized/shared by the patient.
    """
    user = request.current_user
    doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
    consultations = ConsultationRepository.list_by_doctor(doc["doctor_id"])
    return jsonify({"success": True, "consultations": consultations})
