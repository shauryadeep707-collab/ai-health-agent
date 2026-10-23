import time
from functools import wraps
from flask import request, jsonify

# In-memory rate limiting bucket
# key: ip_address or endpoint:ip -> list of timestamps
_RATE_LIMIT_STORE = {}

def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """Simple in-memory rate limiter for sensitive authentication or upload endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = request.remote_addr or "127.0.0.1"
            key = f"{f.__name__}:{ip}"
            now = time.time()

            timestamps = _RATE_LIMIT_STORE.get(key, [])
            # Filter timestamps within window
            timestamps = [t for t in timestamps if now - t < window_seconds]

            if len(timestamps) >= max_requests:
                return jsonify({
                    "success": False,
                    "error": f"Too many requests. Please wait {int(window_seconds - (now - timestamps[0]))} seconds before trying again.",
                    "code": "RATE_LIMITED"
                }), 429

            timestamps.append(now)
            _RATE_LIMIT_STORE[key] = timestamps
            return f(*args, **kwargs)
        return decorated
    return decorator
