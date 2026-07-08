"""
Fyers Authentication Module (using raw HTTP requests).
Bypasses fyers-apiv3 SDK to avoid Python 3.14 compatibility issues.
"""

import os
import hashlib
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

FYERS_APP_ID = os.getenv("FYERS_APP_ID")
FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
FYERS_REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", ".fyers_token")

# Fyers API endpoints
AUTH_BASE_URL = "https://api-t1.fyers.in/api/v3"
TOKEN_URL = f"{AUTH_BASE_URL}/validate-authcode"


def generate_login_url() -> str:
    """Generates the Fyers login URL. User must open this in a browser."""
    params = {
        "client_id": FYERS_APP_ID,
        "redirect_uri": FYERS_REDIRECT_URI,
        "response_type": "code",
        "state": "fyers_trading_strategy",
    }
    url = f"https://api-t1.fyers.in/api/v3/generate-authcode?{urlencode(params)}"
    return url


def generate_access_token(auth_code: str) -> str:
    """
    Exchanges the auth_code for an access_token using raw HTTP POST.
    The auth_code is obtained after the user logs in via the login URL.
    """
    # Fyers requires an appIdHash = SHA256(app_id + ":" + secret_key)
    app_id_hash = hashlib.sha256(
        f"{FYERS_APP_ID}:{FYERS_SECRET_KEY}".encode()
    ).hexdigest()

    payload = {
        "grant_type": "authorization_code",
        "appIdHash": app_id_hash,
        "code": auth_code,
    }

    response = requests.post(TOKEN_URL, json=payload)
    data = response.json()

    if data.get("s") == "ok" and "access_token" in data:
        access_token = data["access_token"]
        # Save token to file for reuse
        with open(TOKEN_FILE, "w") as f:
            f.write(access_token)
        print("Access token generated and saved successfully!")
        return access_token
    else:
        raise RuntimeError(f"Failed to generate access token: {data}")


def get_access_token() -> str:
    """
    Returns an access token. Checks in order:
    1. Saved token file (.fyers_token)
    2. FYERS_AUTH_CODE in .env -> exchanges for a new token
    """
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token = f.read().strip()
        if token:
            print("Using saved access token.")
            return token

    # Try to get auth_code from .env
    auth_code = os.getenv("FYERS_AUTH_CODE", "").strip()

    if not auth_code or auth_code == "PASTE_YOUR_AUTH_CODE_HERE":
        print("=" * 60)
        print("  FYERS AUTHENTICATION REQUIRED")
        print("=" * 60)
        print()
        print("Step 1: Open the following URL in your browser:")
        print()
        print(f"  {generate_login_url()}")
        print()
        print("Step 2: Log in with your Fyers credentials.")
        print("Step 3: Copy the 'auth_code' from the redirected URL.")
        print("Step 4: Paste it into your .env file as FYERS_AUTH_CODE=<code>")
        print("Step 5: Re-run this script.")
        raise RuntimeError("No auth_code found. Please add FYERS_AUTH_CODE to your .env file.")

    return generate_access_token(auth_code)


if __name__ == "__main__":
    token = get_access_token()
    print(f"\nAccess Token: {token[:20]}...")
