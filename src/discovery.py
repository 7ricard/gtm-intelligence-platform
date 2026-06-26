import json
import os
import re

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

from src.profiles import get_active_profile

load_dotenv()

client = Anthropic()

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
        return json.loads(cleaned)


def generate_discovery_queries(focus: str = None) -> list:
    profile = get_active_profile()
    firmographic = profile["firmographic"]
    verticals = ", ".join(firmographic.get("verticals", []))
    arr_range = firmographic.get("arr_range", "")
    funding_stage = firmographic.get("funding_stage", "")
    geographies = ", ".join(firmographic.get("geographies", [])) or "any"
    positive_signals = ", ".join(profile.get("positive_signals", []))

    focus_line = f"Additional focus: {focus}" if focus else ""
    prompt = f"""You are a B2B SaaS market researcher. Generate about 5 targeted web search queries that will surface recently announced funding rounds for obscure or emerging startups matching this ICP.

ICP:
- Stage: {funding_stage}
- Verticals: {verticals}
- ARR range: {arr_range}
- Geographies: {geographies}
- Positive signals to surface: {positive_signals}
{focus_line}

QUERY GUIDELINES
- Favor recently announced rounds with small dollar amounts, for example "$3 million Series A", "$5 million Series A B2B SaaS", "$8 million Series A startup 2024".
- Target trade press sources that cover small rounds: TechCrunch, Axios Pro Rata, Business Wire, PR Newswire, Crunchbase News.
- Include year references (2024, 2025) to bias toward recent announcements.
- Vary the vertical angle, for example fintech, devtools, HR tech, vertical SaaS, security.
- Do NOT generate "top SaaS companies", "best SaaS tools", or any ranking or list-style queries. Those surface large, well-known companies, not emerging startups.

Return ONLY a raw JSON array of query strings, no markdown, no code fences."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.content[0].text)


def resolve_domain(company_name: str, hint_domain: str = None) -> dict | None:
    """Returns {"domain": str, "content": str} or None."""
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    tlds = [".com", ".io", ".ai", ".co", ".app"]
    candidates = []

    if hint_domain:
        hint = hint_domain.lower().strip().rstrip("/")
        if not hint.startswith("http"):
            hint_clean = hint
        else:
            hint_clean = hint.split("//", 1)[-1].split("/")[0]
        candidates.append(hint_clean)

    for tld in tlds:
        candidate = f"{slug}{tld}"
        if candidate not in candidates:
            candidates.append(candidate)

    headers = {"User-Agent": BROWSER_USER_AGENT}
    first_200 = None
    first_200_content = ""

    for domain in candidates:
        try:
            resp = requests.get(
                f"https://{domain}",
                headers=headers,
                timeout=5,
                allow_redirects=True,
            )
            if resp.status_code != 200:
                continue
            text = resp.text
            if len(text) < 200:
                continue
            if first_200 is None:
                first_200 = domain
                first_200_content = text
            if company_name.lower() in text.lower():
                print(f"Domain: {domain} resolved for {company_name}")
                return {"domain": domain, "content": text}
        except Exception:
            continue

    if first_200:
        print(f"Domain: {first_200} resolved for {company_name}")
        return {"domain": first_200, "content": first_200_content}

    print(f"Domain: none found for {company_name}")
    return None


def verify_company_match(company_name: str, domain: str, page_content: str) -> str:
    """Returns 'high', 'medium', 'low', or 'no match'."""
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    name_lower = company_name.lower()
    content_lower = page_content.lower()
    domain_lower = domain.lower()

    name_in_content = name_lower in content_lower
    slug_in_domain = slug in domain_lower.split(".")[0]

    count = content_lower.count(name_lower)

    if slug_in_domain and name_in_content and count >= 3:
        return "high"
    if name_in_content and count >= 2:
        return "medium"
    if name_in_content:
        return "low"
    return "no match"


def source_and_extract_candidates(queries: list) -> list:
    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))

    raw_results = []
    for query in queries:
        try:
            resp = tavily.search(query=query, max_results=5)
            for item in resp.get("results", []):
                raw_results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", "")[:600],
                    "url": item.get("url", ""),
                })
        except Exception:
            continue

    prompt = f"""You are a data extraction assistant. From the search result titles and snippets below, extract every distinct company that could plausibly be a B2B SaaS startup.

Search results:
{json.dumps(raw_results, indent=2)}

Return ONLY a raw JSON array where each element has exactly these keys:
- company_name: string
- domain_hint: string (the company domain if it appears in the text or URL, otherwise null)

