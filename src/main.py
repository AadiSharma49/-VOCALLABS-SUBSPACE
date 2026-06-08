from dotenv import load_dotenv
load_dotenv()

import sys
import time
from ocean import get_lookalike_companies
from prospeo import find_decision_makers
from brevo import send_email
from templates import preview_email

# Constant for the planned mask limitation notice
PROSPEO_MASK_HELP = (
    "Prospeo returned masked emails (e.g. 'v****@domain.com'). "
    "Upgrade the Prospeo plan to receive full, unmasked email addresses."
)

DIVIDER = "=" * 52
THIN_DIVIDER = "-" * 52


def print_banner():
    print()
    print(DIVIDER)
    print("   VOCALLABS OUTREACH PIPELINE")
    print(DIVIDER)
    print()


def print_stage(stage_num: int, total: int, name: str):
    print(f"\n[{stage_num}/{total}] {name}")
    print(THIN_DIVIDER)


def print_success(msg: str):
    print(f"  \u2713 {msg}")


def print_warning(msg: str):
    print(f"  \u26a0 {msg}")


def print_error(msg: str):
    print(f"  \u2717 {msg}")


def determine_status(companies_ok, contacts, emails_sent, emails_failed, emails_with_addresses):
    """Determine final pipeline status."""
    if contacts == 0:
        return "FAILED"
    if emails_sent == 0 and emails_with_addresses > 0:
        # User chose not to send, or all sends failed
        if emails_failed > 0:
            return "FAILED"
        return "PARTIAL SUCCESS"
    if emails_failed > 0:
        return "PARTIAL SUCCESS"
    if emails_sent > 0:
        return "SUCCESS"
    if emails_with_addresses == 0:
        return "PARTIAL SUCCESS"
    return "SUCCESS"


def print_results(
    input_domain,
    companies_processed,
    companies_skipped,
    total_contacts,
    emails_with_addresses,
    emails_sent,
    emails_failed,
    execution_time,
):
    status = determine_status(
        companies_processed > 0,
        total_contacts,
        emails_sent,
        emails_failed,
        emails_with_addresses,
    )

    status_symbol = {
        "SUCCESS": "\u2713 SUCCESS",
        "PARTIAL SUCCESS": "\u26a0  PARTIAL SUCCESS",
        "FAILED": "\u2717 FAILED",
    }

    print()
    print(DIVIDER)
    print("   RESULTS")
    print(DIVIDER)
    print(f"  Companies Processed:  {companies_processed}")
    print(f"  Companies Skipped:    {companies_skipped}")
    print(f"  Contacts Found:       {total_contacts}")
    print(f"  Emails Found:         {emails_with_addresses}")
    print(f"  Emails Sent:          {emails_sent}")
    print(f"  Emails Failed:        {emails_failed}")
    print()
    print(f"  Execution Time:       {execution_time:.1f}s")
    print()
    print(f"  STATUS: {status_symbol[status]}")
    print(DIVIDER)
    print()


def main():
    start_time = time.time()

    print_banner()

    input_domain = input("  Input Domain: ").strip()
    if not input_domain:
        print_error("No domain provided. Exiting.")
        sys.exit(1)

    # Tracking counters
    companies_processed = 0
    companies_skipped = 0
    total_contacts = 0
    emails_with_addresses = 0
    emails_sent = 0
    emails_failed = 0

    # ── Stage 1: Ocean ──
    print_stage(1, 3, "Ocean")

    try:
        companies = get_lookalike_companies(input_domain)
        companies_processed = len(companies)
        print_success(f"Found {companies_processed} similar companies")
    except Exception as e:
        print_error(f"Ocean API failed: {e}")
        companies = []

    if not companies:
        print_warning("No companies found. Pipeline cannot continue.")
        elapsed = time.time() - start_time
        print_results(input_domain, 0, 0, 0, 0, 0, 0, elapsed)
        return

    top_domains = companies[:3]

    # ── Stage 2: Prospeo (contact discovery + email resolution) ──
    print_stage(2, 3, "Prospeo")

    all_contacts = []

    for d in top_domains:
        try:
            print(f"  Searching: {d} ...")
            decision_makers = find_decision_makers(d)
            if decision_makers:
                print_success(f"Found {len(decision_makers)} contacts at {d}")
                for person in decision_makers:
                    person["domain"] = d
                    all_contacts.append(person)
            else:
                companies_skipped += 1
                print_warning(f"No contacts found at {d}")
        except Exception as e:
            companies_skipped += 1
            print_error(f"Skipped {d}: {type(e).__name__}: {e}")

    total_contacts = len(all_contacts)
    print_success(f"Total contacts gathered: {total_contacts}")

    if not all_contacts:
        print_warning("No contacts found. Pipeline cannot continue.")
        elapsed = time.time() - start_time
        print_results(input_domain, companies_processed, companies_skipped, 0, 0, 0, 0, elapsed)
        return

    # Build email queue from contacts that have usable (non-masked) email addresses
    email_queue = []
    masked_count = 0

    for person in all_contacts:
        email = person.get("email", "")
        name = person["name"]
        domain = person["domain"]
        is_masked = person.get("email_is_masked", False)
        raw_masked = person.get("raw_masked_value", "")

        if is_masked:
            masked_count += 1
            print_warning(f"{name} → masked email ({raw_masked}) — cannot send")
        elif email:
            emails_with_addresses += 1
            email_queue.append({
                "email": email,
                "name": name,
                "domain": domain,
            })
            email_status = person.get("email_status", "unknown")
            print_success(f"{name} → {email} ({email_status})")
        else:
            print_warning(f"No email address for {name} — skipping")

    if masked_count > 0:
        print_warning(PROSPEO_MASK_HELP)

    print_success(f"Found {emails_with_addresses} usable email addresses")

    # ── Stage 3: Brevo ──
    print_stage(3, 3, "Brevo")

    if not email_queue:
        print_warning("No emails to send.")
    else:
        # Print summary table
        print()
        print(f"  {'#':<4} {'Name':<22} {'Email':<28} {'Domain'}")
        print(f"  {'-'*4} {'-'*22} {'-'*28} {'-'*20}")
        for i, entry in enumerate(email_queue, 1):
            print(f"  {i:<4} {entry['name']:<22} {entry['email']:<28} {entry['domain']}")
        print()

        confirm = input("  Proceed with sending emails? (y/n): ").strip().lower()

        if confirm == "y":
            # Show preview for the first email
            if email_queue:
                preview_email(email_queue[0]["name"], email_queue[0]["domain"])

            for entry in email_queue:
                print(f"\n  [Brevo] Sending to {entry['name']} ({entry['email']})...")
                success = send_email(entry["email"], entry["name"], entry["domain"])
                if success:
                    emails_sent += 1
                    print_success(f"Email sent to {entry['email']}")
                else:
                    emails_failed += 1
                    print_error(f"Failed to send to {entry['email']}")
            print(f"\n  [Brevo] Results: {emails_sent} sent, {emails_failed} failed")
        else:
            print("  Email sending cancelled.")

    # ── Final Results ──
    elapsed = time.time() - start_time
    print_results(
        input_domain,
        companies_processed,
        companies_skipped,
        total_contacts,
        emails_with_addresses,
        emails_sent,
        emails_failed,
        elapsed,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  FATAL ERROR: {type(e).__name__}: {e}")
        sys.exit(1)