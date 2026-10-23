import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from backend.config import Config
from backend.routes.auth_routes import auth_bp
from backend.routes.doctor_routes import doctor_bp
from backend.routes.patient_routes import patient_bp
from backend.routes.ai_routes import ai_bp
from backend.routes.appointment_routes import appointment_bp
from backend.routes.medicine_routes import medicine_bp
from backend.routes.product_routes import product_bp

def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(medicine_bp)
    app.register_blueprint(product_bp)

    # Ensure upload directory exists
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    # Security Headers Middleware
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Enable CORS for development
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response

    # Frontend Route Servicing
    @app.route("/", methods=["GET"])
    def serve_index():
        return send_from_directory(str(frontend_dir), "index.html")

    @app.route("/<path:filename>", methods=["GET"])
    def serve_frontend_files(filename):
        target = frontend_dir / filename
        if target.exists() and target.is_file():
            return send_from_directory(str(frontend_dir), filename)
        # Try serving .html if extension omitted
        html_target = frontend_dir / f"{filename}.html"
        if html_target.exists():
            return send_from_directory(str(frontend_dir), f"{filename}.html")
        return jsonify({"error": "Resource not found", "path": filename}), 404

    # Standard JSON Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "error": "Bad request", "details": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"success": False, "error": "File size exceeds 10MB limit."}), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"================================================================")
    print(f" AI Health Agent Server starting on http://{Config.HOST}:{Config.PORT}")
    print(f" Database Mode: {Config.DB_TYPE.upper()}")
    print(f" AI Provider: {Config.AI_PROVIDER.upper()}")
    print(f" DigiLocker Mode: {Config.DIGILOCKER_ENV.upper()}")
    print(f"================================================================")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
