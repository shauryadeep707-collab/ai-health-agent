import re
import logging
from flask import Blueprint, request, jsonify
from backend.security.auth import jwt_required, role_required
from backend.security.validation import sanitize_input
from backend.database.repositories import (
    DoctorProfileRepository, AppointmentRepository, PatientProfileRepository, ConsultationRepository
)
from backend.services.ai_health_service import AIHealthConsultationService
from backend.security.audit import log_audit_event

logger = logging.getLogger(__name__)

appointment_bp = Blueprint("appointment", __name__, url_prefix="/api/appointments")


def _clean_doctor_name(full_name: str) -> str:
    """Normalizes doctor name so 'Dr.' appears exactly once."""
    clean = re.sub(r"^(?:dr\.?\s*)+", "", (full_name or "").strip(), flags=re.IGNORECASE).strip()
    return f"Dr. {clean}" if clean else "Doctor"


def _is_ai_doctor(doctor: dict) -> bool:
    """Returns True for AI-connected doctors (such as Dr. Priya Sharma)."""
    doc_name = (doctor.get("full_name") or doctor.get("doctor_name") or "").lower()
    doc_bio = (doctor.get("bio") or "").lower()
    doc_specialty = (doctor.get("specialty") or "").lower()
    return "priya" in doc_name or "ai" in doc_name or "ai" in doc_bio or "ai" in doc_specialty

@appointment_bp.route("/doctors", methods=["GET"])
def list_doctors():
    """
    Search doctors by specialty, location/jurisdiction, or name.
    Does not display fabricated doctor profiles.
    """
    query = request.args.get("query", "").strip()
    specialty = request.args.get("specialty", "").strip()
    jurisdiction = request.args.get("jurisdiction", "").strip()
    verified_only = request.args.get("verified_only", "true").lower() in ("true", "1")

    doctors = DoctorProfileRepository.search(
        query=query,
        specialty=specialty,
        jurisdiction=jurisdiction,
        verified_only=verified_only
    )

    # Sanitize and present public profile
    results = []
    for d in doctors:
        results.append({
            "doctor_id": d["doctor_id"],
            "full_name": d["full_name"],
            "specialty": d["specialty"],
            "qualification": d["medical_qualification"],
            "experience_years": d["experience_years"],
            "registration_council": d["registration_council"],
            "jurisdiction": d["jurisdiction"],
            "clinic_address": d["clinic_address"],
            "consultation_fee": d["consultation_fee"],
            "verification_status": d["verification_status"],
            "bio": d["bio"],
            "available_slots": ["09:30 AM", "11:00 AM", "02:30 PM", "04:00 PM", "05:30 PM"]
        })

    return jsonify({"success": True, "doctors": results, "count": len(results)})

