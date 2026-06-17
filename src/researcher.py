import json
import re

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

SYSTEM_PROMPT = (
    "You are a senior B2B SaaS go-to-market analyst. You specialize in "
    "researching companies and turning raw website content into sharp, "
    "actionable account intelligence for sales and marketing teams."
)


def research_account(company_name: str, domain: str, content: str) -> dict:
    user_message = f"""Analyze the following company and produce account intelligence for outbound GTM efforts.

Company name: {company_name}
Domain: {domain}

Scraped website content:
{content}

Return a single JSON object with exactly these keys:
- icp_signals: array of strings (company size, industry, growth stage, buying signals)
- pain_points: array of strings (likely business problems given their model and stage)
- tech_stack_signals: array of strings (tools or platforms they likely use)
- recommended_angle: string, one paragraph, the strongest outbound hook
- icp_tier: string, exactly "A", "B", or "C"
- summary: string, 2 to 3 sentences

For "recommended_angle" and "summary", never use em dashes; use commas, periods, or parentheses instead.

Return ONLY raw JSON. No markdown, no code fences, no commentary."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
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
