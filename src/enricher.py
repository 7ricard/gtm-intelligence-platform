import json
import os
import re

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

WIKIDATA_USER_AGENT = "GTMIntelligencePlatform/1.0 (https://github.com/your-org/gtm-intelligence-platform)"
SEC_USER_AGENT = "GTMIntelligencePlatform your-email@example.com"


def get_wikidata_data(company_name: str, domain: str) -> dict:
    empty = {"found": False}
    try:
        search_url = "https://www.wikidata.org/w/api.php"
        search_params = {
            "action": "wbsearchentities",
            "search": company_name,
            "language": "en",
            "format": "json",
            "limit": 5,
        }
        headers = {"User-Agent": WIKIDATA_USER_AGENT}
        resp = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        resp.raise_for_status()
        candidates = resp.json().get("search", [])

        if not candidates:
            print("Wikidata: no match")
            return empty

        chosen_entity = None
        chosen_qid = None
        confidence = "low"

        for candidate in candidates:
            qid = candidate.get("id", "")
            try:
                entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
                entity_resp = requests.get(entity_url, headers=headers, timeout=10)
                entity_resp.raise_for_status()
                entity_data = entity_resp.json().get("entities", {}).get(qid, {})
                claims = entity_data.get("claims", {})

                websites = claims.get("P856", [])
                for w in websites:
                    url_val = (
                        w.get("mainsnak", {})
                        .get("datavalue", {})
                        .get("value", "")
                    )
                    if domain.lower().rstrip("/") in url_val.lower():
                        chosen_entity = entity_data
                        chosen_qid = qid
                        confidence = "high"
                        break

                if chosen_entity:
                    break
            except Exception:
                continue

        if not chosen_entity:
            qid = candidates[0].get("id", "")
            try:
                entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
                entity_resp = requests.get(entity_url, headers=headers, timeout=10)
                entity_resp.raise_for_status()
                chosen_entity = entity_resp.json().get("entities", {}).get(qid, {})
                chosen_qid = qid
                confidence = "low"
            except Exception:
                print("Wikidata: no match")
                return empty

        claims = chosen_entity.get("claims", {})

        def get_string_value(prop):
            entries = claims.get(prop, [])
            if not entries:
                return None
            return (
                entries[0]
                .get("mainsnak", {})
                .get("datavalue", {})
                .get("value", None)
            )

        def get_time_value(prop):
            val = get_string_value(prop)
            if isinstance(val, dict):
                return val.get("time", "")[1:5] or None
            return None

        def get_quantity_value(prop):
            val = get_string_value(prop)
            if isinstance(val, dict):
                return val.get("amount", None)
            return None

        def get_entity_labels(prop):
            entries = claims.get(prop, [])
            labels = []
            for entry in entries:
                val = entry.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if isinstance(val, dict):
                    qid_ref = val.get("id", "")
                    label = val.get("id", "")
                    try:
                        label_resp = requests.get(
                            "https://www.wikidata.org/w/api.php",
                            params={"action": "wbgetentities", "ids": qid_ref, "props": "labels", "languages": "en", "format": "json"},
                            headers=headers,
                            timeout=8,
                        )
                        label_resp.raise_for_status()
                        label = (
                            label_resp.json()
                            .get("entities", {})
                            .get(qid_ref, {})
                            .get("labels", {})
                            .get("en", {})
                            .get("value", qid_ref)
                        )
                    except Exception:
                        pass
                    labels.append(label)
            return labels or None

        founded_year = get_time_value("P571")
        employees = get_quantity_value("P1128")

        hq_entries = claims.get("P159", [])
        hq = None
        if hq_entries:
            hq_val = (
                hq_entries[0]
                .get("mainsnak", {})
                .get("datavalue", {})
                .get("value", {})
            )
            if isinstance(hq_val, dict):
                hq_qid = hq_val.get("id", "")
                try:
                    hq_resp = requests.get(
                        "https://www.wikidata.org/w/api.php",
                        params={"action": "wbgetentities", "ids": hq_qid, "props": "labels", "languages": "en", "format": "json"},
                        headers=headers,
                        timeout=8,
                    )
                    hq_resp.raise_for_status()
                    hq = (
                        hq_resp.json()
                        .get("entities", {})
                        .get(hq_qid, {})
                        .get("labels", {})
                        .get("en", {})
                        .get("value", hq_qid)
                    )
                except Exception:
                    hq = hq_qid

        founders = get_entity_labels("P112")
        industry = get_entity_labels("P452")

        name_label = (
            chosen_entity.get("labels", {}).get("en", {}).get("value", company_name)
        )
        print(f"Wikidata: found {name_label}")

        return {
            "found": True,
            "founded_year": founded_year,
            "hq": hq,
            "employees": employees,
            "founders": founders,
            "industry": industry,
            "confidence": confidence,
            "source": f"https://www.wikidata.org/wiki/{chosen_qid}",
        }

    except Exception as e:
        print(f"Wikidata: no match ({e})")
        return empty