Deduplicate by company name (case-insensitive). No markdown, no code fences."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    candidates = _parse_json(response.content[0].text)

    seen = set()
    deduped = []
    for c in candidates:
        key = c.get("company_name", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    return deduped


def prefilter_candidates(candidates: list) -> list:
    profile = get_active_profile()
    firmographic = profile["firmographic"]
    verticals = ", ".join(firmographic.get("verticals", []))
    arr_range = firmographic.get("arr_range", "")
    funding_stage = firmographic.get("funding_stage", "")
    personas = ", ".join(profile.get("personas", []))

    negative_icp = profile.get("negative_icp", {})
    exclude_verticals = ", ".join(negative_icp.get("exclude_verticals", [])) or "none"
    exclude_stages = ", ".join(negative_icp.get("exclude_stages", [])) or "none"
    exclude_descriptors = ", ".join(negative_icp.get("exclude_descriptors", [])) or "none"

    prompt = f"""You are a B2B SaaS go-to-market analyst. Filter the following list of candidate companies against this Ideal Customer Profile and remove obvious non-fits.

ICP:
- Stage: {funding_stage}
- Verticals: {verticals}
- ARR range: {arr_range}
- Target personas: {personas}

Remove any company that is clearly:
- A large public company or enterprise (Fortune 500, publicly traded)
- A consumer product with no B2B SaaS angle
- A non-software business (agency, hardware, marketplace, media)
- A VC firm, accelerator, or investor (not an operating company)
- A well-known, household-name company that is obviously well past the {funding_stage} stage and a {arr_range} ARR profile (for example Salesforce, HubSpot, Stripe, Slack, Notion, Figma, GitHub, Snowflake, Databricks, Canva, Zoom, or any similarly large and mature company)

NEGATIVE ICP DISQUALIFIERS (drop any candidate that clearly matches one of these):
- Excluded verticals: {exclude_verticals}
- Excluded stages: {exclude_stages}
- Excluded descriptors: {exclude_descriptors}

When in doubt about size or stage, keep the candidate. Only drop companies where it is obvious they do not fit.

Candidates:
{json.dumps(candidates, indent=2)}

Return ONLY a raw JSON array of the companies that pass the filter, preserving the company_name and domain_hint fields exactly. No markdown, no code fences."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_json(response.content[0].text)


def discover(focus: str = None, limit: int = 5) -> dict:
    from src.agent import run_research

    queries = generate_discovery_queries(focus)
    candidates = source_and_extract_candidates(queries)
    filtered = prefilter_candidates(candidates)

    qualified = []
    skipped = []

    for candidate in filtered:
        if len(qualified) >= limit:
            break

        company_name = candidate.get("company_name", "").strip()
        domain_hint = candidate.get("domain_hint")

        if not company_name:
            continue

        resolved = resolve_domain(company_name, domain_hint)
        if not resolved:
            skipped.append({"company_name": company_name, "reason": "no domain resolved"})
            continue

        domain = resolved["domain"]
        page_content = resolved["content"]

        try:
            match_confidence = verify_company_match(company_name, domain, page_content)
            print(f"Verify {company_name}: {match_confidence}")
        except Exception as e:
            match_confidence = "unknown"
            print(f"Verify {company_name}: error ({e})")

        if match_confidence == "no match":
            skipped.append({"company_name": company_name, "domain": domain, "reason": "verification: no match"})
            continue

        if match_confidence == "low":
            skipped.append({"company_name": company_name, "domain": domain, "reason": f"low match confidence: {domain}"})
            continue

        try:
            result = run_research(company_name, domain)
            icp_score = result.get("icp_score")
            icp_tier = result.get("icp_tier")
            qualified.append({
                "company_name": company_name,
                "domain": domain,
                "icp_score": icp_score,
                "icp_tier": icp_tier,
                "match_confidence": match_confidence,
            })
            print(f"Qualified {company_name}: {icp_score} ({icp_tier})")
        except Exception as e:
            skipped.append({"company_name": company_name, "domain": domain, "reason": str(e)})

    qualified.sort(key=lambda r: (r.get("icp_score") or 0), reverse=True)

    return {"qualified": qualified, "skipped": skipped, "queries": queries}


def mock_discover(focus: str = None, limit: int = 5) -> dict:
    all_qualified = [
        {
            "company_name": "Rootly",
            "domain": "rootly.com",
            "icp_score": 94,
            "icp_tier": "A+",
            "match_confidence": "high",
        },
        {
            "company_name": "Synder",
            "domain": "synder.com",
            "icp_score": 81,
            "icp_tier": "A",
            "match_confidence": "high",
        },
        {
            "company_name": "Kindo",
            "domain": "kindo.ai",
            "icp_score": 76,
            "icp_tier": "A",
            "match_confidence": "medium",
        },
        {
            "company_name": "Numra",
            "domain": "numra.io",
            "icp_score": 61,
            "icp_tier": "B",
            "match_confidence": "medium",
        },
        {
            "company_name": "Vaultree",
            "domain": "vaultree.com",
            "icp_score": 55,
            "icp_tier": "B",
            "match_confidence": "high",
        },
    ]
    skipped = [
        {
            "company_name": "DataBrew",
            "domain": "databrew.app",
            "reason": "low match confidence: databrew.app",
        },
    ]
    queries = [
        "\"Series A\" B2B SaaS startup 2024 funding announcement",
        "small Series A fintech startup site:techcrunch.com 2024",
        "\"$5 million Series A\" B2B SaaS 2025",
    ]
    return {
        "qualified": all_qualified[:limit],
        "skipped": skipped,
        "queries": queries,
    }
