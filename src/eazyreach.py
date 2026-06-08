"""EazyReach integration — DEPRECATED (kept for reference).

Per the assignment update, EazyReach is no longer required. Prospeo now
returns email addresses directly, eliminating the need for a separate email
resolution stage.

This module is retained for reference only. It will not be imported or used
by the pipeline.

Authentication and wallet balance checks against the Superflow B2B API are
implemented and tested, but the enrichment endpoint was never documented.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://api.superflow.run/b2b/createAuthToken/"
BALANCE_URL = "https://api.superflow.run/b2b/getGreenBalance"

# Cached auth token to avoid re-authentication on every call
_auth_token = None
_auth_expiry = 0


def get_auth_token(force_refresh: bool = False) -> str | None:
    """Authenticate with EazyReach and return an auth token.

    NOTE: This module is deprecated. Prospeo resolves emails directly.
    """
    global _auth_token, _auth_expiry

    if not force_refresh and _auth_token and time.time() < _auth_expiry:
        return _auth_token

    client_id = os.getenv("EAZYREACH_CLIENT_ID")
    client_secret = os.getenv("EAZYREACH_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    payload = {
        "clientId": client_id,
        "clientSecret": client_secret,
    }

    try:
        response = requests.post(AUTH_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        response.raise_for_status()
        data = response.json()
        token = data.get("authToken")
        if token:
            _auth_token = token
            _auth_expiry = time.time() + 21600
            return token
        return None
    except requests.RequestException:
        return None


def get_wallet_balance() -> int | None:
    """Check the EazyReach wallet (green) balance.

    NOTE: This module is deprecated. Prospeo resolves emails directly.
    """
    token = get_auth_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(BALANCE_URL, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return int(data.get("amount", 0))
        return None
    except requests.RequestException:
        return None


def resolve_email(linkedin_url: str) -> dict | None:
    """Resolve a LinkedIn profile URL to a verified work email via EazyReach.

    NOTE: This module is deprecated. Prospeo resolves emails directly.
    This function is kept for backward compatibility only.

    Returns:
        Always returns None (email resolution is now handled by Prospeo).
    """
    return None