from flask import Blueprint, request, jsonify
from backend.security.auth import jwt_required, role_required
from backend.security.validation import sanitize_input
from backend.services.ai_health_service import AIHealthConsultationService
from backend.database.repositories import (
    ConsultationRepository, PatientProfileRepository, DoctorProfileRepository
)
from backend.security.audit import log_audit_event

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

@ai_bp.route("/chat", methods=["POST"])
@jwt_required
@role_required(["PATIENT"])
def chat_consultation():
    """
    Conversational AI Health Consultation:
    1. Checks emergency red flags.
    2. Incorporates patient clinical profile (allergies, conditions).
    3. Retains multi-turn dialogue memory.
    4. Enforces medical safety guidelines.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404

    data = request.get_json() or {}
    message_text = sanitize_input(data.get("message", "")).strip()
    consultation_id = data.get("consultation_id", None)

    if not message_text:
        return jsonify({"success": False, "error": "Message text cannot be empty."}), 400

    # Retrieve or create consultation session
    if consultation_id:
        consultation = ConsultationRepository.find_by_id(consultation_id)
        if not consultation or consultation["patient_id"] != pat["patient_id"]:
            return jsonify({"success": False, "error": "Consultation not found or unauthorized."}), 404
        history = ConsultationRepository.get_messages(consultation_id)
    else:
        # Create fresh consultation
        title = message_text[:40] + ("..." if len(message_text) > 40 else "")
        consultation_id = ConsultationRepository.create(
            patient_id=pat["patient_id"],
            title=title,
            consult_type="AI_ASSISTANT"
        )
        history = []

    # Store patient's user message
    ConsultationRepository.add_message(
        consultation_id=consultation_id,
        sender_type="PATIENT",
        sender_id=user["user_id"],
        message_text=message_text
    )

    # Process AI guidance
    guidance = AIHealthConsultationService.generate_health_guidance(
        user_message=message_text,
        conversation_history=history,
        patient_profile=pat
    )

    # Save AI response message
    ConsultationRepository.add_message(
        consultation_id=consultation_id,
        sender_type="AI_ASSISTANT",
        sender_id="AI_HEALTH_AGENT",
        message_text=guidance["message"],
        disclaimer_note=guidance["disclaimer"]
    )

    if guidance.get("red_flag_alert"):
        log_audit_event(
            "RED_FLAG_EMERGENCY_TRIGGERED", "CONSULTATIONS", consultation_id, "ALERT",
            {"query": message_text, "risk": "EMERGENCY"}
        )

    return jsonify({
        "success": True,
        "consultation_id": consultation_id,
        "response": guidance["message"],
        "risk_category": guidance["risk_category"],
        "red_flag_alert": bool(guidance["red_flag_alert"]),
        "disclaimer": guidance["disclaimer"],
        "follow_up_questions": guidance.get("follow_up_questions", []),
        "recommended_specialty": guidance.get("recommended_specialty", "General Medicine"),
        "ai_provider": guidance.get("ai_provider")
    })

@ai_bp.route("/consultations", methods=["GET"])
@jwt_required
@role_required(["PATIENT"])
def list_consultations():
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    consultations = ConsultationRepository.list_by_patient(pat["patient_id"])
    return jsonify({"success": True, "consultations": consultations})

@ai_bp.route("/consultations/<consultation_id>", methods=["GET"])
@jwt_required
def get_consultation_messages(consultation_id):
    user = request.current_user
    consultation = ConsultationRepository.find_by_id(consultation_id)
    if not consultation:
        return jsonify({"success": False, "error": "Consultation session not found."}), 404

    # Authorization
    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if consultation["patient_id"] != pat["patient_id"]:
            return jsonify({"success": False, "error": "Unauthorized."}), 403
    elif user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if not doc or doc.get("verification_status") != "VERIFIED" or consultation.get("assigned_doctor_id") != doc["doctor_id"]:
            return jsonify({"success": False, "error": "Unauthorized access to patient consultation."}), 403

    messages = ConsultationRepository.get_messages(consultation_id)
    return jsonify({
        "success": True,
        "consultation": consultation,
        "messages": messages
    })

@ai_bp.route("/consultations/<consultation_id>/share", methods=["POST"])
@jwt_required
@role_required(["PATIENT"])
def share_consultation_with_doctor(consultation_id):
    """
    Explicit Patient Consent Action:
    Allows patient to share an AI health discussion with a selected verified doctor.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    consultation = ConsultationRepository.find_by_id(consultation_id)

    if not consultation or consultation["patient_id"] != pat["patient_id"]:
        return jsonify({"success": False, "error": "Consultation not found."}), 404

    data = request.get_json() or {}
    doctor_id = data.get("doctor_id")

    doctor = DoctorProfileRepository.find_by_id(doctor_id)
    if not doctor or doctor.get("verification_status") != "VERIFIED":
        return jsonify({"success": False, "error": "Target doctor must be an active, verified doctor."}), 400

    ConsultationRepository.share_with_doctor(consultation_id, doctor_id)

    log_audit_event(
        "CONSULTATION_SHARED_WITH_DOCTOR", "CONSULTATIONS", consultation_id, "SUCCESS",
        {"doctor_id": doctor_id, "patient_id": pat["patient_id"]}
    )

    return jsonify({
        "success": True,
        "message": f"Consultation securely shared with Dr. {doctor['full_name']}."
    })
