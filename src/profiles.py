import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DEFAULT_PROFILE = {
    "firmographic": {
        "verticals": ["B2B SaaS"],
        "arr_range": "$2M to $10M",
        "employee_range": "",
        "funding_stage": "Series A",
        "geographies": [],
        "business_model": "B2B SaaS subscription",
    },
    "technographic": {
        "target_stack": [],
        "competitors_to_displace": [],
    },
    "personas": ["Founder", "CEO", "CRO", "Head of GTM", "VP of Sales"],
    "positive_signals": [
        "recent funding round",
        "hiring for GTM or sales roles",
        "market or product expansion",
    ],
    "negative_icp": {
        "exclude_verticals": [],
        "exclude_stages": ["Series C or later", "public company"],
        "exclude_descriptors": [],
    },
    "weights": {
        "firmographic_fit": 20,
        "buying_signals": 20,
        "funding_stage": 15,
        "industry_fit": 15,
        "technographic_fit": 15,
        "persona_accessibility": 15,
    },
    "thresholds": {"A+": 90, "A": 75, "B": 50},
}


def _get_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)


def list_profiles() -> list:
    client = _get_client()
    response = (
        client.table("icp_profiles")
        .select("id, name, is_active, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_profile(profile_id: str) -> dict:
    client = _get_client()
    response = (
        client.table("icp_profiles")
        .select("*")
        .eq("id", profile_id)
        .single()
        .execute()
    )
    return response.data


def get_active_profile() -> dict:
    client = _get_client()
    response = (
        client.table("icp_profiles")
        .select("profile")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]["profile"]
    return DEFAULT_PROFILE


def save_profile(name: str, profile: dict, profile_id: str = None) -> str:
    client = _get_client()
    if profile_id:
        response = (
            client.table("icp_profiles")
            .update({"name": name, "profile": profile, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", profile_id)
            .execute()
        )
        return response.data[0]["id"]
    else:
        response = (
            client.table("icp_profiles")
            .insert({"name": name, "profile": profile})
            .execute()
        )
        return response.data[0]["id"]


def set_active(profile_id: str):
    client = _get_client()
    client.table("icp_profiles").update({"is_active": False}).eq("is_active", True).execute()
    client.table("icp_profiles").update({"is_active": True}).eq("id", profile_id).execute()


def seed_default_profile() -> str:
    client = _get_client()
    existing = client.table("icp_profiles").select("id").limit(1).execute()
    if existing.data:
        return None
    response = (
        client.table("icp_profiles")
        .insert({"name": "Series A B2B SaaS", "profile": DEFAULT_PROFILE, "is_active": True})
        .execute()
    )
    return response.data[0]["id"]
