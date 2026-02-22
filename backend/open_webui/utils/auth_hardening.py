"""Auth hardening utilities — Phase 4.3

Provides: OAuth config validation, password strength checking,
redirect URI sanitization, email format validation.
"""

import re
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth config validation
# ---------------------------------------------------------------------------

OAUTH_REQUIRED_FIELDS: dict[str, list[str]] = {
    "google": ["client_id", "client_secret"],
    "github": ["client_id", "client_secret"],
    "microsoft": ["client_id", "client_secret", "tenant_id"],
    "oidc": ["client_id", "client_secret", "provider_url"],
}


@dataclass
class OAuthConfigResult:
    valid: bool
    missing: list[str] = field(default_factory=list)


def validate_oauth_config(provider: str, config: dict | None) -> OAuthConfigResult:
    """Validate that an OAuth provider config has all required fields."""
    if config is None:
        required = OAUTH_REQUIRED_FIELDS.get(provider, OAUTH_REQUIRED_FIELDS["oidc"])
        return OAuthConfigResult(valid=False, missing=list(required))

    required = OAUTH_REQUIRED_FIELDS.get(provider, OAUTH_REQUIRED_FIELDS["oidc"])
    missing = [f for f in required if not config.get(f)]
    return OAuthConfigResult(valid=len(missing) == 0, missing=missing)


# ---------------------------------------------------------------------------
# Password strength
# ---------------------------------------------------------------------------

_COMMON_PASSWORDS = frozenset([
    "password", "password1", "password123", "123456", "12345678",
    "qwerty", "abc123", "letmein", "admin", "welcome",
    "monkey", "master", "dragon", "login", "princess",
    "football", "shadow", "sunshine", "trustno1", "iloveyou",
])


@dataclass
class PasswordStrength:
    score: int  # 0-5
    issues: list[str] = field(default_factory=list)


def check_password_strength(password: str) -> PasswordStrength:
    """Score a password 0-5 and list issues."""
    if not password:
        return PasswordStrength(score=0, issues=["Password is empty"])

    issues = []
    score = 0

    # Length — short passwords get a hard penalty
    if len(password) < 8:
        issues.append("Minimum length is 8 characters")
        score -= 2
    else:
        score += 1
        if len(password) >= 12:
            score += 1

    # Character classes
    if re.search(r"[A-Z]", password):
        score += 1
    else:
        issues.append("Must contain at least one uppercase letter")

    if re.search(r"[a-z]", password):
        score += 1
    else:
        issues.append("Must contain at least one lowercase letter")

    if re.search(r"\d", password):
        score += 1
    else:
        issues.append("Must contain at least one digit/number")

    if re.search(r"[^a-zA-Z0-9]", password):
        score += 1
    else:
        issues.append("Must contain at least one special character")

    # Common password check
    if password.lower() in _COMMON_PASSWORDS:
        issues.append("This is a commonly used password")
        score = max(0, score - 2)

    # Clamp to 0-5
    score = max(0, min(score, 5))

    return PasswordStrength(score=score, issues=issues)


# ---------------------------------------------------------------------------
# Redirect URI sanitization
# ---------------------------------------------------------------------------

def sanitize_redirect_uri(uri: str | None, allowed_origin: str) -> str:
    """Sanitize a redirect URI to prevent open redirect attacks.

    Returns the URI if safe, otherwise "/".
    """
    if not uri:
        return "/"

    # Block dangerous schemes
    lower = uri.lower().strip()
    if lower.startswith(("javascript:", "data:", "vbscript:")):
        return "/"

    # Block protocol-relative URLs
    if uri.startswith("//") or uri.startswith("\\"):
        return "/"

    # Relative paths are safe
    if uri.startswith("/") and not uri.startswith("//"):
        return uri

    # Absolute URL — must match allowed origin
    try:
        parsed = urlparse(uri)
        allowed = urlparse(allowed_origin)

        if parsed.scheme in ("http", "https") and parsed.netloc == allowed.netloc:
            return uri
    except Exception:
        pass

    return "/"


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
)


def validate_email_format(email: str | None) -> bool:
    """Validate email format. Requires a proper domain with TLD."""
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_RE.match(email))
