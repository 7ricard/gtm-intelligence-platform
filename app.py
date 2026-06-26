import streamlit as st

from src.agent import run_research
from src.database import get_all_accounts


def esc(text):
    return str(text).replace("$", "\\$")


TIER_COLORS = {"A+": "#00a550", "A": "#4caf50", "B": "#ff9800", "C": "#f44336"}
CONF_COLORS = {"high": "#4caf50", "medium": "#ff9800"}

st.set_page_config(page_title="GTM Intelligence Platform", layout="wide")

st.title("GTM Intelligence Platform")
st.subheader("Account Intelligence")

tab_research, tab_discover = st.tabs(["Research a company", "Discover accounts"])

# -- Research a company -------------------------------------------------------
with tab_research:
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

# -- Discover accounts --------------------------------------------------------
with tab_discover:
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

# -- Research History ---------------------------------------------------------
st.divider()
st.subheader("Research History")

history = get_all_accounts()
if not history:
    st.caption("No accounts researched yet.")
else:
    display_cols = ["company_name", "domain", "icp_tier", "icp_score", "created_at"]
    rows = [{col: row.get(col) for col in display_cols} for row in history]
    st.dataframe(rows, use_container_width=True)
