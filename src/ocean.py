import os
import requests
from dotenv import load_dotenv

load_dotenv()


def get_lookalike_companies(domain: str, size: int = 10) -> list[str]:
    """Find lookalike companies for a given domain using the Ocean API.

    Args:
        domain: The company domain to find lookalikes for.
        size: Number of lookalike companies to return (default 10).

    Returns:
        A list of company domain strings.

    Raises:
        ValueError: If the OCEAN_API_KEY environment variable is not set.
        requests.HTTPError: If the API returns an HTTP error response.
    """
    api_key = os.getenv("OCEAN_API_KEY")
    if not api_key:
        raise ValueError("OCEAN_API_KEY environment variable is not set")

    url = "https://api.ocean.io/v3/search/companies"
    headers = {
        "X-Api-Token": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "size": size,
        "companiesFilters": {
            "lookalikeDomains": [domain]
        },
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    data = response.json()
    companies = data.get("companies", [])

    if not companies:
        return []

    domains = []
    for item in companies:
        company_data = item.get("company", {})
        domain_name = company_data.get("domain")
        if domain_name:
            domains.append(domain_name)

    return domains