@appointment_bp.route("/book", methods=["POST"])
@jwt_required
@role_required(["PATIENT"])
def book_appointment():
    """
    Book an appointment with a verified doctor.
    Confirms booking only when backend completes database transaction.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404

    data = request.get_json() or {}
    doctor_id = data.get("doctor_id")
    date_str = data.get("appointment_date")
    slot_time = data.get("slot_time")
    reason = sanitize_input(data.get("reason", ""))

    if not doctor_id or not date_str or not slot_time:
        return jsonify({"success": False, "error": "Doctor, appointment date, and time slot are required."}), 400

    doctor = DoctorProfileRepository.find_by_id(doctor_id)
    if not doctor:
        return jsonify({"success": False, "error": "Doctor not found."}), 404

    if doctor.get("verification_status") != "VERIFIED":
        return jsonify({"success": False, "error": "Appointments can only be scheduled with verified medical doctors."}), 400

    # Check if doctor is Dr. Priya / AI Doctor Specialist who automatically accepts bookings
    is_ai_doctor = _is_ai_doctor(doctor)
    initial_status = "CONFIRMED" if is_ai_doctor else "BOOKED"

    apt_id = AppointmentRepository.create(
        patient_id=pat["patient_id"],
        doctor_id=doctor_id,
        appointment_date=date_str,
        slot_time=slot_time,
        reason_for_visit=reason,
        status=initial_status
    )

    doc_display = _clean_doctor_name(doctor.get("full_name", ""))

    if is_ai_doctor:
        AppointmentRepository.update_status(
            apt_id, "CONFIRMED",
            doctor_notes=f"Appointment automatically accepted by {doc_display} (AI Clinical Specialist). Consultation chat is active."
        )
        msg = f"Appointment instantly accepted & confirmed by {doc_display} (AI Specialist)! Your Consultation Chat is ready."
    else:
        msg = f"Appointment request submitted with {doc_display} for {date_str} at {slot_time}. Awaiting doctor confirmation."

    log_audit_event(
        "APPOINTMENT_BOOKED", "APPOINTMENTS", apt_id, "SUCCESS",
        {
            "doctor_id": doctor_id,
            "patient_id": pat["patient_id"],
            "date": date_str,
            "time": slot_time,
            "status": initial_status,
            "is_auto_accepted": is_ai_doctor
        }
    )

    return jsonify({
        "success": True,
        "message": msg,
        "appointment_id": apt_id,
        "status": initial_status,
        "is_auto_accepted": is_ai_doctor
    }), 201

@appointment_bp.route("/my", methods=["GET"])
@jwt_required
def get_my_appointments():
    user = request.current_user
    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        apts = AppointmentRepository.list_by_patient(pat["patient_id"])
        for a in apts:
            a["is_ai_doctor"] = _is_ai_doctor(a)
    elif user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        apts = AppointmentRepository.list_by_doctor(doc["doctor_id"])
    else:
        apts = []

    return jsonify({"success": True, "appointments": apts})

@appointment_bp.route("/<appointment_id>/status", methods=["PUT"])
@jwt_required
def update_appointment_status(appointment_id):
    user = request.current_user
    apt = AppointmentRepository.find_by_id(appointment_id)
    if not apt:
        return jsonify({"success": False, "error": "Appointment not found."}), 404

    data = request.get_json() or {}
    new_status = data.get("status", "").upper()
    notes = sanitize_input(data.get("doctor_notes", ""))

    valid_statuses = ("BOOKED", "CONFIRMED", "CANCELLED", "COMPLETED", "RESCHEDULED")
    if new_status not in valid_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Allowed: {', '.join(valid_statuses)}"}), 400

    # Authorization
    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if apt["patient_id"] != pat["patient_id"]:
            return jsonify({"success": False, "error": "Unauthorized."}), 403
        if new_status not in ("CANCELLED",):
            return jsonify({"success": False, "error": "Patients can only cancel appointments."}), 403
    elif user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if apt["doctor_id"] != doc["doctor_id"]:
            return jsonify({"success": False, "error": "Unauthorized."}), 403

    AppointmentRepository.update_status(appointment_id, new_status, notes or None)

    log_audit_event("APPOINTMENT_STATUS_UPDATED", "APPOINTMENTS", appointment_id, "SUCCESS", {"new_status": new_status})

    return jsonify({"success": True, "message": f"Appointment status updated to {new_status}."})


def _authorize_appointment_chat(user, appointment_id, allow_completed=False):
    """Validates appointment ownership and status for consultation chat access."""
    apt = AppointmentRepository.find_by_id(appointment_id)
    if not apt:
        return None, None, None, (jsonify({"success": False, "error": "Appointment not found."}), 404)

    allowed = ("CONFIRMED", "COMPLETED") if allow_completed else ("CONFIRMED",)
    if apt.get("status") not in allowed:
        return None, None, None, (jsonify({
            "success": False,
            "error": "Consultation chat unlocks only after the doctor confirms this appointment."
        }), 403)

    pat = PatientProfileRepository.find_by_id(apt["patient_id"])
    doc = DoctorProfileRepository.find_by_id(apt["doctor_id"])
    if not pat or not doc:
        return None, None, None, (jsonify({"success": False, "error": "Appointment participants not found."}), 404)

    if user["role"] == "PATIENT":
        caller_pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if not caller_pat or caller_pat["patient_id"] != apt["patient_id"]:
            return None, None, None, (jsonify({"success": False, "error": "Unauthorized."}), 403)
    elif user["role"] == "DOCTOR":
        caller_doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if not caller_doc or caller_doc["doctor_id"] != apt["doctor_id"]:
            return None, None, None, (jsonify({"success": False, "error": "Unauthorized."}), 403)
    else:
        return None, None, None, (jsonify({"success": False, "error": "Unauthorized role."}), 403)

    return apt, pat, doc, None


@appointment_bp.route("/<appointment_id>/chat", methods=["GET"])
@jwt_required
def get_appointment_chat(appointment_id):
    """Returns persistent appointment chat history, auto-seeding greeting on first open."""
    user = request.current_user
    apt, pat, doc, err_resp = _authorize_appointment_chat(user, appointment_id, allow_completed=True)
    if err_resp:
        return err_resp

    doc_display = _clean_doctor_name(doc.get("full_name", ""))
    is_ai_doc = _is_ai_doctor(doc)
    chat_id = f"apt-chat-{appointment_id}"
    ConsultationRepository.get_or_create_for_appointment(
        consultation_id=chat_id,
        patient_id=apt["patient_id"],
        doctor_id=apt["doctor_id"],
        title=f"Appointment Chat: {doc_display} ({apt['appointment_date']})"
    )

    messages = ConsultationRepository.get_messages(chat_id)
    if not messages:
        reason = (apt.get("reason_for_visit") or "").strip()
        reason_note = f' I see your visit reason: "{reason}".' if reason else ""
        if is_ai_doc:
            greeting = (
                f"Hello {pat.get('full_name', 'there')}! I am **{doc_display}** ({doc.get('specialty', 'Specialist')}).\n\n"
                f"Your appointment for **{apt['appointment_date']} at {apt['slot_time']}** is confirmed.{reason_note}\n\n"
                "Let's start our consultation — tell me how you're feeling right now or what symptoms are bothering you, and we'll go step by step."
            )
        else:
            greeting = (
                f"Hello {pat.get('full_name', 'there')}! Your consultation chat with **{doc_display}** "
                f"({doc.get('specialty', 'Specialist')}) for **{apt['appointment_date']} at {apt['slot_time']}** is now active.{reason_note}\n\n"
                "Please describe your symptoms or questions below."
            )
        ConsultationRepository.add_message(
            consultation_id=chat_id,
            sender_type="DOCTOR",
            sender_id=doc["doctor_id"],
            message_text=greeting
        )
        messages = ConsultationRepository.get_messages(chat_id)

    return jsonify({
        "success": True,
        "consultation_id": chat_id,
        "appointment": {
            "appointment_id": apt["appointment_id"],
            "appointment_date": str(apt["appointment_date"]),
            "slot_time": apt["slot_time"],
            "status": apt["status"],
            "reason_for_visit": apt.get("reason_for_visit", "")
        },
        "doctor": {
            "doctor_id": doc["doctor_id"],
            "full_name": doc_display,
            "specialty": doc.get("specialty", ""),
            "qualification": doc.get("medical_qualification", "")
        },
        "patient_name": pat.get("full_name", "Patient"),
        "is_ai_doctor": is_ai_doc,
        "messages": messages
    })


@appointment_bp.route("/<appointment_id>/chat", methods=["POST"])
@jwt_required
def send_appointment_chat_message(appointment_id):
    """
    Sends a chat message inside a confirmed appointment.
    When the assigned doctor is Dr. Priya / AI Specialist, Gemini AI replies automatically as that doctor.
    """
    user = request.current_user
    apt, pat, doc, err_resp = _authorize_appointment_chat(user, appointment_id, allow_completed=False)
    if err_resp:
        return err_resp

    data = request.get_json() or {}
    message_text = sanitize_input(data.get("message", "")).strip()
    if not message_text:
        return jsonify({"success": False, "error": "Message text cannot be empty."}), 400

    doc_display = _clean_doctor_name(doc.get("full_name", ""))
    is_ai_doc = _is_ai_doctor(doc)
    chat_id = f"apt-chat-{appointment_id}"
    ConsultationRepository.get_or_create_for_appointment(
        consultation_id=chat_id,
        patient_id=apt["patient_id"],
        doctor_id=apt["doctor_id"],
        title=f"Appointment Chat: {doc_display} ({apt['appointment_date']})"
    )

    if user["role"] == "DOCTOR":
        ConsultationRepository.add_message(
            consultation_id=chat_id,
            sender_type="DOCTOR",
            sender_id=doc["doctor_id"],
            message_text=message_text
        )
        return jsonify({
            "success": True,
            "ai_replied": False,
            "sender_type": "DOCTOR",
            "reply": message_text
        })

    # Patient sending message: load prior history before appending current turn
    prior_history = ConsultationRepository.get_messages(chat_id)
    ConsultationRepository.add_message(
        consultation_id=chat_id,
        sender_type="PATIENT",
        sender_id=user["user_id"],
        message_text=message_text
    )

    if not is_ai_doc:
        return jsonify({
            "success": True,
            "ai_replied": False,
            "message": f"Message sent to {doc_display}. They will review and reply shortly."
        })

    # Connect AI Doctor Engine as the appointed AI Specialist (e.g. Dr. Priya Sharma)
    doc_ctx = {
        **doc,
        "full_name": doc_display,
        "appointment_reason": apt.get("reason_for_visit", "")
    }
    guidance = AIHealthConsultationService.generate_health_guidance(
        user_message=message_text,
        conversation_history=prior_history,
        patient_profile=pat,
        doctor_profile=doc_ctx
    )

    learned_info = guidance.get("learned_memory")
    profile_updated = False
    if learned_info:
        try:
            update_res = PatientProfileRepository.update_clinical_memory(
                patient_id=pat["patient_id"],
                new_allergies=learned_info.get("allergies"),
                new_chronic_conditions=learned_info.get("conditions")
            )
            if update_res:
                profile_updated = True
        except Exception as e:
            logger.warning("Appointment chat clinical memory persistence error: %s", e)

    ConsultationRepository.add_message(
        consultation_id=chat_id,
        sender_type="DOCTOR",
        sender_id=doc["doctor_id"],
        message_text=guidance["message"],
        disclaimer_note=guidance.get("disclaimer", "")
    )

    if guidance.get("red_flag_alert"):
        log_audit_event(
            "RED_FLAG_EMERGENCY_TRIGGERED", "APPOINTMENTS", appointment_id, "ALERT",
            {"query": message_text, "risk": "EMERGENCY", "doctor_id": doc["doctor_id"]}
        )

    return jsonify({
        "success": True,
        "ai_replied": True,
        "doctor_name": doc_display,
        "reply": guidance["message"],
        "disclaimer": guidance.get("disclaimer", ""),
        "risk_category": guidance.get("risk_category", "LOW"),
        "red_flag_alert": bool(guidance.get("red_flag_alert")),
        "follow_up_questions": guidance.get("follow_up_questions", []),
        "learned_memory": learned_info,
        "profile_memory_updated": profile_updated
    })
