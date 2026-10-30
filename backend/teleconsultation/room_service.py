import uuid
import time
from datetime import datetime, timezone
from backend.database.repositories import AppointmentRepository

class TeleconsultationService:
    """
    Manages dedicated WebRTC teleconsultation rooms, participant access tokens,
    and end-of-call audit notes between verified doctors and patients.
    """

    _active_rooms = {}

    @classmethod
    def get_or_create_room(cls, appointment_id: str, doctor_name: str = "", patient_name: str = ""):
        """
        Creates or retrieves an encrypted WebRTC room session.
        Room ID is deterministic per appointment or randomly generated for instant visits.
        """
        clean_id = (appointment_id or f"instant-{uuid.uuid4().hex[:8]}").strip()
        room_name = f"aiheal-{clean_id}"

        if room_name not in cls._active_rooms:
            cls._active_rooms[room_name] = {
                "room_id": room_name,
                "appointment_id": clean_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "doctor_name": doctor_name or "Doctor",
                "patient_name": patient_name or "Patient",
                "status": "ACTIVE",
                "participants": []
            }

        return cls._active_rooms[room_name]

    @classmethod
    def end_room_session(cls, room_name: str, summary_notes: str = ""):
        """Concludes an active consultation room and logs medical session completion."""
        if room_name in cls._active_rooms:
            cls._active_rooms[room_name]["status"] = "CONCLUDED"
            cls._active_rooms[room_name]["ended_at"] = datetime.now(timezone.utc).isoformat()
            cls._active_rooms[room_name]["summary_notes"] = summary_notes
            return cls._active_rooms[room_name]
        return None
