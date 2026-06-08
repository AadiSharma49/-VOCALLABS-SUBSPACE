import os
import re
import time
import requests
from dotenv import load_dotenv
from templates import render_subject, render_html, SENDER_NAME

load_dotenv()

MAX_RETRIES = 3
RETRY_BACKOFF = 2

SENDER_EMAIL = "outreach@vocallabs.com"


def send_email(to_email: str, person_name: str, company_domain: str) -> bool:
    """Send a outreach email via the Brevo (Sendinblue) Transactional Email API.

    Args:
        to_email: Recipient email address.
        person_name: Name of the recipient.
        company_domain: Domain of the recipient's company.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        print("[Brevo] Cannot send email: BREVO_API_KEY not set")
        return False

    if not _is_valid_email(to_email):
        print(f"[Brevo] Invalid email address: {to_email}")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL,
        },
        "to": [
            {
                "email": to_email,
                "name": person_name,
            }
        ],
        "subject": render_subject(company_domain),
        "htmlContent": render_html(person_name, company_domain),
    }

    response = _request_with_retries(url, payload, headers)

    if response is None:
        print(f"[Brevo] Failed to send to {to_email}: max retries exhausted")
        return False

    status = response.status_code

    if status == 201 or status == 200:
        print(f"[Brevo] Email sent to {to_email}")
        return True

    if status == 400:
        try:
            err = response.json().get("message", "Bad Request")
        except Exception:
            err = "Bad Request"
        print(f"[Brevo] Failed to send to {to_email}: {err}")
        return False

    if status == 429:
        print(f"[Brevo] Failed to send to {to_email}: Rate Limited")
        return False

    if status >= 500:
        print(f"[Brevo] Failed to send to {to_email}: Server Error ({status})")
        return False

    try:
        err = response.json().get("message", f"HTTP {status}")
    except Exception:
        err = f"HTTP {status}"
    print(f"[Brevo] Failed to send to {to_email}: {err}")
    return False


def _is_valid_email(email: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _request_with_retries(url: str, payload: dict, headers: dict) -> "requests.Response | None":
    """Send POST request with retries for 429 and 5xx errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"[Brevo] Request error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                print(f"[Brevo] Retrying in {wait}s...")
                time.sleep(wait)
            continue

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", RETRY_BACKOFF * attempt))
            print(f"[Brevo] Rate limited on attempt {attempt}. Retrying after {retry_after}s...")
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            wait = RETRY_BACKOFF * attempt
            print(f"[Brevo] Server error {response.status_code} on attempt {attempt}. Retrying in {wait}s...")
            time.sleep(wait)
            continue

        return response

    return None