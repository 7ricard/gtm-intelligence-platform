from src.scraper import fetch_company_content
from src.researcher import research_account
from src.database import save_account


def run_research(company_name: str, domain: str) -> dict:
    content = fetch_company_content(domain)
    result = research_account(company_name, domain, content)

    result["company_name"] = company_name
    result["domain"] = domain
    result["homepage_content"] = content

    saved_id = save_account(result)
    result["saved_id"] = saved_id

    return result
