"""Azure Entra ID JWT token validation."""

import logging
from typing import Any

import httpx
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

# Microsoft Entra ID OIDC endpoints
AUTHORITY = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"
JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"
ISSUER = f"https://sts.windows.net/{settings.AZURE_TENANT_ID}/"
AUDIENCE = f"api://{settings.AZURE_CLIENT_ID}"

_jwks_cache: dict[str, Any] | None = None


async def _get_signing_keys() -> dict[str, Any]:
    """Fetch and cache JWKS from Azure Entra ID."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def _find_rsa_key(token: str, jwks: dict[str, Any]) -> dict[str, str] | None:
    """Find the RSA key matching the token's kid header."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        return None

    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key.get("use", "sig"),
                "n": key["n"],
                "e": key["e"],
            }
    return None


async def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT token from Azure Entra ID.

    Returns the decoded claims if valid. Raises ValueError on failure.
    """
    jwks = await _get_signing_keys()
    rsa_key = _find_rsa_key(token, jwks)

    if rsa_key is None:
        raise ValueError("Unable to find matching signing key")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        raise ValueError(f"Token validation failed: {e}") from e

    return payload


def extract_user_info(claims: dict[str, Any]) -> dict[str, Any]:
    """Extract user information from validated JWT claims."""
    roles = claims.get("roles", [])
    return {
        "user_id": claims.get("oid", claims.get("sub", "")),
        "name": claims.get("name", ""),
        "email": claims.get("preferred_username", claims.get("email", "")),
        "roles": roles,
        "tenant_id": claims.get("tid", ""),
    }
