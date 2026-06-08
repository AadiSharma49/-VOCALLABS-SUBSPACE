"""Prospeo integration — search-person API.

This module serves as both contact discovery AND email resolution.
Prospeo returns person data including name, title, LinkedIn URL, and
email addresses. Email fields may be masked depending on the API plan.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds base for exponential backoff


def _is_masked_email(email: str) -> bool:
    """Check if an email string is masked (contains asterisks).

    Prospeo may return masked/display emails like 'v****@domain.com'
    depending on the API plan level. Masked emails cannot be used
    for sending outreach emails.

    Args:
        email: The email string to check.

    Returns:
        True if the email contains asterisks (masked), False otherwise.
    """
    return "*" in email if email else False


def find_decision_makers(domain: str, limit: int = 5) -> list[dict]:
    """Find decision makers at a company using the Prospeo Search Person API.

    Prospeo returns person data including name, title, LinkedIn URL, AND
    email addresses. Note: depending on the Prospeo plan, email addresses
    may be masked (e.g. 'v****@domain.com').

    Args:
        domain: The company domain to search for people at.
        limit: Maximum number of people to return (default 5).

    Returns:
        A list of dicts with name, title, linkedin_url, email, email_status,
        and email_is_masked. Contacts with masked emails still have their
        email field set to empty string — the masked value is logged for
        reference but not usable for sending.
    """
    api_key = os.getenv("PROSPEO_API_KEY")
    if not api_key:
        print("[Prospeo] Skipping domain: PROSPEO_API_KEY not set")
        return []

    url = "https://api.prospeo.io/search-person"
    headers = {
        "X-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "page": 1,
        "filters": {
            "company": {
                "websites": {
                    "include": [domain]
                }
            }
        },
    }

    response = _request_with_retries(url, payload, headers)

    if response is None:
        print(f"[Prospeo] Skipping domain: {domain}")
        print("  Reason: Max retries exhausted for transient errors")
        return []

    status = response.status_code

    if status == 400:
        print(f"[Prospeo] Skipping domain: {domain}")
        print("  Reason: Bad Request")
        return []

    if status == 429:
        print(f"[Prospeo] Skipping domain: {domain}")
        print("  Reason: Rate Limited")
        return []

    if status >= 500:
        print(f"[Prospeo] Skipping domain: {domain}")
        print(f"  Reason: Server Error ({status})")
        return []

    if status == 401:
        print(f"[Prospeo] Skipping domain: {domain}")
        print("  Reason: Invalid API Key")
        return []

    if status != 200:
        print(f"[Prospeo] Skipping domain: {domain}")
        print(f"  Reason: HTTP {status}")
        return []

    data = response.json()

    if data.get("error"):
        error_code = data.get("error_code", "UNKNOWN")
        print(f"[Prospeo] Skipping domain: {domain}")
        print(f"  Reason: API error - {error_code}")
        return []

    results = data.get("results", [])
    if not results:
        return []

    # Track whether we saw any masked emails across this domain
    any_masked = False

    decision_makers = []
    for item in results[:limit]:
        person = item.get("person", {})
        full_name = person.get("full_name", "")
        if not full_name:
            first = person.get("first_name", "")
            last = person.get("last_name", "")
            full_name = f"{first} {last}".strip()

        title = person.get("current_job_title", "") or person.get("job_title", "") or person.get("title", "")
        linkedin_url = person.get("linkedin_url", "") or person.get("linkedin", "")

        # Extract and validate email from Prospeo response
        email = ""
        email_status = "unavailable"
        email_is_masked = False
        raw_masked = ""

        email_data = person.get("email")
        if isinstance(email_data, dict):
            raw_val = email_data.get("email", "") or ""
            email_status = email_data.get("status", "unavailable")
            revealed = email_data.get("revealed")

            if raw_val:
                if _is_masked_email(raw_val):
                    # Email is masked — the API returned a display version
                    email_is_masked = True
                    any_masked = True
                    raw_masked = raw_val
                    # Do NOT set email to the masked value; leave it empty
                    email = ""
                    # Only print per-contact message if this is a new masked occurrence
                else:
                    # Real, usable email
                    email = raw_val

        decision_makers.append({
            "name": full_name,
            "title": title,
            "linkedin_url": linkedin_url,
            "email": email,
            "email_status": email_status,
            "email_is_masked": email_is_masked,
            "raw_masked_value": raw_masked,
        })

    # If all returned emails for this domain are masked, print a domain-level notice
    if any_masked:
        print(f"[Prospeo] Masked email returned by API plan")

    return decision_makers


def _request_with_retries(url: str, payload: dict, headers: dict) -> "requests.Response | None":
    """Send POST request with retries for 429 and 5xx errors.

    Returns the final Response object, or None if all retries are exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"[Prospeo] Request error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                print(f"[Prospeo] Retrying in {wait}s...")
                time.sleep(wait)
            continue

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", RETRY_BACKOFF * attempt))
            print(f"[Prospeo] Rate limited on attempt {attempt}. Retrying after {retry_after}s...")
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            wait = RETRY_BACKOFF * attempt
            print(f"[Prospeo] Server error {response.status_code} on attempt {attempt}. Retrying in {wait}s...")
            time.sleep(wait)
            continue

        return response

    return None