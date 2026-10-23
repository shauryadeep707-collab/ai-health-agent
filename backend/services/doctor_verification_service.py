import re
import difflib
from datetime import datetime, timezone
from backend.database.repositories import DoctorProfileRepository, DoctorVerificationRepository
from backend.security.audit import log_audit_event

def normalize_name(name: str) -> str:
    """Normalizes doctor name by stripping honorifics, titles, and whitespace."""
    if not name:
        return ""
    cleaned = re.sub(r"^(dr\.?|doctor|prof\.?)\s+", "", name.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", "", cleaned) # Remove punctuation
    return " ".join(cleaned.lower().split())

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculates similarity score (0.0 to 100.0) using token comparison and sequence matching."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    if not norm1 or not norm2:
        return 0.0

    if norm1 == norm2:
        return 100.0

    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    # Token overlap (Jaccard)
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    # If completely disjoint words
    if not intersection:
        # Check character sequence matcher only as small weight
        char_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return round(char_ratio * 40.0, 2) # Cap disjoint words at 40%

    # If all tokens of one are in the other (e.g. "Priya Sharma" in "Priya K Sharma")
    if intersection == tokens1 or intersection == tokens2:
        return 90.0

    # Weighted blend of token Jaccard and character sequence similarity
    token_score = (len(intersection) / len(union)) * 100.0
    seq_score = difflib.SequenceMatcher(None, norm1, norm2).ratio() * 100.0
    combined = (token_score * 0.6) + (seq_score * 0.4)
    return round(combined, 2)

def normalize_reg_no(reg_no: str) -> str:
    """Normalizes registration number by stripping spaces, hyphens, and casing."""
    if not reg_no:
        return ""
    return re.sub(r"[\s\-\/]", "", reg_no.upper().strip())

class DoctorVerificationService:
    """
    Evaluates doctor verification credentials retrieved via DigiLocker / API Setu.
    Implements the 4-tier state machine:
    - VERIFIED: Perfect or near-perfect match on Registration No, Name (>= 85%), and active issuer status.
    - REVIEW_REQUIRED: Inconclusive result, slight name difference (55% - 84%), or council jurisdiction manual cross-check.
    - REJECTED: Decisive negative evidence (revoked license, registration number invalid, or complete mismatch).
    - PENDING: Incomplete flow.
    """

    @staticmethod
    def process_digilocker_document(doctor_id: str, doc_payload: dict, verification_id: str = None) -> dict:
        doctor = DoctorProfileRepository.find_by_id(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor profile not found for ID {doctor_id}")

        cert = doc_payload.get("certificate_data", {})
        extracted_name = cert.get("doctor_name", "")
        extracted_reg_no = cert.get("registration_number", "")
        extracted_council = cert.get("medical_council", "")
        extracted_qual = cert.get("medical_qualification", "")
        issuer_id = doc_payload.get("issuer_id", "in.gov.nmc")
        doc_uri = doc_payload.get("doc_uri", "")
        txn_id = doc_payload.get("digilocker_txn_id", "")

        # 1. Name Match Score
        name_score = calculate_name_similarity(doctor["full_name"], extracted_name)

        # 2. Registration Number Match
        reg_match = 1 if normalize_reg_no(doctor["registration_number"]) == normalize_reg_no(extracted_reg_no) else 0

        # 3. State Machine Assessment
        new_status = "PENDING"
        rejection_reason = None
        review_notes = []

        if reg_match == 1:
            if name_score >= 85.0:
                new_status = "VERIFIED"
                review_notes.append("DigiLocker credential verified. Registration number and doctor identity confirmed.")
            elif name_score >= 40.0:
                new_status = "REVIEW_REQUIRED"
                review_notes.append(
                    f"Name similarity ({name_score}%) requires administrative confirmation. Registered: '{doctor['full_name']}' vs DigiLocker: '{extracted_name}'."
                )
            else:
                new_status = "REJECTED"
                rejection_reason = f"Registration number matches an existing entry, but the doctor name '{extracted_name}' does not match the registered profile '{doctor['full_name']}'."
        else:
            # Registration number mismatch
            new_status = "REJECTED"
            rejection_reason = f"Provided registration number '{doctor['registration_number']}' does not match the DigiLocker certificate registration number '{extracted_reg_no}'."

        # Check council consistency
        if extracted_council and doctor["registration_council"]:
            c_score = difflib.SequenceMatcher(None, doctor["registration_council"].lower(), extracted_council.lower()).ratio()
            if c_score < 0.6 and new_status == "VERIFIED":
                new_status = "REVIEW_REQUIRED"
                review_notes.append(f"Registration Council mismatch: Registered as '{doctor['registration_council']}', but certificate issued by '{extracted_council}'.")

        # Save verification record
        notes_str = " | ".join(review_notes)
        verified_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if new_status == "VERIFIED" else None

        if verification_id:
            DoctorVerificationRepository.update(
                verification_id=verification_id,
                status=new_status,
                digilocker_txn_id=txn_id,
                doc_uri=doc_uri,
                issuer_id=issuer_id,
                extracted_doctor_name=extracted_name,
                extracted_reg_no=extracted_reg_no,
                extracted_council=extracted_council,
                extracted_qual=extracted_qual,
                name_match_score=name_score,
                reg_no_match=reg_match,
                rejection_reason=rejection_reason,
                review_notes=notes_str,
                verified_by="DigiLocker Automated Gateway"
            )
        else:
            # Create fresh record
            fresh_id = DoctorVerificationRepository.create(
                doctor_id=doctor_id,
                provider_source="DIGILOCKER",
                doc_type="DOCREG",
                status=new_status
            )
            DoctorVerificationRepository.update(
                verification_id=fresh_id,
                status=new_status,
                digilocker_txn_id=txn_id,
                doc_uri=doc_uri,
                issuer_id=issuer_id,
                extracted_doctor_name=extracted_name,
                extracted_reg_no=extracted_reg_no,
                extracted_council=extracted_council,
                extracted_qual=extracted_qual,
                name_match_score=name_score,
                reg_no_match=reg_match,
                rejection_reason=rejection_reason,
                review_notes=notes_str,
                verified_by="DigiLocker Automated Gateway"
            )

        # Update doctor profile table
        DoctorProfileRepository.update_verification_status(doctor_id, new_status, verified_at)

        # Audit log
        log_audit_event(
            event_type="DIGILOCKER_DOCTOR_VERIFICATION",
            target_resource="DOCTOR_PROFILES",
            resource_id=doctor_id,
            event_status="SUCCESS" if new_status == "VERIFIED" else ("WARNING" if new_status == "REVIEW_REQUIRED" else "ALERT"),
            details={
                "status": new_status,
                "name_score": name_score,
                "reg_no_match": reg_match,
                "rejection_reason": rejection_reason,
                "notes": notes_str
            },
            user_id=doctor["user_id"]
        )

        return {
            "doctor_id": doctor_id,
            "status": new_status,
            "name_match_score": name_score,
            "reg_no_match": bool(reg_match),
            "extracted_doctor_name": extracted_name,
            "extracted_reg_no": extracted_reg_no,
            "extracted_council": extracted_council,
            "rejection_reason": rejection_reason,
            "review_notes": notes_str,
            "verified_at": verified_at
        }
