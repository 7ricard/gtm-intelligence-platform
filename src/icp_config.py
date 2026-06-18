# Ideal Customer Profile definition. Edit this file to retarget the scoring engine.

ICP = {
    "definition": "Series A B2B SaaS companies with $2M to $10M ARR.",
    "target_arr": "$2M to $10M",
    "target_stage": "Series A",
    "target_vertical": "B2B SaaS",
    "target_personas_in_priority_order": [
        "Founder",
        "CEO",
        "CRO",
        "Head of GTM",
        "VP of Sales",
    ],
}

# Scoring weights across six dimensions. All values must sum to 100.
WEIGHTS = {
    "firmographic_fit": 20,       # Company size and ARR match the ICP definition
    "buying_signals": 20,         # Evidence of active growth, hiring, or tooling investment
    "funding_stage": 15,          # Funding round aligns with target stage (Series A)
    "industry_fit": 15,           # Vertical matches B2B SaaS focus
    "technographic_fit": 15,      # Tech stack suggests compatibility with our solution
    "persona_accessibility": 15,  # Target personas are reachable and visible at the company
}

# Tier thresholds (inclusive lower bounds).
# A+ is 90 or higher, A is 75 to 89, B is 50 to 74, C is below 50.
THRESHOLDS = {"A+": 90, "A": 75, "B": 50}
