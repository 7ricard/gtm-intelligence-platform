import json
import re

from dotenv import load_dotenv
from anthropic import Anthropic

from src.profiles import get_active_profile

load_dotenv()

client = Anthropic()


def _build_enrichment_block(enrichment: dict, profile: dict) -> str:
    if not enrichment or "error" in enrichment:
        return ""

    def val(key):
        v = enrichment.get(key, "unknown")
        return v if v else "unknown"

    personas_found = enrichment.get("target_personas_found") or []
    recent_signals = enrichment.get("recent_signals") or []

    arr_range = profile["firmographic"].get("arr_range", "")
    funding_stage = profile["firmographic"].get("funding_stage", "")
    personas_list = ", ".join(profile.get("personas", []))

    lines = [
        "CONFIRMED ENRICHMENT DATA (authoritative; takes priority over website inference)",
        f"Funding stage: {val('funding_stage')}",
        f"Total funding raised: {val('total_funding_raised')}",
        f"Last round: {val('last_round')}",
        f"Revenue or ARR estimate: {val('revenue_or_arr_estimate')}",
        f"Employee count: {val('employee_count')}",
        f"Founded year: {val('founded_year')}",
        f"HQ location: {val('hq_location')}",
        f"Target personas found: {', '.join(personas_found) if personas_found else 'none identified'}",
        f"Recent signals: {'; '.join(recent_signals) if recent_signals else 'none'}",
        f"Data confidence: {val('confidence')}",
        "",
        "Scoring notes for enrichment-backed dimensions:",
        f"- firmographic_fit: use revenue_or_arr_estimate and employee_count against the {arr_range} ARR target; fall back to brief inference only where enrichment is 'unknown'.",
        f"- funding_stage: use the confirmed funding_stage against the {funding_stage} target; fall back to brief inference only where enrichment is 'unknown'.",
        f"- persona_accessibility: use target_personas_found; score higher when named buyers match {personas_list}; fall back to brief inference only where enrichment is 'unknown'.",
    ]
    return "\n".join(lines)


def score_account(brief: dict, enrichment: dict = None) -> dict:
    profile = get_active_profile()
    weights = profile["weights"]
    thresholds = profile["thresholds"]

    firmographic = profile["firmographic"]
    verticals = ", ".join(firmographic.get("verticals", []))
    arr_range = firmographic.get("arr_range", "")
    funding_stage = firmographic.get("funding_stage", "")
    business_model = firmographic.get("business_model", "")
    geographies = ", ".join(firmographic.get("geographies", [])) or "any"
    employee_range = firmographic.get("employee_range", "") or "not specified"

    technographic = profile["technographic"]
    target_stack = ", ".join(technographic.get("target_stack", [])) or "none specified"
    competitors = ", ".join(technographic.get("competitors_to_displace", [])) or "none specified"

    personas = ", ".join(profile.get("personas", []))
    positive_signals = ", ".join(profile.get("positive_signals", []))

    negative_icp = profile.get("negative_icp", {})
    exclude_verticals = ", ".join(negative_icp.get("exclude_verticals", [])) or "none"
    exclude_stages = ", ".join(negative_icp.get("exclude_stages", [])) or "none"
    exclude_descriptors = ", ".join(negative_icp.get("exclude_descriptors", [])) or "none"

    enrichment_block = _build_enrichment_block(enrichment, profile)

    prompt = f"""You are a senior B2B SaaS go-to-market analyst. Score the following account against the Ideal Customer Profile (ICP) rubric below.

ICP DEFINITION
Verticals: {verticals}
Business model: {business_model}
Target ARR: {arr_range}
Target Stage: {funding_stage}
Geographies: {geographies}
Employee range: {employee_range}
Target Personas (in priority order): {personas}
Positive signals: {positive_signals}
Target stack: {target_stack}
Competitors to displace: {competitors}

NEGATIVE ICP DISQUALIFIERS
Excluded verticals: {exclude_verticals}
Excluded stages: {exclude_stages}
Excluded descriptors: {exclude_descriptors}

If the account clearly matches any disqualifier above, heavily penalize firmographic_fit (score it 10 or below) and note the specific disqualifier in that dimension's rationale.

ACCOUNT BRIEF
Summary: {brief.get("summary", "")}
ICP Signals: {brief.get("icp_signals", [])}
Pain Points: {brief.get("pain_points", [])}
Tech Stack Signals: {brief.get("tech_stack_signals", [])}

{enrichment_block + chr(10) if enrichment_block else ""}SCORING TASK
Score each of the following six dimensions from 0 to 100 based on how well the account matches the ICP. Where confirmed enrichment data is provided above, use it as the primary source for the relevant dimensions and fall back to brief inference only for fields marked "unknown". Where no enrichment is available, use only evidence present in the brief and score conservatively where data is missing.

Dimensions to score:
- firmographic_fit: Company size and ARR match the ICP definition
- buying_signals: Evidence of active growth, hiring, or tooling investment
- funding_stage: Funding round aligns with the target stage ({funding_stage})
- industry_fit: Vertical matches {verticals} focus
- technographic_fit: Tech stack suggests compatibility with our solution
- persona_accessibility: Target personas are reachable and visible at the company

For each dimension, write a one-sentence rationale. Do not use em dashes in any rationale.

Return ONLY raw JSON with no markdown and no code fences, mapping each dimension name to an object with exactly these keys:
{{"score": <integer 0 to 100>, "rationale": <string>}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    try:
        scores = json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
        try:
            scores = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": text}

    breakdown = []
    total = 0.0

    for dimension, weight in weights.items():
        entry = scores.get(dimension, {})
        score = int(entry.get("score", 0))
        rationale = entry.get("rationale", "")
        contribution = score * weight / 100
        total += contribution
        breakdown.append({
            "dimension": dimension,
            "score": score,
            "weight": weight,
            "contribution": round(contribution, 2),
            "rationale": rationale,
        })

    overall = round(total)

    if overall >= thresholds["A+"]:
        tier = "A+"
    elif overall >= thresholds["A"]:
        tier = "A"
    elif overall >= thresholds["B"]:
        tier = "B"
    else:
        tier = "C"

    return {
        "icp_score": overall,
        "icp_tier": tier,
        "breakdown": breakdown,
    }
