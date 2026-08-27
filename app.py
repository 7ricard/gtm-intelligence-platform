import ast

import streamlit as st

from src.agent import run_research
from src.database import get_all_accounts
from src.profiles import (
    list_profiles,
    get_profile,
    get_active_profile,
    save_profile,
    set_active,
    seed_default_profile,
)


def esc(text):
    return str(text).replace("$", "\\$")


def clean_text_field(value):
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = ast.literal_eval(stripped)
            except (ValueError, SyntaxError):
                parsed = stripped[1:-1].strip()
                if len(parsed) >= 2 and parsed[0] == parsed[-1] and parsed[0] in ("'", '"'):
                    parsed = parsed[1:-1]
            value = parsed

    if isinstance(value, list):
        if len(value) == 1:
            value = value[0]
        else:
            value = " ".join(str(v) for v in value)

    return value


def _csv_input(label, value_list, key):
    current = ", ".join(value_list) if value_list else ""
    raw = st.text_input(label, value=current, key=key, autocomplete="off")
    return [v.strip() for v in raw.split(",") if v.strip()]


def badge(text, bg, fg="#ffffff", font_size="0.95rem", padding="0.15rem 0.65rem"):
    return (
        f"<span style='background-color:{bg}; color:{fg}; padding:{padding}; "
        f"border-radius:999px; font-weight:600; font-size:{font_size}; "
        f"display:inline-block; line-height:1.5;'>{text}</span>"
    )


def spacer(px=16):
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


def muted_label(text):
    st.markdown(f"<div class='muted-label'>{text}</div>", unsafe_allow_html=True)


def score_bar(score):
    try:
        pct = max(0, min(100, float(score)))
    except (TypeError, ValueError):
        pct = 0
    if pct >= 80:
        color = "#4caf50"
    elif pct >= 50:
        color = "#ff9800"
    else:
        color = "#e0796b"
    return (
        f"<div class='score-bar-track'>"
        f"<div class='score-bar-fill' style='width:{pct}%; background-color:{color};'></div>"
        f"</div>"
    )


TIER_COLORS = {
    "A+": {"bg": "#00753a", "fg": "#ffffff"},
    "A": {"bg": "#4caf50", "fg": "#ffffff"},
    "B": {"bg": "#ff9800", "fg": "#3a2300"},
    "C": {"bg": "#e0796b", "fg": "#ffffff"},
}
CONF_COLORS = {
    "high": {"bg": "#4caf50", "fg": "#ffffff"},
    "medium": {"bg": "#ff9800", "fg": "#3a2300"},
    "low": {"bg": "#e0796b", "fg": "#ffffff"},
}
_DEFAULT_BADGE = {"bg": "#9e9e9e", "fg": "#ffffff"}

st.set_page_config(page_title="GTM Intelligence Platform", layout="wide")
st.title("GTM Intelligence Platform")

