import json
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def _get_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)


def save_account(data: dict) -> str:
    client = _get_client()

    row = {
        "company_name": data.get("company_name"),
        "domain": data.get("domain"),
        "homepage_content": data.get("homepage_content"),
        "icp_signals": data.get("icp_signals"),
        "pain_points": data.get("pain_points"),
        "tech_stack_signals": data.get("tech_stack_signals"),
        "recommended_angle": data.get("recommended_angle"),
        "icp_tier": data.get("icp_tier"),
        "summary": data.get("summary"),
        "raw_brief": json.dumps(data),
    }

    response = client.table("accounts").insert(row).execute()
    return response.data[0]["id"]


def get_all_accounts() -> list:
    client = _get_client()

    response = (
        client.table("accounts")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data
