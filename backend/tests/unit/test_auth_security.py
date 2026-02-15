"""
Unit tests for authentication and security module.
Tests JWT token validation, user extraction, and Keycloak integration.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from jose import jwt

from app.core.security import (
    get_keycloak_public_keys,
    decode_token,
    get_current_user,
    get_current_active_user,
)
from app.core.config import settings

# ============================================================================
# Test Data
# ============================================================================

MOCK_PUBLIC_KEYS = {
    "keys": [
        {
            "kid": "test-key-id",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "mock-modulus",
            "e": "AQAB",
        }
    ]
}

VALID_TOKEN_PAYLOAD = {
    "sub": "user-uuid-123",
    "email": "user@example.com",
    "preferred_username": "testuser",
    "name": "Test User",
    "given_name": "Test",
    "family_name": "User",
    "realm_access": {"roles": ["user"]},
    "exp": 9999999999,  # Far future expiry
}


# ============================================================================
# Test: get_keycloak_public_keys
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_keycloak_public_keys_success():
    """Test successful retrieval of Keycloak public keys."""
    with patch("httpx.AsyncClient") as mock_client_class:
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = MOCK_PUBLIC_KEYS
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Call function
        result = await get_keycloak_public_keys()

        # Assertions
        assert result == MOCK_PUBLIC_KEYS
        assert "keys" in result
        assert len(result["keys"]) == 1


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_keycloak_public_keys_failure():
    """Test handling of Keycloak public keys retrieval failure."""
    with patch("httpx.AsyncClient") as mock_client_class:
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_client_class.return_value = mock_client

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_keycloak_public_keys()

        assert exc_info.value.status_code == 503
        assert "Unable to fetch Keycloak public keys" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_keycloak_public_keys_caching():
    """Test that public keys are cached after first retrieval."""
    # Reset cache
    from app.core import security
    security._keycloak_public_keys = None

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = Mock()
        mock_response.json.return_value = MOCK_PUBLIC_KEYS
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # First call - should fetch from API
        result1 = await get_keycloak_public_keys()

        # Second call - should use cache
        result2 = await get_keycloak_public_keys()

        # Assertions
        assert result1 == result2
        # get should only be called once due to caching
        assert mock_client.__aenter__.return_value.get.call_count == 1


# ============================================================================
# Test: decode_token
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
def test_decode_token_success():
    """Test successful JWT token decoding."""
    # Create a mock token with proper header
    with patch("jose.jwt.get_unverified_header") as mock_header, \
            patch("jose.jwt.decode") as mock_decode:
        mock_header.return_value = {"kid": "test-key-id"}
        mock_decode.return_value = VALID_TOKEN_PAYLOAD

        result = decode_token("mock.jwt.token", MOCK_PUBLIC_KEYS)

        # Assertions
        assert result["sub"] == "user-uuid-123"
        assert result["email"] == "user@example.com"
        assert mock_decode.called


@pytest.mark.unit
@pytest.mark.auth
def test_decode_token_invalid_key_id():
    """Test token decoding with invalid key ID."""
    with patch("jose.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {"kid": "wrong-key-id"}

        with pytest.raises(HTTPException) as exc_info:
            decode_token("mock.jwt.token", MOCK_PUBLIC_KEYS)

        assert exc_info.value.status_code == 401
        assert "Unable to find appropriate key" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.auth
def test_decode_token_expired():
    """Test token decoding with expired token."""
    from jose import JWTError

    with patch("jose.jwt.get_unverified_header") as mock_header, \
            patch("jose.jwt.decode") as mock_decode:
        mock_header.return_value = {"kid": "test-key-id"}
        mock_decode.side_effect = JWTError("Token has expired")

        with pytest.raises(HTTPException) as exc_info:
            decode_token("mock.jwt.token", MOCK_PUBLIC_KEYS)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


# ============================================================================
# Test: get_current_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_current_user_success(mock_user_payload):
    """Test successful user extraction from JWT token."""
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid.jwt.token"
    )

    with patch("app.core.security.get_keycloak_public_keys") as mock_keys, \
            patch("app.core.security.decode_token") as mock_decode:
        mock_keys.return_value = MOCK_PUBLIC_KEYS
        mock_decode.return_value = mock_user_payload

        result = await get_current_user(credentials)

        # Assertions
        assert result["sub"] == mock_user_payload["sub"]
        assert result["email"] == mock_user_payload["email"]
        assert result["preferred_username"] == mock_user_payload["preferred_username"]
        assert "roles" in result


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test user extraction with invalid token."""
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.jwt.token"
    )

    with patch("app.core.security.get_keycloak_public_keys") as mock_keys, \
            patch("app.core.security.decode_token") as mock_decode:
        mock_keys.return_value = MOCK_PUBLIC_KEYS
        mock_decode.side_effect = HTTPException(status_code=401, detail="Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401


# ============================================================================
# Test: get_current_active_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_current_active_user(mock_user_payload):
    """Test active user validation."""
    result = await get_current_active_user(mock_user_payload)

    # Should return the same payload (no additional checks in current implementation)
    assert result == mock_user_payload


# ============================================================================
# Test: Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
def test_decode_token_missing_kid():
    """Test token decoding when kid is missing from header."""
    with patch("jose.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {}  # Missing 'kid'

        with pytest.raises(HTTPException) as exc_info:
            decode_token("mock.jwt.token", MOCK_PUBLIC_KEYS)

        assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_get_current_user_missing_fields(mock_user_payload):
    """Test user extraction with incomplete token payload."""
    from fastapi.security import HTTPAuthorizationCredentials

    incomplete_payload = {
        "sub": "user-123",
        # Missing other fields
    }

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid.jwt.token"
    )

    with patch("app.core.security.get_keycloak_public_keys") as mock_keys, \
            patch("app.core.security.decode_token") as mock_decode:
        mock_keys.return_value = MOCK_PUBLIC_KEYS
        mock_decode.return_value = incomplete_payload

        result = await get_current_user(credentials)

        # Should handle missing fields gracefully
        assert result["sub"] == "user-123"
        assert result["email"] is None
        assert result["roles"] == []  # Default empty list
