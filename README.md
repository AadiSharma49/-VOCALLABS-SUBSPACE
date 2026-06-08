# VocalLabs Outreach Pipeline

A modular, CLI-based outreach automation pipeline that discovers lookalike companies, finds decision makers with verified email addresses, and sends personalized outreach emails.

## Pipeline

```
Input Domain
    ↓
 Ocean.io        → Find similar companies
    ↓
 Prospeo         → Find decision makers + email addresses
    ↓
 Brevo          → Send personalized outreach emails
```

## Integrations

| Integration | Status | Description |
|-------------|--------|-------------|
| **Ocean.io** | ✅ Complete & Tested | Lookalike company discovery |
| **Prospeo** | ✅ Complete & Tested | Decision maker search + email resolution (see note below) |
| **Brevo** | ✅ Complete & Tested | Transactional email delivery |
| **CLI Pipeline** | ✅ Complete & Tested | End-to-end orchestration with error handling |

> **Note on Prospeo emails:** The current Prospeo API plan returns masked/display emails (e.g. `v****@domain.com`) rather than full addresses. The pipeline detects this automatically. Contacts with masked emails are listed for reference but excluded from the send queue. A notice is displayed when masking is detected, and no masked email is ever sent to Brevo.

## Setup

1. Install dependencies:
   ```
   pip install requests python-dotenv
   ```

2. Configure `.env`:
   ```
   OCEAN_API_KEY=your_key_here
   PROSPEO_API_KEY=your_key_here
   BREVO_API_KEY=your_key_here
   ```

3. Run the pipeline:
   ```
   cd src
   python main.py
   ```

## Project Structure

```
.
├── .env                    # API keys (not committed)
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── PROJECT_ARCHITECTURE.md  # System architecture documentation
├── DEMO_SCRIPT.md          # Interview demo walkthrough
└── src/
    ├── main.py              # Pipeline orchestrator & CLI
    ├── ocean.py             # Ocean.io API integration
    ├── prospeo.py           # Prospeo API (contacts + emails)
    ├── eazyreach.py         # Deprecated (kept for reference)
    ├── brevo.py             # Brevo transactional email API
    └── templates.py         # Email template system
```

## CLI Features

- **3-stage progress display** with success/warning/error indicators
- **Smart email handling** — detects masked emails and excludes them from sends
- **Email preview** before sending
- **Safety checkpoint** — emails are never sent without explicit user confirmation
- **Final results summary** with execution time and pipeline status (SUCCESS / PARTIAL SUCCESS / FAILED)
- **Per-domain error isolation** — one failure never crashes the entire run
- **Retry logic** for rate limits (429) and server errors (5xx) on Prospeo and Brevo