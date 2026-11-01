import re
from typing import Any, Dict, List, Optional
from fastapi import Header, HTTPException, Request, status
from backend.config import settings


async def verify_host_header(request: Request) -> None:
    """Blocks DNS rebinding attacks by validating the Host header."""
    host = request.headers.get("host", "").split(":")[0].lower()
    allowed_hosts = {"127.0.0.1", "localhost", "testserver"}
    if host not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Untrusted Host header '{host}'. Localhost access only."
        )


async def verify_session_token(
    request: Request,
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
) -> None:
    """Validates ephemeral session token on state-altering requests."""
    # In development or read requests, query param token is also accepted
    query_token = request.query_params.get("token")
    token = x_session_token or query_token
    
    if not token or token != settings.SESSION_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid session security token."
        )


def sanitize_telemetry_dict(data: Any) -> Any:
    """Recursively redacts PII such as usernames, serials, and GUIDs."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(term in k_lower for term in ("serialnumber", "uuid", "identifyingnumber", "macaddress", "username")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_telemetry_dict(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_telemetry_dict(item) for item in data]
    elif isinstance(data, str):
        # Redact user directory names
        redacted = re.sub(r'([A-Za-z]:\\Users\\)[^\\]+', r'\1[USER]', data, flags=re.IGNORECASE)
        # Redact standard GUIDs
        redacted = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '[GUID]', redacted)
        return redacted
    else:
        return data
