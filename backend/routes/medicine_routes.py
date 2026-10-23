from flask import Blueprint, request, jsonify
from backend.services.medicine_service import MedicineService

medicine_bp = Blueprint("medicine", __name__, url_prefix="/api/medicines")

@medicine_bp.route("/search", methods=["GET"])
def search_medicines():
    query = request.args.get("query", "").strip()
    limit = int(request.args.get("limit", 20))
    results = MedicineService.search(query, limit)
    return jsonify({
        "success": True,
        "medicines": results,
        "count": len(results),
        "disclaimer": "Medicine details are sourced from authoritative compendia (WHO, FDA, CDSCO). Always consult a licensed physician or registered pharmacist before taking or changing medication."
    })

@medicine_bp.route("/<medicine_id>", methods=["GET"])
def get_medicine(medicine_id):
    med = MedicineService.get_details(medicine_id)
    if not med:
        return jsonify({"success": False, "error": "Medicine record not found."}), 404
    return jsonify({"success": True, "medicine": med})

@medicine_bp.route("/check-interactions", methods=["POST"])
def check_interactions():
    data = request.get_json() or {}
    medicine_ids = data.get("medicine_ids", [])
    result = MedicineService.check_interactions(medicine_ids)
    return jsonify({"success": True, **result})
