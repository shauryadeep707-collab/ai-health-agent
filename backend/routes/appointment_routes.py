from flask import Blueprint, request, jsonify
from backend.security.auth import jwt_required, role_required
from backend.security.validation import sanitize_input
from backend.database.repositories import (
    DoctorProfileRepository, AppointmentRepository, PatientProfileRepository
)
from backend.security.audit import log_audit_event

appointment_bp = Blueprint("appointment", __name__, url_prefix="/api/appointments")

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

    apt_id = AppointmentRepository.create(
        patient_id=pat["patient_id"],
        doctor_id=doctor_id,
        appointment_date=date_str,
        slot_time=slot_time,
        reason_for_visit=reason
    )

    log_audit_event(
        "APPOINTMENT_BOOKED", "APPOINTMENTS", apt_id, "SUCCESS",
        {"doctor_id": doctor_id, "patient_id": pat["patient_id"], "date": date_str, "time": slot_time}
    )

    return jsonify({
        "success": True,
        "message": f"Appointment booked successfully with Dr. {doctor['full_name']} for {date_str} at {slot_time}.",
        "appointment_id": apt_id,
        "status": "BOOKED"
    }), 201

@appointment_bp.route("/my", methods=["GET"])
@jwt_required
def get_my_appointments():
    user = request.current_user
    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        apts = AppointmentRepository.list_by_patient(pat["patient_id"])
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
