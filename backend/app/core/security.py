from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from typing import Optional, Dict
from app.core.config import settings

security = HTTPBearer()

# Cache for Keycloak public keys
_keycloak_public_keys: Optional[Dict] = None


async def get_keycloak_public_keys() -> Dict:
    """
    Fetch Keycloak public keys for JWT verification.
    Caches keys to avoid repeated requests.
    """
    global _keycloak_public_keys

    if _keycloak_public_keys is None:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(settings.KEYCLOAK_CERTS_URL, timeout=10.0)
                response.raise_for_status()
                _keycloak_public_keys = response.json()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Unable to fetch Keycloak public keys: {str(e)}"
                )

    return _keycloak_public_keys


def decode_token(token: str, public_keys: Dict) -> Dict:
    """
    Decode and validate JWT token using Keycloak public keys.
    """
    try:
        # Get unverified header to find correct key
        unverified_header = jwt.get_unverified_header(token)
        key_id = unverified_header.get("kid")

        # Find the matching public key
        rsa_key = None
        for key in public_keys.get("keys", []):
            if key.get("kid") == key_id:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )

        # Decode and validate token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=[settings.ALGORITHM],
            audience=settings.KEYCLOAK_CLIENT_ID,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True
            }
        )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Dependency to get current authenticated user from JWT token.
    Validates token and returns user information.
    """
    token = credentials.credentials

    # Get Keycloak public keys
    public_keys = await get_keycloak_public_keys()

    # Decode and validate token
    payload = decode_token(token, public_keys)

    # Extract user information
    user_info = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "preferred_username": payload.get("preferred_username"),
        "name": payload.get("name"),
        "given_name": payload.get("given_name"),
        "family_name": payload.get("family_name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
    }

    return user_info


async def get_current_active_user(
        current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Dependency to ensure user is active.
    Can be extended with additional checks.
    """
    # Add any additional user validation logic here
    return current_user
