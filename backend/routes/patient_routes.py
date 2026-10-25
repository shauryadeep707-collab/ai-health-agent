import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_file
from backend.security.auth import jwt_required, role_required
from backend.security.validation import validate_uploaded_file, sanitize_input
from backend.services.report_analysis_service import ReportAnalysisService
from backend.database.repositories import (
    PatientProfileRepository, MedicalReportRepository, UserRepository, DoctorProfileRepository
)
from backend.security.audit import log_audit_event
from backend.config import Config

patient_bp = Blueprint("patient", __name__, url_prefix="/api/patient")

@patient_bp.route("/profile", methods=["GET"])
@jwt_required
@role_required(["PATIENT"])
def get_patient_profile():
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404
    return jsonify({"success": True, "patient": pat})

@patient_bp.route("/profile", methods=["PUT"])
@jwt_required
@role_required(["PATIENT"])
def update_patient_profile():
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404

    data = request.get_json() or {}
    dob = data.get("date_of_birth", pat.get("date_of_birth"))
    gender = data.get("gender", pat.get("gender"))
    blood_group = data.get("blood_group", pat.get("blood_group"))
    emergency_contact = sanitize_input(data.get("emergency_contact", pat.get("emergency_contact") or ""))
    allergies = sanitize_input(data.get("allergies", pat.get("allergies") or ""))
    chronic = sanitize_input(data.get("chronic_conditions", pat.get("chronic_conditions") or ""))

    PatientProfileRepository.update(
        patient_id=pat["patient_id"],
        date_of_birth=dob,
        gender=gender,
        blood_group=blood_group,
        emergency_contact=emergency_contact,
        allergies=allergies,
        chronic_conditions=chronic
    )

    if data.get("full_name") or data.get("phone_number"):
        UserRepository.update_profile(
            user_id=user["user_id"],
            full_name=sanitize_input(data.get("full_name", user["full_name"])),
            phone_number=data.get("phone_number", user.get("phone_number"))
        )

    return jsonify({"success": True, "message": "Profile updated successfully."})

@patient_bp.route("/reports/upload", methods=["POST"])
@jwt_required
@role_required(["PATIENT"])
def upload_medical_report():
    """
    Upload and analyze medical report:
    1. Validates file type, size, and header magic bytes.
    2. Stores file securely.
    3. Extracts text via PDF parser / OCR.
    4. Identifies test names, values, reference ranges, and flags.
    5. Calls AI engine for plain English explanation.
    6. Stores in database and logs audit entry.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file_obj = request.files["file"]
    is_valid, err_msg, ext = validate_uploaded_file(file_obj)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    raw_user_type = request.form.get("test_type", "").strip()
    user_test_type = "" if ReportAnalysisService.is_generic_title(raw_user_type) else sanitize_input(raw_user_type)
    report_date = request.form.get("report_date", "").strip() or None

    # Secure storage
    safe_name = secure_filename(file_obj.filename)
    unique_stored_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
    save_dir = Config.UPLOAD_FOLDER
    save_dir.mkdir(parents=True, exist_ok=True)
    destination = save_dir / unique_stored_name

    file_obj.save(str(destination))
    file_size = destination.stat().st_size
    mime_type = file_obj.mimetype or f"application/{ext}"

    # Comprehensive multimodal AI & rule-engine extraction
    analysis_result = ReportAnalysisService.analyze_report_comprehensive(
        file_path=str(destination),
        file_type=mime_type,
        original_filename=safe_name,
        user_test_type=user_test_type,
        user_report_date=report_date
    )

    final_test_type = analysis_result.get("detected_title") or user_test_type or "Diagnostic Lab Report"
    final_report_date = analysis_result.get("test_date") or report_date
    parsed_values = analysis_result.get("parameters", [])
    ai_analysis = analysis_result.get("ai_analysis", {})
    extracted_text = analysis_result.get("extracted_text", "")

    # Save to Database
    report_id = MedicalReportRepository.create_report(
        patient_id=pat["patient_id"],
        original_filename=safe_name,
        stored_filename=unique_stored_name,
        file_path=str(destination),
        file_size_bytes=file_size,
        file_type=mime_type,
        test_type=final_test_type,
        report_date=final_report_date,
        ocr_raw_text=extracted_text
    )

    MedicalReportRepository.save_test_values(report_id, parsed_values)

    MedicalReportRepository.save_analysis(
        report_id=report_id,
        ai_provider=ai_analysis.get("ai_provider", "Clinical Engine"),
        summary_plain_en=ai_analysis.get("summary_plain_en", ""),
        clinical_notes=ai_analysis.get("clinical_notes", ""),
        abnormal_count=ai_analysis.get("abnormal_count", 0),
        urgent_flags=ai_analysis.get("urgent_flags", ""),
        risk_level=ai_analysis.get("risk_level", "LOW"),
        recommendations=ai_analysis.get("recommendations", "")
    )

    log_audit_event(
        "MEDICAL_REPORT_UPLOADED", "MEDICAL_REPORTS", report_id, "SUCCESS",
        {"filename": safe_name, "test_type": final_test_type, "risk_level": ai_analysis.get("risk_level", "LOW")}
    )

    return jsonify({
        "success": True,
        "message": "Report uploaded and analyzed successfully.",
        "report_id": report_id,
        "original_filename": safe_name,
        "test_type": final_test_type,
        "report_date": final_report_date,
        "test_values": parsed_values,
        "ai_analysis": ai_analysis,
        "file_url": f"/api/patient/reports/{report_id}/file",
        "extracted_text_preview": extracted_text[:300] if extracted_text else ""
    }), 201

@patient_bp.route("/reports/<report_id>/file", methods=["GET"])
@jwt_required
def view_report_file(report_id):
    """
    Serves the original uploaded medical report (Image or PDF) securely
    to the authorized patient or a verified doctor.
    """
    user = request.current_user
    report = MedicalReportRepository.find_by_id(report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404

    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if not pat or report["patient_id"] != pat["patient_id"]:
            return jsonify({"success": False, "error": "Access unauthorized."}), 403
    elif user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if not doc or doc.get("verification_status") != "VERIFIED":
            return jsonify({"success": False, "error": "Only verified doctors can view clinical reports."}), 403

    raw_path = report.get("file_path")
    file_path = Path(raw_path) if raw_path else None
    if not file_path or not file_path.exists():
        stored_name = report.get("stored_filename", "")
        file_path = Config.UPLOAD_FOLDER / stored_name

    if not file_path.exists():
        return jsonify({"success": False, "error": "Report file is not available on disk."}), 404

    mimetype = report.get("file_type") or "application/octet-stream"
    return send_file(
        str(file_path),
        mimetype=mimetype,
        as_attachment=False,
        download_name=report.get("original_filename")
    )

@patient_bp.route("/reports/<report_id>/confirm", methods=["POST"])
@jwt_required
@role_required(["PATIENT"])
def confirm_report_values(report_id):
    """
    Patient confirms or validates OCR extraction results.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    report = MedicalReportRepository.find_by_id(report_id)

    if not report or report["patient_id"] != pat["patient_id"]:
        return jsonify({"success": False, "error": "Report not found or access unauthorized."}), 404

    MedicalReportRepository.set_confirmed(report_id, 1)
    return jsonify({"success": True, "message": "Extracted report values confirmed by patient."})

