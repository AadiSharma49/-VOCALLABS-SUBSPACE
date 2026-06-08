# VocalLabs Outreach Pipeline — Interview Preparation Guide

> **Generated from actual project code.** Every explanation references real functions, variables, and API calls from the codebase.

---

## Table of Contents

1. [Beginner Explanation](#1-beginner-explanation)
2. [Interview-Level Explanation](#2-interview-level-explanation)
3. [Senior Engineer Explanation](#3-senior-engineer-explanation)
4. [Architecture Deep Dive](#4-architecture-deep-dive)
5. [End-to-End Workflow](#5-end-to-end-workflow)
6. [Top 20 Interview Questions & Answers](#6-top-20-interview-questions--answers)

---

## 1. Beginner Explanation

### What is this project?

A Python program that runs in the terminal (CLI). You give it a company's website domain (like `google.com`), and it:

1. **Finds similar companies** using Ocean.io API
2. **Finds people who work there** (decision makers like CEOs, VPs) using Prospeo API
3. **Sends them personalized emails** using Brevo API

### Simple Data Flow

```
Your input: "yandex.com"
        ↓
Step 1: Ocean API → returns ["mail.ru", "rambler.ru", ...] (similar companies)
        ↓
Step 2: Prospeo API → returns [{"name": "Ivan", "email": "ivan@mail.ru"}, ...]
        ↓
Step 3: Brevo API → sends "Hi Ivan, I have an idea for mail.ru..."
```

### Files Explained (Like I'm Five)

| File | What it does |
|------|-------------|
| `main.py` | The **boss** — tells other files when to run and in what order |
| `ocean.py` | The **scout** — goes out and finds similar companies |
| `prospeo.py` | The **detective** — finds people's names and emails |
| `brevo.py` | The **mailman** — delivers the emails |
| `templates.py` | The **writer** — writes the email content |
| `eazyreach.py` | The **retired worker** — not used anymore, just kept as a reminder |

### Environment Variables

Think of these like locker combinations stored in a `.env` file:

- **OCEAN_API_KEY** — password to use Ocean API
- **PROSPEO_API_KEY** — password to use Prospeo API
- **BREVO_API_KEY** — password to use Brevo (sending emails)

### What's "Masked Email"?

The Prospeo API on the current plan returns emails like `v****@yandex.com.tr` instead of the full address. The `*` hides most characters. The pipeline detects this and warns you: *"Hey, upgrade your plan to get real emails."* It won't try to send to `v****@yandex.com.tr` because that would bounce.

---

## 2. Interview-Level Explanation

### Purpose

A modular CLI application that automates B2B outreach. Given an input company domain, it discovers lookalike companies, identifies decision makers with their contact information, and sends personalized cold emails — all through a single terminal command.

### Architecture

**3-stage pipeline** (was 4, EazyReach removed per assignment update):

```
main.py (orchestrator)
 ├─ Stage 1: ocean.get_lookalike_companies()
 ├─ Stage 2: prospeo.find_decision_makers()
 └─ Stage 3: brevo.send_email()
```

**Pattern:** Pipeline/Orchestrator pattern. `main.py` controls the flow. Each module is independent with a single public function. Data flows as Python lists of dicts between stages.

### File-by-File Breakdown

#### `src/main.py` — Orchestrator (260 lines)

- **`print_banner()`** — prints the CLI header graphic
- **`print_stage(n, total, name)`** — prints `[1/3] Ocean` style headers
- **`print_success/warning/error(msg)`** — prints checkmark/warning/X symbols
- **`determine_status(...)`** — evaluates counters and returns `"SUCCESS"`, `"PARTIAL SUCCESS"`, or `"FAILED"`
- **`print_results(...)`** — prints the final summary table
- **`main()`** — the core function. Collects domain input, runs stages in sequence, handles errors at each boundary, manages counters, and prints results

**Key design decisions:**
- Every stage is wrapped in `try/except Exception` — one failing stage doesn't crash the pipeline
- Uses `input()` for user confirmation before sending emails — safety checkpoint
- Tracks 6 counters: `companies_processed`, `companies_skipped`, `total_contacts`, `emails_with_addresses`, `emails_sent`, `emails_failed`
- Splits the top 3 domains from Ocean results to limit Prospeo API calls

#### `src/ocean.py` — Ocean.io API (54 lines)

- **`get_lookalike_companies(domain, size=10)`** → `list[str]`
- Calls `POST https://api.ocean.io/v3/search/companies`
- Request payload: `{"size": 10, "companiesFilters": {"lookalikeDomains": ["input.com"]}}`
- Response: `{"companies": [{"company": {"domain": "similar.com"}}]}`
- Env required: `OCEAN_API_KEY`

**Error handling:** Raises `ValueError` if API key missing. Uses `response.raise_for_status()` for HTTP errors (caught by `main.py`'s try/except).

#### `src/prospeo.py` — Prospeo API + Email Extraction (206 lines)

- **`_is_masked_email(email)`** — detects `*` in email strings
- **`find_decision_makers(domain, limit=5)`** → `list[dict]`
- **`_request_with_retries(url, payload, headers)`** — retry helper

Calls `POST https://api.prospeo.io/search-person` with:
```json
{"page": 1, "filters": {"company": {"websites": {"include": ["domain.com"]}}}}
```

Response contains `results[].person.email`:
```json
{"status": "VERIFIED", "revealed": false, "email": "v****@domain.com"}
```

Returns dicts with keys: `name`, `title`, `linkedin_url`, `email`, `email_status`, `email_is_masked`, `raw_masked_value`

**Retry logic:** 3 attempts with exponential backoff (2s, 4s, 6s) for 429 (rate limit) and 5xx (server error). Uses `Retry-After` header if provided.

**HTTP status handling:** 400 (bad request), 429 (rate limited), 500+ (server error), 401 (invalid key) — all caught and logged, empty list returned.

#### `src/brevo.py` — Brevo Email API (125 lines)

- **`_is_valid_email(email)`** — regex validation: `^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`
- **`send_email(to_email, person_name, company_domain)`** → `bool`
- **`_request_with_retries(url, payload, headers)`** — same retry pattern as prospeo.py

Calls `POST https://api.brevo.com/v3/smtp/email` with sender, recipient, subject (from templates), and HTML body.

**Return convention:** Always returns `bool`. Never raises exceptions — the pipeline continues even if sending fails.

#### `src/templates.py` — Email Content (58 lines)

- **`render_subject(domain)`** → `"Quick idea for {domain}"`
- **`render_body(name, domain)`** → plain text email body
- **`render_html(name, domain)`** → HTML version by replacing `\n` with `<br/>`
- **`preview_email(name, domain)`** — prints the email in CLI for user review before sending

### Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Per-stage** | Each stage is in a try/except block in `main()` |
| **Per-domain** | Prospeo failures are isolated per company domain |
| **Per-person** | Contacts without/masked emails are skipped individually |
| **Per-email** | Each Brevo send is independent; failures don't stop others |
| **Retry** | Prospeo & Brevo: 3 retries, exponential backoff, 30s timeout |

### Masked Email Detection

The `_is_masked_email()` function checks if `"*" in email`. When detected:
- `email` field is set to `""` (empty string)
- `email_is_masked` is set to `True`
- `raw_masked_value` stores the original masked string
- The pipeline prints a warning: *"Masked email returned by API plan"*
- The contact is excluded from the Brevo send queue

---

## 3. Senior Engineer Explanation

### Architectural Analysis

**Pattern:** Pipeline/Chain-of-Responsibility with **fault isolation** at every boundary.

**Design strengths:**
1. **Single Responsibility** — each module does exactly one thing and exposes one public function
2. **Dependency Injection (lightweight)** — modules import their own env vars; `main.py` doesn't know which API keys exist
3. **Fail-fast at stage level, fail-soft at operation level** — if Ocean crashes, the pipeline stops early with a clear message. If one Prospeo domain fails, the pipeline continues with remaining domains
4. **Defensive parsing** — `prospeo.py` uses `.get()` with defaults everywhere, handles missing keys, validates email structure
5. **Idempotent retry** — `_request_with_retries()` separates transient errors (429, 5xx) from fatal errors (400, 401) and only retries the former

**Trade-offs worth discussing:**
1. **No async** — synchronous `requests` means each API call blocks. For 3 domains × 5 contacts = 15 email sends at ~1s each = 15s. Acceptable for a CLI tool but would need `asyncio`/`aiohttp` for production scale
2. **No database** — all state is in memory. If the pipeline crashes mid-send, there's no recovery. A work queue (Redis/SQS) would be the production upgrade
3. **CLI only** — no web UI, no API endpoint, no scheduled execution. The `main()` function is tightly coupled to `input()`
4. **Prospeo plan limitation** — masked emails are a blocker for real sends. The detection is clean, but the pipeline can't complete its primary goal without a plan upgrade

### Data Flow in Detail

```
input()
  ↓ (str domain)
main().companies = ocean.get_lookalike_companies(domain)
  ↓ (list[str] of up to 10 domains)
top_domains = companies[:3]  # truncate to 3
  ↓ (list[str] of 3 domains)
for d in top_domains:
    prospeo.find_decision_makers(d)
    ↓ (list[dict] per domain, merged into all_contacts)
for person in all_contacts:
    if email_is_masked → skip, log warning
    if email → add to email_queue
    if no email → skip
  ↓ (list[dict] of sendable contacts)
brevo.send_email(entry["email"], entry["name"], entry["domain"])
  ↓ (bool per send)
summary printed
```

### API Contract Design

Each module returns **simple, predictable types**:

```python
# ocean.py → list[str]  (guaranteed, never None)
# prospeo.py → list[dict]  (guaranteed, never None, never raises)
# brevo.py → bool  (guaranteed, never None, never raises)
```

This is the **Null Object Pattern** — returning empty collections instead of `None` means callers don't need null checks. `for d in companies:` works whether there are 0 or 10 items.

### Retry Strategy Comparison (prospeo.py vs brevo.py)

Both implement the same algorithm but independently:
- MAX_RETRIES = 3
- RETRY_BACKOFF = 2 seconds (base)
- 429: uses `Retry-After` header if present, otherwise linear backoff
- 5xx: exponential backoff (`attempt * RETRY_BACKOFF`)
- Network errors (DNS, timeout, connection refused): retried with backoff
- All other status codes: returned immediately (no retry)

**Why separate implementations?** Each module is independent. If Brevo needed different retry behavior (e.g., longer backoff for email rate limits), the change is isolated.

### Environment Variable Management

`load_dotenv()` is called in every module that needs env vars. This is a deliberate choice — each module is independently testable. `main.py` calls it first (line 1-2), but `ocean.py`, `prospeo.py`, and `brevo.py` also call it as a safety net.

---

## 4. Architecture Deep Dive

### Project Structure

```
vocallabs-outreach-pipeline/
├── .env                          # API credentials (gitignored)
├── .gitignore                    # Excludes .env, __pycache__/, .vscode/
├── README.md                     # Project overview & setup
├── PROJECT_ARCHITECTURE.md       # Detailed tech documentation
├── DEMO_SCRIPT.md                # Interview demo walkthrough
├── INTERVIEW_GUIDE.md            # ← You are here
└── src/
    ├── main.py                   # Orchestrator (260 lines)
    ├── ocean.py                  # Ocean.io API (54 lines)
    ├── prospeo.py                # Prospeo API + email extraction (206 lines)
    ├── brevo.py                  # Brevo transactional email (125 lines)
    ├── templates.py              # Email templates (58 lines)
    └── eazyreach.py              # Deprecated, kept for reference
```

### Module Dependency Graph

```
main.py
  ├── ocean.py       (import get_lookalike_companies)
  ├── prospeo.py     (import find_decision_makers)
  ├── brevo.py       (import send_email)
  └── templates.py   (import preview_email)

brevo.py
  └── templates.py   (import render_subject, render_html, SENDER_NAME)
```

No circular dependencies. Each arrow represents a single function import.

### External API Dependencies

| API | Endpoint | Method | Auth Header | Purpose |
|-----|----------|--------|-------------|---------|
| Ocean.io | `api.ocean.io/v3/search/companies` | POST | `X-Api-Token` | Lookalike company search |
| Prospeo | `api.prospeo.io/search-person` | POST | `X-KEY` | Person search with emails |
| Brevo | `api.brevo.com/v3/smtp/email` | POST | `api-key` | Transactional email send |

### Safety Mechanisms

1. **Confirmation gate:** User must type `y` before any emails are sent
2. **Email preview:** Shows the first email content before sending
3. **Summary table:** Lists all recipients before the confirmation prompt
4. **Masked email detection:** Automatically filters out emails with asterisks
5. **Graceful degradation:** Every failure produces a message but doesn't crash

---

## 5. End-to-End Workflow

### Console Session (Simulated)

```
====================================================
   VOCALLABS OUTREACH PIPELINE
====================================================

  Input Domain: yandex.com

[1/3] Ocean
----------------------------------------------------
  ✓ Found 10 similar companies

[2/3] Prospeo
----------------------------------------------------
  Searching: mail.ru ...
  ✓ Found 5 contacts at mail.ru
  ✓ Ivan Petrov → ivan@mail.ru (VERIFIED)
  ✓ Olga Sidorova → olga@mail.ru (VERIFIED)
  Searching: rambler.ru ...
  ✓ Found 3 contacts at rambler.ru
  ⚠ Alex Smirnov → masked email (a****@rambler.ru) — cannot send
  ✓ Total contacts gathered: 8
[Prospeo] Masked email returned by API plan
  ✓ Found 7 usable email addresses

[3/3] Brevo
----------------------------------------------------
  #    Name                   Email                      Domain
  ---- ---------------------- -------------------------- --------------------
  1    Ivan Petrov            ivan@mail.ru               mail.ru
  2    Olga Sidorova          olga@mail.ru               mail.ru
  ...

  Proceed with sending emails? (y/n): n
  Email sending cancelled.

====================================================
   RESULTS
====================================================
  Companies Processed:  10
  Companies Skipped:    1
  Contacts Found:       8
  Emails Found:         7
  Emails Sent:          0
  Emails Failed:        0

  Execution Time:       12.3s

  STATUS: ⚠  PARTIAL SUCCESS
====================================================
```

---

## 6. Top 20 Interview Questions & Answers

### Question 1: Explain the overall architecture of this project.

**Answer:** It's a pipeline architecture with 3 stages. `main.py` is the orchestrator that calls one function from each module sequentially. Each module (`ocean.py`, `prospeo.py`, `brevo.py`) encapsulates a single external API integration. Data flows as Python lists of dicts between stages. Error handling at each boundary ensures one failure doesn't crash the entire pipeline.

### Question 2: How does `main.py` handle errors in each stage?

**Answer:** Each stage is wrapped in `try/except Exception`. If Ocean fails, companies becomes `[]` and the pipeline exits early with a warning. If Prospeo fails for a specific domain, `companies_skipped` increments and the loop continues to the next domain. If Brevo fails for a specific email, that send is logged as failed but other sends continue. This is **graceful degradation** — the pipeline always completes, even with partial failures.

### Question 3: What's the retry logic and why did you implement it yourself instead of using a library?

**Answer:** Both `prospeo.py` and `brevo.py` have `_request_with_retries()` with 3 attempts, exponential backoff starting at 2 seconds, and special handling for HTTP 429 (uses `Retry-After` header) and 5xx errors (exponential backoff). Network errors (timeouts, DNS failures) are also retried. I implemented it manually because the logic is simple (15 lines), avoids adding a dependency like `tenacity` or `backoff`, and gives full control over which status codes trigger retries vs. immediate failure.

### Question 4: How do you detect masked emails and what happens when you find one?

**Answer:** The `_is_masked_email()` function checks if `"*"` is in the email string. When detected, the `email` field is set to empty string, `email_is_masked` becomes `True`, and `raw_masked_value` stores the original. In `main.py`, contacts with `email_is_masked=True` are excluded from the Brevo send queue and a warning is displayed. A help message suggests upgrading the Prospeo plan. This prevents sending to invalid addresses.

### Question 5: Why is `eazyreach.py` still in the project if it's not used?

**Answer:** It's kept as a reference. The original pipeline had 4 stages including EazyReach for email resolution. Per the assignment update, Prospeo now handles email resolution directly, so the EazyReach module is deprecated but preserved to show the evolution of the architecture. It's not imported anywhere in `main.py`.

### Question 6: What environment variables are used and how are they loaded?

**Answer:** Four env vars: `OCEAN_API_KEY`, `PROSPEO_API_KEY`, `BREVO_API_KEY` from the original setup, plus `EAZYREACH_CLIENT_ID` and `EAZYREACH_CLIENT_SECRET` (for the now-deprecated EazyReach module). They're loaded via `python-dotenv`'s `load_dotenv()` which reads from `.env`. Each module calls `load_dotenv()` independently so they're self-contained for testing.

### Question 7: How would you scale this pipeline to handle thousands of companies per run?

**Answer:** Several changes needed: (1) Replace synchronous `requests` with `asyncio`/`aiohttp` for concurrent API calls. (2) Replace in-memory state with a database or message queue (Redis/SQS) for persistence and recovery. (3) Add rate-limit-aware scheduling to respect API quotas. (4) Move from CLI to a scheduled service (cron/AWS Lambda/Cloud Run). (5) Add idempotency keys to prevent duplicate processing. (6) Add webhook support for long-running operations.

### Question 8: Explain the data structures used for data flow between modules.

**Answer:** Three main types: `list[str]` for company domains (Ocean output), `list[dict]` for contacts (Prospeo output) with keys `name`, `title`, `linkedin_url`, `email`, `email_status`, `email_is_masked`, `raw_masked_value`, and `bool` for Brevo send results. `main.py` transforms Prospeo's output into an `email_queue` which is `list[dict]` with `email`, `name`, `domain`. The type annotations are in docstrings, not enforced at runtime (Python duck typing).

### Question 9: How do you ensure no API keys are committed to GitHub?

**Answer:** The `.gitignore` file explicitly excludes `.env` from version control. The initial `git add` command only staged specific source files, not the `.env` file. This is a standard security practice — credentials should never be in repositories, especially public ones.

### Question 10: Why does `prospeo.py` return an empty list instead of raising exceptions?

**Answer:** It follows the **Null Object Pattern**. Returning `[]` means `main.py` can always iterate safely: `for person in decision_makers:` works whether there are 0 or 5 items. No null checks needed. This simplifies the orchestrator code and prevents `AttributeError` or `TypeError` crashes.

### Question 11: Compare `prospeo.py`'s retry function with `brevo.py`'s — are they duplicated code?

**Answer:** They are structurally identical but independently implemented. This is a deliberate trade-off — code duplication vs. coupling. Each module is fully self-contained: you can test `prospeo.py` in isolation without `brevo.py` and vice versa. If Brevo needed different retry parameters (e.g., longer backoff due to stricter rate limits), the change is isolated. In a larger codebase, I'd extract a shared utility module.

### Question 12: What happens if the Prospeo API returns no results?

**Answer:** If Prospeo returns empty results for a domain, `find_decision_makers()` returns `[]`. In `main.py`, this triggers `companies_skipped += 1` and a warning message. The pipeline continues to the next domain. If all domains return empty, `total_contacts` is 0 and the pipeline exits early with a "No contacts found" warning.

### Question 13: How does the Brevo module validate email addresses before sending?

**Answer:** The `_is_valid_email()` function uses regex: `^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`. It checks for a valid local part, `@`, domain, and TLD (minimum 2 chars like `.io`). This catches obvious typos but doesn't verify deliverability. Also, `main.py` already filters out masked emails before they reach Brevo, so the regex is a secondary safety net.

### Question 14: How would you test this pipeline?

**Answer:** Three levels: (1) **Unit tests** — mock `requests.post` for each module and verify parsing logic, retry behavior, and error handling. (2) **Integration tests** — run against real/sandbox APIs with a test domain and verify the pipeline completes without errors. (3) **End-to-end** — run the full pipeline with confirmation set to "n" (cancel before send) and verify counters match expectations. The modular design makes unit testing straightforward since each module has a single public function with clear inputs and outputs.

### Question 15: What's the significance of `companies[:3]` in `main.py`?

**Answer:** Ocean returns up to 10 similar companies. Processing all 10 through Prospeo would consume API credits and increase runtime. `companies[:3]` limits to the top 3 most similar results. This is a practical optimization — in most B2B outreach scenarios, 3 companies provide enough contacts for a meaningful campaign. It's also a form of resource management: fewer API calls means faster execution and lower cost.

### Question 16: How does the `determine_status()` function work?

**Answer:** It evaluates 5 counters to classify the pipeline outcome:
- **FAILED:** No contacts found, or sends exhausted with failures
- **PARTIAL SUCCESS:** User cancelled sending (had contacts but 0 sent), or some sends failed, or no usable emails found
- **SUCCESS:** At least 1 email sent with 0 failures

This provides honest, nuanced reporting rather than a binary pass/fail.

### Question 17: What security considerations are relevant here?

**Answer:** (1) API keys stored in `.env` (gitignored) — standard practice. (2) Sender email `outreach@vocallabs.com` is hardcoded — could be an env var. (3) No user data is persisted — all state is in-memory. (4) The Brevo API key has permission to send emails — limiting its scope in the Brevo dashboard would be wise. (5) No authentication for the CLI itself — anyone with terminal access can run the pipeline.

### Question 18: How would you add a new API integration (e.g., a new email provider)?

**Answer:** Create a new file (e.g., `sendgrid.py`) with a single public function matching the Brevo interface signature. The function should accept `to_email, person_name, company_domain` and return `bool`. In `main.py`, swap the import: replace `from brevo import send_email` with `from sendgrid import send_email`. If both need to coexist, add configuration to select the provider. The key insight: **the interface is the contract** — as long as `send_email(email, name, domain) → bool` is consistent, the pipeline doesn't care which provider is underneath.

### Question 19: Explain the `_request_with_retries()` function's algorithm in detail.

**Answer:** The algorithm:
1. Loop 1 to MAX_RETRIES (3)
2. Try POST with 30s timeout
3. On network error → log, wait `attempt * RETRY_BACKOFF` seconds, retry
4. On HTTP 429 → read `Retry-After` header (or default to `attempt * RETRY_BACKOFF`), wait, retry (don't decrement attempt count for 429 specifically — note: this actually does use `continue` which increments the attempt counter, a potential improvement point)
5. On HTTP 500+ → wait `attempt * RETRY_BACKOFF`, retry
6. On any other status code → return response immediately (success or fatal error)
7. After 3 attempts → return None

**Potential improvement:** 429 retries should ideally not count toward the 3-attempt limit since they indicate the server is temporarily overloaded, not that our request is bad.

### Question 20: How would you convert this CLI tool into a web service?

**Answer:** (1) Extract the core logic from `main()` into an async function. (2) Use FastAPI or Flask to expose `POST /pipeline` that accepts `{"domain": "..."}` and returns a `pipeline_id`. (3) Run the pipeline as a background task (Celery/ARQ) with WebSocket polling for progress. (4) Add a simple React/Vue frontend for domain input and real-time progress display. (5) Store results in PostgreSQL/SQLite. (6) Add authentication (JWT) to protect API endpoints. (7) The modular architecture makes this straightforward — `ocean.py`, `prospeo.py`, `brevo.py` need zero changes.

---

### Quick Reference: Functions & Their Signatures

```python
# ocean.py
get_lookalike_companies(domain: str, size: int = 10) -> list[str]

# prospeo.py
find_decision_makers(domain: str, limit: int = 5) -> list[dict]
  # Dict keys: name, title, linkedin_url, email, email_status,
  #            email_is_masked, raw_masked_value

# brevo.py
send_email(to_email: str, person_name: str, company_domain: str) -> bool

# templates.py
render_subject(company_domain: str) -> str
render_body(person_name: str, company_domain: str) -> str
render_html(person_name: str, company_domain: str) -> str
preview_email(person_name: str, company_domain: str) -> None
```

### Quick Reference: HTTP Status Code Handling

| Status | Prospeed | Brevo |
|--------|----------|-------|
| 200/201 | ✅ Success | ✅ Success |
| 400 | ⛔ Bad Request → skip | ⛔ Bad Request → fail |
| 401 | ⛔ Invalid Key → skip | N/A |
| 429 | 🔄 Retry (up to 3x) | 🔄 Retry (up to 3x) |
| 500+ | 🔄 Retry (up to 3x) | 🔄 Retry (up to 3x) |
| Network error | 🔄 Retry (up to 3x) | 🔄 Retry (up to 3x) |