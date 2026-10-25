import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify
from backend.config import Config
from backend.database.repositories import UserRepository, DoctorProfileRepository, PatientProfileRepository

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def check_password(password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def generate_jwt_token(user: dict) -> str:
    """Generates a secure JSON Web Token with user claims and expiration."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["user_id"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user["full_name"],
        "iat": now,
        "exp": now + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")

def decode_jwt_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])

def get_current_user_from_request():
    """Extracts and verifies JWT token from Authorization header or cookie."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif "auth_token" in request.cookies:
        token = request.cookies.get("auth_token")
    elif request.args.get("token"):
        token = request.args.get("token").strip()

    if not token:
        return None

    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        user = UserRepository.find_by_id(user_id)
        if not user or not user.get("is_active"):
            return None

        # Attach role-specific profile ID
        if user["role"] == "DOCTOR":
            doc = DoctorProfileRepository.find_by_user_id(user_id)
            if doc:
                user["doctor_id"] = doc["doctor_id"]
                user["verification_status"] = doc.get("verification_status", "PENDING")
        elif user["role"] == "PATIENT":
            pat = PatientProfileRepository.find_by_user_id(user_id)
            if pat:
                user["patient_id"] = pat["patient_id"]

        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def jwt_required(f):
    """Decorator ensuring that request has a valid authenticated JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user_from_request()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in.",
                "code": "AUTH_REQUIRED"
            }), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    """Decorator ensuring that user possesses one of the allowed roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "current_user", None) or get_current_user_from_request()
            if not user:
                return jsonify({
                    "success": False,
                    "error": "Authentication required.",
                    "code": "AUTH_REQUIRED"
                }), 401
            request.current_user = user
            if user.get("role") not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": f"Access denied. Requires one of roles: {', '.join(allowed_roles)}.",
                    "code": "FORBIDDEN_ROLE"
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def verified_doctor_required(f):
    """Decorator ensuring the user is a doctor whose DigiLocker verification is VERIFIED."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(request, "current_user", None) or get_current_user_from_request()
        if not user:
            return jsonify({"success": False, "error": "Authentication required.", "code": "AUTH_REQUIRED"}), 401
        request.current_user = user

        if user.get("role") != "DOCTOR":
            return jsonify({"success": False, "error": "Only medical practitioners can access this resource.", "code": "NOT_A_DOCTOR"}), 403

        doc = DoctorProfileRepository.find_by_user_id(user["user_id"])
        if not doc or doc.get("verification_status") != "VERIFIED":
            return jsonify({
                "success": False,
                "error": "Access reserved for verified doctors. Please complete your DigiLocker credential verification.",
                "verification_status": doc.get("verification_status") if doc else "UNKNOWN",
                "code": "VERIFICATION_REQUIRED"
            }), 403
        return f(*args, **kwargs)
    return decorated
