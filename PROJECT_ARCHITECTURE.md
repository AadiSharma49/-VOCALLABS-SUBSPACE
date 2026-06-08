# Project Architecture — VocalLabs Outreach Pipeline

## Pipeline Overview

The pipeline takes a single company domain as input and produces a list of personalized outreach emails sent to decision makers at lookalike companies.

```
Input Domain (e.g. "yandex.com")
         │
         ▼
┌─────────────────┐
│   Ocean.io       │  Find 10+ lookalike companies
│   (Stage 1/3)    │  via POST /v3/search/companies
└────────┬────────┘
         │  List of company domains
         ▼
┌──────────────────────┐
│   Prospeo             │  Search decision makers per domain
│   (Stage 2/3)         │  via POST /search-person
│                       │  Returns name, title, linkedin_url, AND email
│                       │  (may be masked depending on API plan)
└──────────┬───────────┘
           │  List of {name, title, email, domain}
           ▼
┌─────────────────┐
│   Brevo          │  Send personalized email
│   (Stage 3/3)    │  via POST /v3/smtp/email
└─────────────────┘
```

## Module Responsibilities

### `src/main.py` — Pipeline Orchestrator

- Displays CLI banner, stage progress, and final results
- Collects user input (domain) and confirmation before sending
- Tracks metrics: companies processed/skipped, contacts found, emails found/sent/failed
- Detects masked emails from Prospeo and excludes them from the send queue
- Prints a help notice when email masking is detected
- Calculates execution time and determines final status (SUCCESS / PARTIAL SUCCESS / FAILED)
- Wraps each stage in error handling so one failure never crashes the entire run
- **3 stages** — EazyReach was removed per assignment update (Prospeo now handles email resolution)

### `src/ocean.py` — Ocean.io Integration

- **Function:** `get_lookalike_companies(domain, size=10) → list[str]`
- Calls `POST https://api.ocean.io/v3/search/companies`
- Sends `lookalikeDomains` filter with the input domain
- Returns a list of company domain strings
- Handles missing API key (raises `ValueError`) and HTTP errors

### `src/prospeo.py` — Prospeo Integration (Contact Discovery + Email Resolution)

- **Function:** `find_decision_makers(domain, limit=5) → list[dict]`
- Calls `POST https://api.prospeo.io/search-person`
- Filters by `company.websites.include` to scope to one domain
- Returns list of `{name, title, linkedin_url, email, email_status, email_is_masked, raw_masked_value}` dicts
- `email` is extracted from `person.email.email` in the Prospeo response
- `email_status` indicates verification level (e.g. "VERIFIED", "UNAVAILABLE")
- **Masked email detection:** Prospeo may return display-only emails containing asterisks (e.g. `v****@domain.com`) depending on the API plan. The `_is_masked_email()` helper checks for `*` in the value:
  - When masked: `email` is set to `""`, `email_is_masked` is `True`, `raw_masked_value` preserves the original
  - When not masked: `email` contains the real address, `email_is_masked` is `False`
  - A domain-level warning `[Prospeo] Masked email returned by API plan` is printed once per domain
- Each person dict has email as a top-level key — no separate email resolution stage needed
- Includes retry logic with exponential backoff for 429 and 5xx errors
- Returns empty list (never crashes) for any failed domain

### `src/eazyreach.py` — EazyReach Integration (Deprecated)

- **Status:** Deprecated — kept for reference only
- Prospeo now returns emails directly (even if masked), eliminating the need for a dedicated email resolution stage
- Not imported or used by the pipeline

### `src/brevo.py` — Brevo Integration

- **Function:** `send_email(to_email, person_name, company_domain) → bool`
- Calls `POST https://api.brevo.com/v3/smtp/email`
- Uses template system for subject and HTML body
- Validates email format before sending
- Includes retry logic for 429 and 5xx errors
- Returns `True`/`False` — never crashes the pipeline

### `src/templates.py` — Email Template System

- `render_subject(company_domain)` → subject line
- `render_body(person_name, company_domain)` → plain-text body
- `render_html(person_name, company_domain)` → HTML body for Brevo
- `preview_email(person_name, company_domain)` → CLI preview block
- Centralized sender name and email content

## Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Per-domain** | Prospeo failures are caught per domain; pipeline continues with remaining domains |
| **Per-person** | Contacts without emails or with masked emails are skipped; others proceed |
| **Per-email** | Brevo failures are caught per send; summary shows sent vs failed counts |
| **Retry** | Prospeo and Brevo retry up to 3 times with exponential backoff for 429/5xx |
| **Graceful degradation** | Failed stages return empty lists, never exceptions that crash the pipeline |

## Data Flow Types

```python
# Ocean output
list[str]  # ["company1.com", "company2.com", ...]

# Prospeo output (when real emails available)
list[dict]  # [
  #   {"name": "John", "title": "CEO", "linkedin_url": "...",
  #    "email": "john@company.com", "email_status": "VERIFIED",
  #    "email_is_masked": False, "raw_masked_value": "", "domain": "..."},
  # ]

# Prospeo output (when emails masked by API plan)
list[dict]  # [
  #   {"name": "John", "title": "CEO", "linkedin_url": "...",
  #    "email": "", "email_status": "VERIFIED",
  #    "email_is_masked": True, "raw_masked_value": "j***@domain.com", "domain": "..."},
  # ]

# Brevo output
bool  # True if sent, False otherwise