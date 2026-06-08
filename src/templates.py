"""Email template system for outreach messages."""

SENDER_NAME = "VocalLabs"


def render_subject(company_domain: str) -> str:
    """Generate the email subject line."""
    return f"Quick idea for {company_domain}"


def render_body(person_name: str, company_domain: str) -> str:
    """Generate a plain-text email body."""
    return (
        f"Hi {person_name},\n"
        f"\n"
        f"I came across {company_domain} while researching companies in the space "
        f"and wanted to reach out.\n"
        f"\n"
        f"We've been working on automating outbound workflows and lead generation "
        f"processes, and I thought there might be an opportunity to help improve "
        f"efficiency and save time.\n"
        f"\n"
        f"Would you be open to a brief conversation to explore if this could be "
        f"relevant for your team?\n"
        f"\n"
        f"Best regards,\n"
        f"The VocalLabs Team"
    )


def render_html(person_name: str, company_domain: str) -> str:
    """Generate an HTML email body."""
    plain = render_body(person_name, company_domain)
    html_body = plain.replace("\n", "<br/>\n")
    return (
        '<html>\n'
        '<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">\n'
        f'<p>{html_body}</p>\n'
        '</body>\n'
        '</html>'
    )


def preview_email(person_name: str, company_domain: str):
    """Print a CLI preview of the email that will be sent."""
    subject = render_subject(company_domain)
    body = render_body(person_name, company_domain)

    print()
    print("  ── EMAIL PREVIEW " + "─" * 34)
    print(f"  To:      {person_name}")
    print(f"  Subject: {subject}")
    print()
    for line in body.split("\n"):
        print(f"  {line}")
    print()
    print("  ── END PREVIEW " + "─" * 35)
    print()