st.markdown(
    """
    <style>
    div[data-testid="stMainBlockContainer"] {
        max-width: 1150px;
        margin-left: auto;
        margin-right: auto;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 2rem;
    }

    h2, h3 {
        margin-top: 1.5rem;
        margin-bottom: 0.6rem;
    }
    h3 {
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #9aa1ac;
    }
    [data-testid="stCaptionContainer"] {
        margin-bottom: 0.75rem;
    }

    div[class*="st-key-card-"] {
        background-color: #1A1D24 !important;
        border: 1px solid rgba(250, 250, 250, 0.10) !important;
        border-radius: 10px !important;
        padding: 1.25rem !important;
        margin-bottom: 1.25rem !important;
    }

    .muted-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #9aa1ac;
        margin-bottom: 0.35rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 3rem;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #9aa1ac;
    }

    .score-bar-track {
        background-color: rgba(250, 250, 250, 0.08);
        border-radius: 999px;
        height: 8px;
        width: 100%;
        overflow: hidden;
        margin: 0.35rem 0 0.5rem 0;
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 999px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

seed_default_profile()

tab_icp, tab_research, tab_discover = st.tabs(
    ["ICP Profile", "Research a Company", "Discover Accounts"]
)

# -- TAB 1: ICP Profile -------------------------------------------------------
with tab_icp:
    all_profiles = list_profiles()

    if not all_profiles:
        st.warning("No profiles found. Reload the page.")
        st.stop()

    active_row = next((p for p in all_profiles if p.get("is_active")), all_profiles[0])
    profile_names = [p["name"] for p in all_profiles]
    active_index = next(
        (i for i, p in enumerate(all_profiles) if p.get("is_active")), 0
    )

    selected_index = st.selectbox(
        "Profile",
        range(len(all_profiles)),
        format_func=lambda i: all_profiles[i]["name"],
        index=active_index,
        key="profile_selector",
    )
    selected_meta = all_profiles[selected_index]
    selected_id = selected_meta["id"]

    is_active = selected_meta.get("is_active", False)
    if is_active:
        st.caption("This profile is currently active.")
    else:
        st.caption(f"Active profile: **{active_row['name']}**")
        if st.button("Set as Active"):
            set_active(selected_id)
            st.success(f"'{selected_meta['name']}' is now the active profile.")
            st.rerun()

    st.divider()

    full_row = get_profile(selected_id)
    p = full_row.get("profile", {})

    firm = p.get("firmographic", {})
    tech = p.get("technographic", {})
    neg = p.get("negative_icp", {})
    weights_data = p.get("weights", {})
    thresholds_data = p.get("thresholds", {})

    pid = selected_id

    st.subheader("Firmographic")
    f_verticals = _csv_input("Verticals (comma-separated)", firm.get("verticals", []), f"f_verticals_{pid}")
    f_arr_range = st.text_input("ARR Range", value=firm.get("arr_range", ""), key=f"f_arr_range_{pid}", autocomplete="off")
    f_funding_stage = st.text_input("Funding Stage", value=firm.get("funding_stage", ""), key=f"f_funding_stage_{pid}", autocomplete="off")
    f_business_model = st.text_input("Business Model", value=firm.get("business_model", ""), key=f"f_business_model_{pid}", autocomplete="off")
    f_employee_range = st.text_input("Employee Range", value=firm.get("employee_range", ""), key=f"f_employee_range_{pid}", autocomplete="off")
    f_geographies = _csv_input("Geographies (comma-separated)", firm.get("geographies", []), f"f_geographies_{pid}")

    st.subheader("Technographic")
    t_stack = _csv_input("Target Stack (comma-separated)", tech.get("target_stack", []), f"t_stack_{pid}")
    t_competitors = _csv_input("Competitors to Displace (comma-separated)", tech.get("competitors_to_displace", []), f"t_competitors_{pid}")

    st.subheader("Personas")
    personas = _csv_input("Personas in priority order (comma-separated)", p.get("personas", []), f"personas_{pid}")

    st.subheader("Positive Signals")
    positive_signals = _csv_input("Positive Signals (comma-separated)", p.get("positive_signals", []), f"positive_signals_{pid}")

    st.subheader("Negative ICP")
    neg_verticals = _csv_input("Exclude Verticals (comma-separated)", neg.get("exclude_verticals", []), f"neg_verticals_{pid}")
    neg_stages = _csv_input("Exclude Stages (comma-separated)", neg.get("exclude_stages", []), f"neg_stages_{pid}")
    neg_descriptors = _csv_input("Exclude Descriptors (comma-separated)", neg.get("exclude_descriptors", []), f"neg_descriptors_{pid}")

    st.subheader("Weights (must total 100)")
    with st.container(border=True, key="card-weights"):
        w_firmographic = st.number_input("firmographic_fit", min_value=0, max_value=100, value=int(weights_data.get("firmographic_fit", 20)), step=1, key=f"w_firmographic_{pid}")
        w_buying = st.number_input("buying_signals", min_value=0, max_value=100, value=int(weights_data.get("buying_signals", 20)), step=1, key=f"w_buying_{pid}")
        w_funding = st.number_input("funding_stage", min_value=0, max_value=100, value=int(weights_data.get("funding_stage", 15)), step=1, key=f"w_funding_{pid}")
        w_industry = st.number_input("industry_fit", min_value=0, max_value=100, value=int(weights_data.get("industry_fit", 15)), step=1, key=f"w_industry_{pid}")
        w_techno = st.number_input("technographic_fit", min_value=0, max_value=100, value=int(weights_data.get("technographic_fit", 15)), step=1, key=f"w_techno_{pid}")
        w_persona = st.number_input("persona_accessibility", min_value=0, max_value=100, value=int(weights_data.get("persona_accessibility", 15)), step=1, key=f"w_persona_{pid}")

        weight_sum = w_firmographic + w_buying + w_funding + w_industry + w_techno + w_persona
        sum_color = "#4caf50" if weight_sum == 100 else "#c62828"
        st.markdown(
            f"<div style='margin-top:0.5rem; font-size:1.35rem; font-weight:700; "
            f"color:{sum_color};'>Weights sum: {weight_sum} / 100</div>",
            unsafe_allow_html=True,
        )
        if weight_sum != 100:
            st.caption("Weights must total exactly 100 to save.")

    st.subheader("Thresholds")
    t_aplus = st.number_input("A+ threshold", min_value=0, max_value=100, value=int(thresholds_data.get("A+", 90)), step=1, key=f"t_aplus_{pid}")
    t_a = st.number_input("A threshold", min_value=0, max_value=100, value=int(thresholds_data.get("A", 75)), step=1, key=f"t_a_{pid}")
    t_b = st.number_input("B threshold", min_value=0, max_value=100, value=int(thresholds_data.get("B", 50)), step=1, key=f"t_b_{pid}")

    st.divider()
    new_profile_name = st.text_input("New profile name (for Save as New)", key="new_profile_name", autocomplete="off")

    save_col, saveas_col = st.columns(2)
    with save_col:
        save_btn = st.button(
            "Save Changes",
            disabled=(weight_sum != 100),
            key="save_changes_btn",
        )
    with saveas_col:
        saveas_btn = st.button(
            "Save as New Profile",
            disabled=(weight_sum != 100),
            key="save_as_new_btn",
        )

    if save_btn or saveas_btn:
        updated_profile = {
            "firmographic": {
                "verticals": f_verticals,
                "arr_range": f_arr_range,
                "funding_stage": f_funding_stage,
                "business_model": f_business_model,
                "employee_range": f_employee_range,
                "geographies": f_geographies,
            },
            "technographic": {
                "target_stack": t_stack,
                "competitors_to_displace": t_competitors,
            },
            "personas": personas,
            "positive_signals": positive_signals,
            "negative_icp": {
                "exclude_verticals": neg_verticals,
                "exclude_stages": neg_stages,
                "exclude_descriptors": neg_descriptors,
            },
            "weights": {
                "firmographic_fit": w_firmographic,
                "buying_signals": w_buying,
                "funding_stage": w_funding,
                "industry_fit": w_industry,
                "technographic_fit": w_techno,
                "persona_accessibility": w_persona,
            },
            "thresholds": {"A+": t_aplus, "A": t_a, "B": t_b},
        }

        if save_btn:
            save_profile(selected_meta["name"], updated_profile, profile_id=selected_id)
            st.success("Profile updated.")
        else:
            if not new_profile_name.strip():
                st.error("Enter a name for the new profile.")
            else:
                new_id = save_profile(new_profile_name.strip(), updated_profile)
                st.success(f"Saved as new profile '{new_profile_name.strip()}' (id: {new_id}).")
                st.rerun()

# -- TAB 2: Research a Company ------------------------------------------------
with tab_research:
    active_profile_name = get_active_profile().get("firmographic", {}).get("funding_stage", "")
    active_row_name = next((p["name"] for p in list_profiles() if p.get("is_active")), "default")
    st.caption(f"Scoring against active profile: **{active_row_name}**")

    with st.form("research_form"):
        company_name = st.text_input("Company Name", autocomplete="off")
        domain = st.text_input("Domain", placeholder="stripe.com", autocomplete="off")
        submitted = st.form_submit_button("Research Account")

    if submitted:
        if not company_name or not domain:
            st.error("Both Company Name and Domain are required.")
        else:
            with st.spinner("Researching..."):
                brief = run_research(company_name, domain)

            spacer(20)

            tier = brief.get("icp_tier", "")
            tier_style = TIER_COLORS.get(tier, _DEFAULT_BADGE)

            with st.container(border=True, key="card-score"):
                score_col, tier_col = st.columns([2, 1])
                with score_col:
                    st.metric("ICP Score", brief.get("icp_score", ""))
                with tier_col:
                    muted_label("ICP Tier")
                    st.markdown(
                        badge(tier, tier_style["bg"], tier_style["fg"], font_size="1.3rem", padding="0.3rem 1rem"),
                        unsafe_allow_html=True,
                    )

            with st.container(border=True, key="card-summary"):
                muted_label("Summary")
                st.write(esc(brief.get("summary", "")))

            with st.container(border=True, key="card-signals"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    muted_label("ICP Signals")
                    for item in brief.get("icp_signals", []):
                        st.markdown(f"- {esc(item)}")
                with col2:
                    muted_label("Pain Points")
                    for item in brief.get("pain_points", []):
                        st.markdown(f"- {esc(item)}")
                with col3:
                    muted_label("Tech Stack Signals")
                    for item in brief.get("tech_stack_signals", []):
                        st.markdown(f"- {esc(item)}")

            st.info(esc(clean_text_field(brief.get("recommended_angle", ""))))

            breakdown = brief.get("score_breakdown", [])
            if breakdown:
                with st.container(border=True, key="card-breakdown"):
                    muted_label("Score Breakdown")
                    for row in breakdown:
                        dimension_label = row["dimension"].replace("_", " ").title()
                        score = row["score"]
                        st.markdown(
                            f"**{dimension_label}** | Score: {score} | Weight: {row['weight']} | Contribution: {row['contribution']}"
                        )
                        st.markdown(score_bar(score), unsafe_allow_html=True)
                        st.caption(esc(row.get("rationale", "")))

                    table_rows = [
                        {
                            "Dimension": r["dimension"].replace("_", " ").title(),
                            "Score": r["score"],
                            "Weight": r["weight"],
                            "Contribution": r["contribution"],
                            "Rationale": r.get("rationale", ""),
                        }
                        for r in breakdown
                    ]
                    st.dataframe(table_rows, width="stretch")

            with st.container(border=True, key="card-enrichment"):
                muted_label("Company Intelligence")
                enrichment = brief.get("enrichment") or {}
                if not enrichment or "error" in enrichment:
                    st.caption("Enrichment unavailable.")
                else:
                    left, right = st.columns(2)
                    with left:
                        st.markdown(f"**Funding Stage:** {esc(enrichment.get('funding_stage', 'unknown'))}")
                        st.markdown(f"**Total Funding Raised:** {esc(enrichment.get('total_funding_raised', 'unknown'))}")
                        st.markdown(f"**Last Round:** {esc(enrichment.get('last_round', 'unknown'))}")
                        st.markdown(f"**Revenue / ARR Estimate:** {esc(enrichment.get('revenue_or_arr_estimate', 'unknown'))}")
                    with right:
                        st.markdown(f"**Employee Count:** {esc(enrichment.get('employee_count', 'unknown'))}")
                        st.markdown(f"**Founded:** {esc(enrichment.get('founded_year', 'unknown'))}")
                        st.markdown(f"**HQ Location:** {esc(enrichment.get('hq_location', 'unknown'))}")
                        st.markdown(f"**Confidence:** {esc(enrichment.get('confidence', 'unknown'))}")

                    recent_signals = enrichment.get("recent_signals") or []
                    if recent_signals:
                        st.markdown("**Recent Signals**")
                        for signal in recent_signals:
                            st.markdown(f"- {esc(signal)}")

                    personas_found = enrichment.get("target_personas_found") or []
                    if personas_found:
                        st.markdown("**Buyers Identified**")
                        for persona in personas_found:
                            st.markdown(f"- {esc(persona)}")

                    sources = enrichment.get("sources") or []
                    if sources:
                        st.markdown("**Sources**")
                        for url in sources:
                            st.markdown(f"- [{url}]({url})")

            st.success(f"Account saved (id: {brief.get('saved_id')})")

    st.divider()
    st.subheader("Research History")
    history = get_all_accounts()
    if not history:
        st.caption("No accounts researched yet.")
    else:
        display_cols = ["company_name", "domain", "icp_tier", "icp_score", "created_at"]
        rows = [{col: row.get(col) for col in display_cols} for row in history]
        st.dataframe(rows, width="stretch")

# -- TAB 3: Discover Accounts -------------------------------------------------
with tab_discover:
    active_row_name_d = next((p["name"] for p in list_profiles() if p.get("is_active")), "default")
    st.caption(f"Scoring against active profile: **{active_row_name_d}**")

    focus_input = st.text_input(
        "Focus (optional)",
        placeholder="e.g. fintech, or funded in the last 6 months",
        autocomplete="off",
    )
    limit_input = st.number_input(
        "How many to qualify", min_value=1, max_value=10, value=5, step=1
    )
    test_mode = st.checkbox("Test mode (no API calls)")

    btn_col, clear_col = st.columns([2, 1])
    with btn_col:
        discover_btn = st.button("Discover Accounts")
    with clear_col:
        if "last_discovery" in st.session_state:
            if st.button("Clear results"):
                del st.session_state["last_discovery"]
                st.rerun()

    if discover_btn:
        if test_mode:
            from src.discovery import mock_discover
            result = mock_discover(focus=focus_input or None, limit=int(limit_input))
        else:
            from src.discovery import discover
            with st.spinner("Discovering accounts. This takes a couple of minutes..."):
                result = discover(focus=focus_input or None, limit=int(limit_input))
        result["profile_name"] = active_row_name_d
        result["_mock"] = test_mode
        st.session_state["last_discovery"] = result

    if "last_discovery" in st.session_state:
        spacer(20)

        result = st.session_state["last_discovery"]
        qualified = result.get("qualified", [])
        skipped = result.get("skipped", [])
        run_profile_name = result.get("profile_name", "unknown")
        is_mock = result.get("_mock", False)

        if is_mock:
            st.caption("Showing mock data. No API calls were made.")

        if not qualified:
            st.warning("No qualified accounts found. Check the skipped list below.")
        else:
            st.success(
                f"Found {len(qualified)} qualified account(s) for the '{run_profile_name}' profile. All discovered companies are saved to the accounts database."
            )
            if run_profile_name != active_row_name_d:
                st.caption(
                    f"Note: the active profile is now '{active_row_name_d}'. Run discovery again to score against it."
                )

            with st.container(border=True, key="card-results"):
                header_cols = st.columns([1, 1, 3, 3, 2])
                header_cols[0].markdown("<div class='muted-label'>Tier</div>", unsafe_allow_html=True)
                header_cols[1].markdown("<div class='muted-label'>ICP Score</div>", unsafe_allow_html=True)
                header_cols[2].markdown("<div class='muted-label'>Company</div>", unsafe_allow_html=True)
                header_cols[3].markdown("<div class='muted-label'>Domain</div>", unsafe_allow_html=True)
                header_cols[4].markdown("<div class='muted-label'>Match Confidence</div>", unsafe_allow_html=True)

                st.divider()

                for row in qualified:
                    tier = row.get("icp_tier", "")
                    score = row.get("icp_score", "")
                    company = esc(row.get("company_name", ""))
                    domain = row.get("domain", "")
                    conf = row.get("match_confidence", "")

                    tier_style = TIER_COLORS.get(tier, _DEFAULT_BADGE)
                    conf_style = CONF_COLORS.get(conf, _DEFAULT_BADGE)

                    row_cols = st.columns([1, 1, 3, 3, 2])
                    row_cols[0].markdown(
                        badge(tier, tier_style["bg"], tier_style["fg"]),
                        unsafe_allow_html=True,
                    )
                    row_cols[1].markdown(
                        f"<span style='font-weight:700; font-size:1.15rem'>{score}</span>",
                        unsafe_allow_html=True,
                    )
                    row_cols[2].markdown(f"**{company}**")
                    row_cols[3].markdown(f"[{domain}](https://{domain})")
                    row_cols[4].markdown(
                        badge(conf, conf_style["bg"], conf_style["fg"], font_size="0.8rem", padding="0.1rem 0.5rem"),
                        unsafe_allow_html=True,
                    )
                    spacer(10)

        if skipped:
            with st.expander(f"Skipped ({len(skipped)})"):
                for s in skipped:
                    name = esc(s.get("company_name", ""))
                    reason = esc(s.get("reason", ""))
                    st.markdown(f"- **{name}**: {reason}")
