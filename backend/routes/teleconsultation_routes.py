from flask import Blueprint, request, jsonify
from backend.teleconsultation.room_service import TeleconsultationService

teleconsult_bp = Blueprint("teleconsultation", __name__, url_prefix="/api/teleconsultation")

@teleconsult_bp.route("/room/create", methods=["POST"])
def create_or_join_room():
    data = request.get_json() or {}
    apt_id = data.get("appointment_id") or data.get("room_id") or ""
    doctor_name = data.get("doctor_name", "")
    patient_name = data.get("patient_name", "")

    room = TeleconsultationService.get_or_create_room(apt_id, doctor_name, patient_name)
    return jsonify({
        "success": True,
        "room": room,
        "webrtc_url": f"/teleconsultation/consultation-room.html?room={room['appointment_id']}"
    })

@teleconsult_bp.route("/room/<room_id>/end", methods=["POST"])
def end_room(room_id):
    data = request.get_json() or {}
    summary = data.get("notes", "")
    ended = TeleconsultationService.end_room_session(room_id, summary)
    return jsonify({
        "success": True,
        "room": ended
    })
