import re
import os
from werkzeug.utils import secure_filename
from backend.config import Config

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")

MAGIC_BYTES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"]
}

def validate_email(email: str) -> bool:
    if not email or len(email) > 255:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_phone(phone: str) -> bool:
    if not phone:
        return True # Optional in some fields
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(PHONE_REGEX.match(cleaned))

def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one numeric digit."
    return True, ""

def sanitize_input(text: str) -> str:
    """Strips executable script tags and basic malicious payloads."""
    if not text:
        return ""
    cleaned = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<.*?>", "", cleaned) # Remove remaining tags
    return cleaned.strip()

def validate_uploaded_file(file_obj) -> tuple[bool, str, str]:
    """
    Validates uploaded file for extension, filename safety, and file magic bytes.
    Returns: (is_valid, error_message, file_extension)
    """
    if not file_obj or not file_obj.filename:
        return False, "No file selected.", ""

    filename = secure_filename(file_obj.filename)
    if not filename:
        return False, "Invalid filename.", ""

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in Config.ALLOWED_EXTENSIONS:
        return False, f"File format '.{ext}' is not supported. Allowed formats: {', '.join(Config.ALLOWED_EXTENSIONS)}.", ""

    # Inspect magic bytes
    try:
        header = file_obj.read(16)
        file_obj.seek(0) # Reset position for subsequent reading
    except Exception as e:
        return False, f"Failed to read file header: {str(e)}", ""

    signatures = MAGIC_BYTES.get(ext, [])
    matches = any(header.startswith(sig) for sig in signatures)
    if not matches:
        return False, f"File content header does not match expected signature for .{ext}.", ""

    return True, "", ext