def get_sec_data(company_name: str) -> dict:
    try:
        print("SEC: fetching company tickers...")
        headers = {"User-Agent": SEC_USER_AGENT}
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        tickers = resp.json()

        name_lower = company_name.lower()
        match = None
        for entry in tickers.values():
            if name_lower in entry.get("title", "").lower():
                match = entry
                break

        if not match:
            print("SEC: private / not found")
            return {"public": False}

        cik = match["cik_str"]
        matched_title = match["title"]
        result = {"public": True, "cik": cik, "matched_title": matched_title}

        try:
            cik_padded = str(cik).zfill(10)
            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
            facts_resp = requests.get(facts_url, headers=headers, timeout=15)
            facts_resp.raise_for_status()
            facts = facts_resp.json()

            revenues = (
                facts.get("facts", {})
                .get("us-gaap", {})
                .get("Revenues", {})
                .get("units", {})
                .get("USD", [])
            )
            if not revenues:
                revenues = (
                    facts.get("facts", {})
                    .get("us-gaap", {})
                    .get("RevenueFromContractWithCustomerExcludingAssessedTax", {})
                    .get("units", {})
                    .get("USD", [])
                )

            annual = [r for r in revenues if r.get("form") in ("10-K", "20-F") and r.get("fp") == "FY"]
            if annual:
                latest = sorted(annual, key=lambda r: r.get("end", ""))[-1]
                result["latest_annual_revenue_usd"] = latest.get("val")
                result["revenue_period_end"] = latest.get("end")
        except Exception:
            pass

        print(f"SEC: public ({matched_title})")
        return result

    except Exception as e:
        print(f"SEC: private / not found ({e})")
        return {"public": False}


def get_tavily_evidence(company_name: str, domain: str) -> dict:
    try:
        api_key = os.environ.get("TAVILY_API_KEY", "")
        client = TavilyClient(api_key=api_key)

        queries = [
            f"{company_name} funding round investors",
            f"{company_name} revenue ARR employees",
            f"{company_name} CEO founder leadership",
        ]

        all_answers = []
        all_results = []

        for query in queries:
            try:
                response = client.search(
                    query=query,
                    include_answer=True,
                    max_results=4,
                )
                answer = response.get("answer", "")
                if answer:
                    all_answers.append(answer)
                for item in response.get("results", []):
                    all_results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                    })
            except Exception:
                continue

        print(f"Tavily: {len(all_results)} results across {len(queries)} queries")
        return {
            "queries": queries,
            "answers": all_answers,
            "results": all_results,
        }

    except Exception as e:
        print(f"Tavily: error ({e})")
        return {"queries": [], "answers": [], "results": []}


def reconcile_evidence(
    company_name: str,
    domain: str,
    wikidata: dict,
    sec: dict,
    tavily: dict,
) -> dict:
    load_dotenv()
    client = Anthropic()

    trimmed_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:500],
        }
        for r in tavily.get("results", [])
    ]

    prompt = f"""You are a senior B2B SaaS market analyst. Reconcile the following evidence about a company into a single confirmed enrichment record.

COMPANY
Name: {company_name}
Domain: {domain}

WIKIDATA
{json.dumps(wikidata, indent=2)}

SEC EDGAR
{json.dumps(sec, indent=2)}

TAVILY ANSWERS
{json.dumps(tavily.get("answers", []), indent=2)}

TAVILY SNIPPETS (trimmed to 500 chars each)
{json.dumps(trimmed_results, indent=2)}

INSTRUCTIONS
Return a single JSON object with exactly these keys:
- funding_stage: string (e.g. "Series A", "Seed", "Public", "unknown")
- total_funding_raised: string (e.g. "$12M", "unknown")
- last_round: string (e.g. "Series B, $20M, Jan 2024", "unknown")
- revenue_or_arr_estimate: string (e.g. "$5M ARR", "unknown")
- employee_count: string (e.g. "120", "50 to 200", "unknown")
- founded_year: string (e.g. "2019", "unknown")
- hq_location: string (e.g. "San Francisco, CA", "unknown")
- recent_signals: array of strings (notable hiring moves, product launches, press, or funding news)
- target_personas_found: array of strings (named executives or roles visible in the evidence)
- sources: array of URLs that directly backed the facts above
- confidence: string, "high", "medium", or "low", followed by a comma and a one-line reason

Rules:
- Only assert facts that are supported by the evidence above.
- If a field is unknown, set it to "unknown".
- When sources conflict, prefer the most recent and most credible source, and note the uncertainty in the relevant field value.
- Do not use em dashes anywhere in any value.
- Return ONLY raw JSON with no markdown and no code fences."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": text}


def enrich_account(company_name: str, domain: str) -> dict:
    try:
        wikidata = get_wikidata_data(company_name, domain)
    except Exception:
        wikidata = {"found": False}

    try:
        sec = get_sec_data(company_name)
    except Exception:
        sec = {"public": False}

    try:
        tavily = get_tavily_evidence(company_name, domain)
    except Exception:
        tavily = {"queries": [], "answers": [], "results": []}

    return reconcile_evidence(company_name, domain, wikidata, sec, tavily)
