from flask import Blueprint, request, jsonify
from backend.services.medicine_service import MedicineService
from backend.database.repositories import MedicineRepository

medicine_bp = Blueprint("medicine", __name__, url_prefix="/api/medicines")

@medicine_bp.route("/search", methods=["GET"])
def search_medicines():
    query = request.args.get("query", "").strip() or request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 20))
    results = MedicineService.search(query, limit)
    return jsonify({
        "success": True,
        "medicines": results,
        "count": len(results),
        "disclaimer": "Medicine details are sourced from authoritative compendia (WHO, FDA, CDSCO) and verified by AI Clinical Pharmacology Engine."
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
    names = data.get("medicine_names") or data.get("names") or []
    ids = data.get("medicine_ids") or []

    # If names provided or if user passed text list
    if names and len(names) >= 2:
        result = MedicineService.check_interactions_ai(names)
        return jsonify({"success": True, **result})

    # If IDs passed, map IDs to names or check pairwise
    if ids and len(ids) >= 2:
        med_names = []
        for mid in ids:
            rec = MedicineRepository.find_by_id(mid)
            if rec and rec.get("brand_name"):
                med_names.append(rec["brand_name"])
            else:
                med_names.append(str(mid).replace("med-", "").title())
        
        if len(med_names) >= 2:
            result = MedicineService.check_interactions_ai(med_names)
            return jsonify({"success": True, **result})

        result = MedicineService.check_interactions(ids)
        return jsonify({"success": True, **result})

    return jsonify({
        "success": False,
        "has_interactions": False,
        "error": "Please provide at least two medications to screen for interactions."
    }), 400

@medicine_bp.route("/ai-check-interactions", methods=["POST"])
def ai_check_interactions():
    data = request.get_json() or {}
    names = data.get("medicine_names") or data.get("names") or data.get("medicines") or []
    if isinstance(names, str):
        names = [n.strip() for n in names.split(",") if n.strip()]
    result = MedicineService.check_interactions_ai(names)
    return jsonify({"success": True, **result})
