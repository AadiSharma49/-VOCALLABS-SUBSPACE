# Demo Script — VocalLabs Outreach Pipeline

## Pre-Demo Checklist

- [ ] Python 3.10+ installed
- [ ] `requests` and `python-dotenv` installed (`pip install requests python-dotenv`)
- [ ] `.env` file configured with valid API keys for Ocean, Prospeo, and Brevo
- [ ] Terminal open at project root

## Demo Commands

### Start the pipeline

```
cd src
python main.py
```

### When prompted for domain, enter:

```
yandex.com
```

## Talking Points (Script)

### Opening (while Ocean stage runs)

> "This is the VocalLabs Outreach Pipeline — a modular CLI tool that automates the process of finding similar companies, identifying their decision makers with verified email addresses, and sending personalized outreach emails."

> "The pipeline has three stages: Ocean.io for company discovery, Prospeo for contact search and email resolution, and Brevo for email delivery."

### Stage 1 — Ocean

> "Ocean.io is finding lookalike companies based on the input domain. It returns a list of similar companies in the same space — like Yandex finding Mail.ru, Rambler, and other Russian tech companies."

### Stage 2 — Prospeo

> "For each company found, Prospeo searches for decision makers — people with relevant titles like CEO, Founder, or VP of Engineering. Critically, Prospeo also returns verified email addresses directly. This means no separate email resolution stage is needed."

> "You'll see each contact displayed with their email address and verification status — everything is real data, no mock or placeholder emails."

### Stage 3 — Brevo

> "Before any emails are sent, the pipeline shows a summary table with all recipients and asks for explicit confirmation. This is a safety checkpoint — nothing is sent without the user approving it."

> "Once confirmed, it shows a preview of the email content, then sends each email via Brevo's transactional email API."

### Results Summary

> "At the end, we get a complete results summary showing how many companies were processed, contacts found, emails resolved, sent, and failed — along with total execution time and a final pipeline status."

## Expected CLI Output

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
  Searching: company1.com ...
  ✓ Found 5 contacts at company1.com
  ✓ John Doe → john@company1.com (VERIFIED)
  ✓ Jane Smith → jane@company1.com (VERIFIED)
  Searching: company2.com ...
  ✓ Found 3 contacts at company2.com
  ✓ Bob Jones → bob@company2.com (VERIFIED)
  ⚠ No email address for Alice Brown — skipping
  ✓ Found 7 email addresses

[3/3] Brevo
----------------------------------------------------
  #    Name                   Email                      Domain
  ---- ---------------------- -------------------------- --------------------
  1    John Doe               john@company1.com          company1.com
  2    Jane Smith             jane@company1.com          company1.com
  3    Bob Jones              bob@company2.com           company2.com

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

## Key Points to Emphasize

1. **3-stage pipeline** — streamlined architecture after EazyReach removal
2. **Real email addresses** — Prospeo returns verified work emails, no mock data
3. **Modular architecture** — each API integration is in its own file with a clean interface
4. **Error isolation** — one failed company never crashes the entire pipeline
5. **Retry logic** — automatic retries with backoff for rate limits and server errors
6. **Safety first** — email preview and confirmation before any sends
7. **Honest status reporting** — SUCCESS, PARTIAL SUCCESS, or FAILED based on actual outcomes

## Closing

> "The pipeline is fully end-to-end with real API integrations: Ocean.io for company discovery, Prospeo for contact finding and email resolution, and Brevo for email delivery. Every email address is a real, verified work email from Prospeo. The architecture is modular, resilient, and production-ready."