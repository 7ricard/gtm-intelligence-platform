import json
import re

from dotenv import load_dotenv
from anthropic import Anthropic

from src.icp_config import ICP, WEIGHTS, THRESHOLDS

load_dotenv()

client = Anthropic()


def score_account(brief: dict) -> dict:
    personas = ", ".join(ICP["target_personas_in_priority_order"])

    prompt = f"""You are a senior B2B SaaS go-to-market analyst. Score the following account against the Ideal Customer Profile (ICP) rubric below.

ICP DEFINITION
Definition: {ICP["definition"]}
Target ARR: {ICP["target_arr"]}
Target Stage: {ICP["target_stage"]}
Target Vertical: {ICP["target_vertical"]}
Target Personas (in priority order): {personas}

ACCOUNT BRIEF
Summary: {brief.get("summary", "")}
ICP Signals: {brief.get("icp_signals", [])}
Pain Points: {brief.get("pain_points", [])}
Tech Stack Signals: {brief.get("tech_stack_signals", [])}

SCORING TASK
Score each of the following six dimensions from 0 to 100 based on how well the account matches the ICP. Use only evidence present in the brief. Where data is missing, score conservatively and state that in the rationale.

Dimensions to score:
- firmographic_fit: Company size and ARR match the ICP definition
- buying_signals: Evidence of active growth, hiring, or tooling investment
- funding_stage: Funding round aligns with the target stage (Series A)
- industry_fit: Vertical matches B2B SaaS focus
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

    for dimension, weight in WEIGHTS.items():
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

    if overall >= THRESHOLDS["A+"]:
        tier = "A+"
    elif overall >= THRESHOLDS["A"]:
        tier = "A"
    elif overall >= THRESHOLDS["B"]:
        tier = "B"
    else:
        tier = "C"

    return {
        "icp_score": overall,
        "icp_tier": tier,
        "breakdown": breakdown,
    }
