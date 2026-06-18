import streamlit as st

from src.agent import run_research
from src.database import get_all_accounts


def esc(text):
    return str(text).replace("$", "\\$")


st.set_page_config(page_title="GTM Intelligence Platform", layout="wide")

st.title("GTM Intelligence Platform")
st.subheader("Account Research Agent, Phase 1")

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
        tier_colors = {"A+": "#00a550", "A": "#4caf50", "B": "orange", "C": "red"}
        tier_color = tier_colors.get(tier, "gray")

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
