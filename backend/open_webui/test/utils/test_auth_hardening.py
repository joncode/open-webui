"""TDD tests for utils/auth_hardening.py — Phase 4.3

Auth hardening utilities: OAuth config validation, password strength
checking, redirect URI sanitization, email validation.
"""

import pytest

from open_webui.utils.auth_hardening import (
    validate_oauth_config,
    check_password_strength,
    sanitize_redirect_uri,
    validate_email_format,
    PasswordStrength,
    OAUTH_REQUIRED_FIELDS,
)


# ===========================================================================
class TestValidateOAuthConfig:
    """Verify OAuth provider configs have required fields."""

    def test_valid_google_config(self):
        config = {"client_id": "abc.apps.googleusercontent.com", "client_secret": "secret123"}
        result = validate_oauth_config("google", config)
        assert result.valid is True
        assert result.missing == []

    def test_google_missing_secret(self):
        config = {"client_id": "abc.apps.googleusercontent.com"}
        result = validate_oauth_config("google", config)
        assert result.valid is False
        assert "client_secret" in result.missing

    def test_google_empty_client_id(self):
        config = {"client_id": "", "client_secret": "secret123"}
        result = validate_oauth_config("google", config)
        assert result.valid is False
        assert "client_id" in result.missing

    def test_valid_github_config(self):
        config = {"client_id": "gh-id", "client_secret": "gh-secret"}
        result = validate_oauth_config("github", config)
        assert result.valid is True

    def test_github_missing_all(self):
        result = validate_oauth_config("github", {})
        assert result.valid is False
        assert "client_id" in result.missing
        assert "client_secret" in result.missing

    def test_valid_oidc_config(self):
        config = {
            "client_id": "oidc-id",
            "client_secret": "oidc-secret",
            "provider_url": "https://auth.example.com",
        }
        result = validate_oauth_config("oidc", config)
        assert result.valid is True

    def test_oidc_missing_provider_url(self):
        config = {"client_id": "oidc-id", "client_secret": "oidc-secret"}
        result = validate_oauth_config("oidc", config)
        assert result.valid is False
        assert "provider_url" in result.missing

    def test_unknown_provider_defaults_to_oidc(self):
        config = {
            "client_id": "id",
            "client_secret": "secret",
            "provider_url": "https://auth.example.com",
        }
        result = validate_oauth_config("custom_provider", config)
        assert result.valid is True

    def test_none_config_is_invalid(self):
        result = validate_oauth_config("google", None)
        assert result.valid is False

    def test_required_fields_constant_exists(self):
        assert "google" in OAUTH_REQUIRED_FIELDS
        assert "github" in OAUTH_REQUIRED_FIELDS
        assert "oidc" in OAUTH_REQUIRED_FIELDS


# ===========================================================================
class TestCheckPasswordStrength:
    """Password strength scoring."""

    def test_strong_password(self):
        result = check_password_strength("C0mpl3x!Pass#2024")
        assert result.score >= 4
        assert result.issues == []

    def test_empty_password(self):
        result = check_password_strength("")
        assert result.score == 0
        assert len(result.issues) > 0

    def test_too_short(self):
        result = check_password_strength("Ab1!")
        assert result.score < 3
        assert any("length" in i.lower() for i in result.issues)

    def test_no_uppercase(self):
        result = check_password_strength("lowercase1!only")
        assert any("uppercase" in i.lower() for i in result.issues)

    def test_no_lowercase(self):
        result = check_password_strength("UPPERCASE1!ONLY")
        assert any("lowercase" in i.lower() for i in result.issues)

    def test_no_digit(self):
        result = check_password_strength("NoDigits!Here")
        assert any("digit" in i.lower() or "number" in i.lower() for i in result.issues)

    def test_no_special_char(self):
        result = check_password_strength("NoSpecial1Here")
        assert any("special" in i.lower() for i in result.issues)

    def test_common_password_flagged(self):
        result = check_password_strength("password123")
        assert any("common" in i.lower() for i in result.issues)

    def test_score_range(self):
        result = check_password_strength("x")
        assert 0 <= result.score <= 5

        result = check_password_strength("V3ry$tr0ng!P@ss")
        assert 0 <= result.score <= 5

    def test_returns_password_strength_type(self):
        result = check_password_strength("test")
        assert isinstance(result, PasswordStrength)
        assert hasattr(result, "score")
        assert hasattr(result, "issues")


# ===========================================================================
class TestSanitizeRedirectUri:
    """Prevent open redirect attacks in OAuth callbacks."""

    def test_valid_relative_path(self):
        assert sanitize_redirect_uri("/dashboard", "https://app.example.com") == "/dashboard"

    def test_valid_same_origin(self):
        result = sanitize_redirect_uri(
            "https://app.example.com/callback", "https://app.example.com"
        )
        assert result == "https://app.example.com/callback"

    def test_rejects_different_origin(self):
        result = sanitize_redirect_uri(
            "https://evil.com/steal", "https://app.example.com"
        )
        assert result == "/"

    def test_rejects_javascript_uri(self):
        result = sanitize_redirect_uri("javascript:alert(1)", "https://app.example.com")
        assert result == "/"

    def test_rejects_data_uri(self):
        result = sanitize_redirect_uri("data:text/html,<script>", "https://app.example.com")
        assert result == "/"

    def test_empty_uri_returns_root(self):
        assert sanitize_redirect_uri("", "https://app.example.com") == "/"

    def test_none_uri_returns_root(self):
        assert sanitize_redirect_uri(None, "https://app.example.com") == "/"

    def test_protocol_relative_rejected(self):
        result = sanitize_redirect_uri("//evil.com/steal", "https://app.example.com")
        assert result == "/"

    def test_backslash_trick_rejected(self):
        result = sanitize_redirect_uri("\\\\evil.com", "https://app.example.com")
        assert result == "/"

    def test_subdomain_mismatch_rejected(self):
        result = sanitize_redirect_uri(
            "https://evil.example.com/steal", "https://app.example.com"
        )
        assert result == "/"


# ===========================================================================
class TestValidateEmailFormat:
    """Email format validation."""

    def test_valid_email(self):
        assert validate_email_format("user@example.com") is True

    def test_valid_email_with_plus(self):
        assert validate_email_format("user+tag@example.com") is True

    def test_valid_email_subdomain(self):
        assert validate_email_format("user@mail.example.com") is True

    def test_invalid_no_at(self):
        assert validate_email_format("userexample.com") is False

    def test_invalid_no_domain(self):
        assert validate_email_format("user@") is False

    def test_invalid_no_local(self):
        assert validate_email_format("@example.com") is False

    def test_invalid_spaces(self):
        assert validate_email_format("user @example.com") is False

    def test_empty_string(self):
        assert validate_email_format("") is False

    def test_none_input(self):
        assert validate_email_format(None) is False

    def test_multiple_at_signs(self):
        assert validate_email_format("user@@example.com") is False

    def test_no_tld(self):
        assert validate_email_format("user@localhost") is False
