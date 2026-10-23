from flask import request
from backend.database.repositories import AuditRepository

def log_audit_event(event_type: str, target_resource: str, resource_id: str = None, event_status: str = "SUCCESS", details: dict = None, user_id: str = None):
    """Utility to record an audit log entry from current request context."""
    actor_id = user_id
    if not actor_id:
        current_user = getattr(request, "current_user", None)
        if current_user:
            actor_id = current_user.get("user_id")

    ip_address = request.remote_addr if request else "127.0.0.1"

    AuditRepository.log(
        actor_user_id=actor_id,
        event_type=event_type,
        target_resource=target_resource,
        resource_id=resource_id,
        event_status=event_status,
        details_json=details or {},
        ip_address=ip_address
    )