@patient_bp.route("/reports", methods=["GET"])
@jwt_required
@role_required(["PATIENT"])
def list_patient_reports():
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    if not pat:
        return jsonify({"success": False, "error": "Patient profile not found."}), 404
    sort_by = request.args.get("sort", "date_desc").strip()
    reports = MedicalReportRepository.list_by_patient(pat["patient_id"], sort_by=sort_by)
    return jsonify({"success": True, "reports": reports, "sort_by": sort_by})

@patient_bp.route("/reports/<report_id>", methods=["GET"])
@jwt_required
def get_report_details(report_id):
    """Accessible by patient who owns it, or a doctor authorized via consultation."""
    user = request.current_user
    report = MedicalReportRepository.find_by_id(report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found."}), 404

    # Authorization Check
    if user["role"] == "PATIENT":
        pat = PatientProfileRepository.find_by_user_id(user["user_id"])
        if not pat or report["patient_id"] != pat["patient_id"]:
            return jsonify({"success": False, "error": "Access unauthorized."}), 403
    elif user["role"] == "DOCTOR":
        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if not doc or doc.get("verification_status") != "VERIFIED":
            return jsonify({"success": False, "error": "Only verified doctors can view clinical reports."}), 403

    analysis = MedicalReportRepository.get_analysis(report_id)
    test_values = MedicalReportRepository.get_test_values(report_id)

    return jsonify({
        "success": True,
        "report": report,
        "analysis": analysis,
        "test_values": test_values
    })

@patient_bp.route("/reports/compare", methods=["GET"])
@jwt_required
@role_required(["PATIENT"])
def compare_parameters_over_time():
    """
    Compares a laboratory parameter over time for trend visualization.
    """
    user = request.current_user
    pat = PatientProfileRepository.find_by_user_id(user["user_id"])
    param_name = request.args.get("parameter", "").strip()

    if not param_name:
        return jsonify({"success": False, "error": "Parameter name required for comparison (e.g. 'Total Cholesterol')."}), 400

    history = MedicalReportRepository.get_parameter_history(pat["patient_id"], param_name)
    return jsonify({
        "success": True,
        "parameter": param_name,
        "data_points": history
    })
