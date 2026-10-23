from flask import Blueprint, request, jsonify
from backend.services.product_service import ProductService

product_bp = Blueprint("product", __name__, url_prefix="/api/products")

@product_bp.route("/search", methods=["GET"])
def search_products():
    query = request.args.get("query", "").strip()
    category = request.args.get("category", "").strip()
    limit = int(request.args.get("limit", 20))
    result = ProductService.search(query=query, category=category, limit=limit)
    return jsonify({"success": True, **result})

@product_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = ProductService.get_categories()
    return jsonify({"success": True, "categories": categories})

@product_bp.route("/<product_id>", methods=["GET"])
def get_product(product_id):
    product = ProductService.get_details(product_id)
    if not product:
        return jsonify({"success": False, "error": "Product not found."}), 404
    return jsonify({"success": True, "product": product})
