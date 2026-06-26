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


def _csv_input(label, value_list, key):
    current = ", ".join(value_list) if value_list else ""
    raw = st.text_input(label, value=current, key=key)
    return [v.strip() for v in raw.split(",") if v.strip()]


TIER_COLORS = {"A+": "#00a550", "A": "#4caf50", "B": "#ff9800", "C": "#f44336"}
CONF_COLORS = {"high": "#4caf50", "medium": "#ff9800"}

st.set_page_config(page_title="GTM Intelligence Platform", layout="wide")
st.title("GTM Intelligence Platform")

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

    with st.form("profile_form"):
        st.subheader("Firmographic")
        f_verticals = _csv_input("Verticals (comma-separated)", firm.get("verticals", []), f"f_verticals_{pid}")
        f_arr_range = st.text_input("ARR Range", value=firm.get("arr_range", ""), key=f"f_arr_range_{pid}")
        f_funding_stage = st.text_input("Funding Stage", value=firm.get("funding_stage", ""), key=f"f_funding_stage_{pid}")
        f_business_model = st.text_input("Business Model", value=firm.get("business_model", ""), key=f"f_business_model_{pid}")
        f_employee_range = st.text_input("Employee Range", value=firm.get("employee_range", ""), key=f"f_employee_range_{pid}")
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

        st.subheader("Weights")
        w_firmographic = st.number_input("firmographic_fit", min_value=0, max_value=100, value=int(weights_data.get("firmographic_fit", 20)), step=1, key=f"w_firmographic_{pid}")
        w_buying = st.number_input("buying_signals", min_value=0, max_value=100, value=int(weights_data.get("buying_signals", 20)), step=1, key=f"w_buying_{pid}")
        w_funding = st.number_input("funding_stage", min_value=0, max_value=100, value=int(weights_data.get("funding_stage", 15)), step=1, key=f"w_funding_{pid}")
        w_industry = st.number_input("industry_fit", min_value=0, max_value=100, value=int(weights_data.get("industry_fit", 15)), step=1, key=f"w_industry_{pid}")
        w_techno = st.number_input("technographic_fit", min_value=0, max_value=100, value=int(weights_data.get("technographic_fit", 15)), step=1, key=f"w_techno_{pid}")
        w_persona = st.number_input("persona_accessibility", min_value=0, max_value=100, value=int(weights_data.get("persona_accessibility", 15)), step=1, key=f"w_persona_{pid}")

        weight_sum = w_firmographic + w_buying + w_funding + w_industry + w_techno + w_persona
        if weight_sum == 100:
            st.caption(f"Weights sum: {weight_sum}")
        else:
            st.error(f"Weights must sum to 100. Current sum: {weight_sum}")

        st.subheader("Thresholds")
        t_aplus = st.number_input("A+ threshold", min_value=0, max_value=100, value=int(thresholds_data.get("A+", 90)), step=1, key=f"t_aplus_{pid}")
        t_a = st.number_input("A threshold", min_value=0, max_value=100, value=int(thresholds_data.get("A", 75)), step=1, key=f"t_a_{pid}")
        t_b = st.number_input("B threshold", min_value=0, max_value=100, value=int(thresholds_data.get("B", 50)), step=1, key=f"t_b_{pid}")

        st.divider()
        new_profile_name = st.text_input("New profile name (for Save as New)", key="new_profile_name")

        save_col, saveas_col = st.columns(2)
        with save_col:
            save_btn = st.form_submit_button(
                "Save Changes",
                disabled=(weight_sum != 100),
            )
        with saveas_col:
            saveas_btn = st.form_submit_button(
                "Save as New Profile",
                disabled=(weight_sum != 100),
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
        company_name = st.text_input("Company Name")
        domain = st.text_input("Domain", placeholder="stripe.com")
        submitted = st.form_submit_button("Research Account")

    if submitted:
        if not company_name or not domain:
            st.error("Both Company Name and Domain are required.")
        else:
            with st.spinner("Researching..."):
                brief = run_research(company_name, domain)

            tier = brief.get("icp_tier", "")
            tier_color = TIER_COLORS.get(tier, "gray")

            tier_col, score_col = st.columns([1, 1])
            with tier_col:
                st.markdown(
                    f"**ICP Tier:** <span style='color:{tier_color}; font-size:1.4rem; font-weight:bold'>{tier}</span>",
                    unsafe_allow_html=True,
                )
            with score_col:
                st.metric("ICP Score", brief.get("icp_score", ""))

            st.write(esc(brief.get("summary", "")))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**ICP Signals**")
                for item in brief.get("icp_signals", []):
                    st.markdown(f"- {esc(item)}")
            with col2:
                st.markdown("**Pain Points**")
                for item in brief.get("pain_points", []):
                    st.markdown(f"- {esc(item)}")
            with col3:
                st.markdown("**Tech Stack Signals**")
                for item in brief.get("tech_stack_signals", []):
                    st.markdown(f"- {esc(item)}")

            st.info(esc(brief.get("recommended_angle", "")))

            breakdown = brief.get("score_breakdown", [])
            if breakdown:
                st.subheader("Score Breakdown")
                for row in breakdown:
                    dimension_label = row["dimension"].replace("_", " ").title()
                    score = row["score"]
                    st.markdown(
                        f"**{dimension_label}** | Score: {score} | Weight: {row['weight']} | Contribution: {row['contribution']}"
                    )
                    st.progress(score / 100)
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
                st.dataframe(table_rows, use_container_width=True)

            st.subheader("Company Intelligence")
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
        st.dataframe(rows, use_container_width=True)

# -- TAB 3: Discover Accounts -------------------------------------------------
with tab_discover:
    active_row_name_d = next((p["name"] for p in list_profiles() if p.get("is_active")), "default")
    st.caption(f"Scoring against active profile: **{active_row_name_d}**")

    focus_input = st.text_input(
        "Focus (optional)",
        placeholder="e.g. fintech, or funded in the last 6 months",
    )
    limit_input = st.number_input(
        "How many to qualify", min_value=3, max_value=10, value=5, step=1
    )
    discover_btn = st.button("Discover Accounts")

    if discover_btn:
        from src.discovery import discover

        with st.spinner("Discovering accounts. This takes a couple of minutes..."):
            result = discover(focus=focus_input or None, limit=int(limit_input))

        qualified = result.get("qualified", [])
        skipped = result.get("skipped", [])

        if not qualified:
            st.warning("No qualified accounts found. Check the skipped list below.")
        else:
            st.success(
                f"Found {len(qualified)} qualified account(s). All discovered companies are saved to the accounts database."
            )

            header_cols = st.columns([1, 1, 3, 3, 2])
            header_cols[0].markdown("**Tier**")
            header_cols[1].markdown("**ICP Score**")
            header_cols[2].markdown("**Company**")
            header_cols[3].markdown("**Domain**")
            header_cols[4].markdown("**Match Confidence**")

            st.divider()

            for row in qualified:
                tier = row.get("icp_tier", "")
                score = row.get("icp_score", "")
                company = esc(row.get("company_name", ""))
                domain = row.get("domain", "")
                conf = row.get("match_confidence", "")

                tier_color = TIER_COLORS.get(tier, "gray")
                conf_color = CONF_COLORS.get(conf, "gray")

                row_cols = st.columns([1, 1, 3, 3, 2])
                row_cols[0].markdown(
                    f"<span style='color:{tier_color}; font-weight:bold; font-size:1.1rem'>{tier}</span>",
                    unsafe_allow_html=True,
                )
                row_cols[1].markdown(str(score))
                row_cols[2].markdown(company)
                row_cols[3].markdown(f"[{domain}](https://{domain})")
                row_cols[4].markdown(
                    f"<span style='color:{conf_color}'>{conf}</span>",
                    unsafe_allow_html=True,
                )

        if skipped:
            with st.expander(f"Skipped ({len(skipped)})"):
                for s in skipped:
                    name = esc(s.get("company_name", ""))
                    reason = esc(s.get("reason", ""))
                    st.markdown(f"- **{name}**: {reason}")
