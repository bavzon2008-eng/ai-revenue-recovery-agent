import streamlit as st
import pandas as pd

from database import (
    init_db,
    get_all_payments,
    get_audit_log,
)
from generate_data import generate_fake_payments


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Revenue Recovery Agent",
    page_icon="💰",
    layout="wide",
)


# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_db()


# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown(
    """
    <style>
        div[data-testid="stMetric"] {
            background-color: #1a1c24;
            border: 1px solid #2d2f3a;
            padding: 15px;
            border-radius: 10px;
        }

        div[data-testid="stMetric"] * {
            color: #ffffff !important;
        }

        div[data-testid="stMetric"] label {
            color: #9aa0ac !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# PAGE HEADER
# =========================================================

st.title("💰 AI Revenue Recovery Agent")

st.caption(
    "Detects failed payments and recovers lost revenue automatically"
)


# =========================================================
# SIDEBAR CONTROLS
# =========================================================

with st.sidebar:

    st.header("Controls")

    # -----------------------------------------------------
    # Generate fresh test data
    # -----------------------------------------------------

    if st.button(
        "🎲 Generate fresh test data",
        use_container_width=True,
    ):

        with st.spinner("Generating fake payment batch..."):

            generate_fake_payments(
                n=50,
                failure_rate=0.4,
            )

        # Clear previous recovery results because this is
        # a completely new dataset.
        st.session_state.pop("last_results", None)

        st.success("Test data generated!")

        st.rerun()

    st.divider()

    # -----------------------------------------------------
    # Run Recovery Agent
    # -----------------------------------------------------

    if st.button(
        "🤖 Run Recovery Agent",
        use_container_width=True,
        type="primary",
    ):

        from agent import run_recovery_batch

        with st.spinner(
            "Agent is deciding and acting on failed payments..."
        ):

            results = run_recovery_batch()

        # Store only the latest run here.
        st.session_state["last_results"] = results

        st.success(
            f"Processed {results['processed']} payments — "
            f"recovered ₹{results['recovered_amount']:,.0f}"
        )

        st.rerun()

    st.caption(
        "Day 3: AI analyzes each failed payment and chooses "
        "RETRY, REMIND, or STOP."
    )


# =========================================================
# LOAD PAYMENT DATA
# =========================================================

payments = get_all_payments()


# =========================================================
# EMPTY STATE
# =========================================================

if not payments:

    st.info(
        "No data yet — click **Generate fresh test data** "
        "in the sidebar to get started."
    )


# --- Dashboard ---
else:
    df = pd.DataFrame(payments)

    total = len(df)

    failed = len(
        df[df["status"] == "failed"]
    )

    succeeded = len(
        df[df["status"] == "success"]
    )

    amount_at_risk = df[
        df["status"] == "failed"
    ]["amount"].sum()

    # --- Main KPI cards ---
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Payments",
        total,
    )

    col2.metric(
        "Successful",
        succeeded,
    )

    col3.metric(
        "Failed",
        failed,
    )

    col4.metric(
        "At Risk",
        f"₹{amount_at_risk:,.0f}",
    )

    # --- Last Recovery Run ---
    if "last_results" in st.session_state:
        st.subheader("🎯 Last Recovery Run")

        r = st.session_state["last_results"]

        rc1, rc2, rc3 = st.columns(3)

        rc1.metric(
            "Payments Processed",
            r["processed"],
        )

        rc2.metric(
            "Recovered This Run",
            r["recovered_count"],
        )

        rc3.metric(
            "Amount Recovered This Run",
            f"₹{r['recovered_amount']:,.0f}",
        )

        with st.expander("See what the agent decided for each payment"):
            st.dataframe(
                pd.DataFrame(r["actions"]),
                use_container_width=True,
                hide_index=True,
            )

        # --- Overall Recovery ---
        st.subheader("📈 Overall Recovery Performance")

        # Reload current database state
        current_payments = get_all_payments()
        current_df = pd.DataFrame(current_payments)

        if not current_df.empty:

            total_recovered_amount = current_df[
                current_df["recovered"] == 1
            ]["amount"].sum()

            total_recovered_count = int(
                (current_df["recovered"] == 1).sum()
            )

            current_at_risk = current_df[
                (current_df["status"] == "failed") &
                (current_df["recovered"] == 0)
            ]["amount"].sum()

        else:
            total_recovered_amount = 0
            total_recovered_count = 0
            current_at_risk = 0

        overall_col1, overall_col2, overall_col3 = st.columns(3)

        overall_col1.metric(
            "💰 Total Recovered",
            f"₹{total_recovered_amount:,.0f}",
        )

        overall_col2.metric(
            "✅ Payments Recovered",
            total_recovered_count,
        )

        overall_col3.metric(
            "⚠️ Still At Risk",
            f"₹{current_at_risk:,.0f}",
        )

        # --- Recovery Overview Chart ---
        st.subheader("📊 Recovery Overview")

        chart_data = pd.DataFrame({
            "Category": [
                "Recovered",
                "Still At Risk",
            ],
            "Amount": [
                total_recovered_amount,
                current_at_risk,
            ],
        })

        st.bar_chart(
            chart_data.set_index("Category")
        )

        # --- Recovery Rate ---
        total_recovery_base = (
            total_recovered_amount + current_at_risk
        )

        recovery_rate = (
            total_recovered_amount
            / total_recovery_base
            * 100
            if total_recovery_base > 0
            else 0
        )

        st.metric(
            "🏆 Overall Recovery Rate",
            f"{recovery_rate:.1f}%",
        )

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 All Payments",
            "⚠️ Failed Payments",
            "🧾 Audit Log",
        ]
    )

    # =========================================================
    # TAB 1 — ALL PAYMENTS
    # =========================================================

    with tab1:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

    # =========================================================
    # TAB 2 — FAILED PAYMENTS
    # =========================================================

    with tab2:
        from detection import enrich_failed_payments

        raw_failed = [
            p
            for p in payments
            if p["status"] == "failed"
        ]

        enriched = enrich_failed_payments(
            raw_failed
        )

        if enriched:

            enriched_df = pd.DataFrame(
                enriched
            )

            display_cols = [
                "id",
                "customer_name",
                "amount",
                "failure_reason",
                "days_failed",
                "urgency",
                "retry_count",
                "eligible",
            ]

            st.dataframe(
                enriched_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            # --- Urgency counters ---
            urgency_counts = (
                enriched_df["urgency"]
                .value_counts()
            )

            col_a, col_b, col_c = st.columns(3)

            col_a.metric(
                "🔴 High urgency",
                int(
                    urgency_counts.get(
                        "high",
                        0,
                    )
                ),
            )

            col_b.metric(
                "🟡 Medium urgency",
                int(
                    urgency_counts.get(
                        "medium",
                        0,
                    )
                ),
            )

            col_c.metric(
                "🟢 Low urgency",
                int(
                    urgency_counts.get(
                        "low",
                        0,
                    )
                ),
            )

        else:
            st.info(
                "No failed payments right now."
            )

        st.caption(
            "Day 3: the AI agent decides "
            "retry / remind / stop for each of these."
        )

    # =========================================================
    # TAB 3 — AUDIT LOG
    # =========================================================

    with tab3:
        audit = get_audit_log()

        if audit:
            audit_df = pd.DataFrame(audit)

            st.dataframe(
                audit_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "details": st.column_config.TextColumn(
                        "Details",
                        width="large",
                    ),
                },
            )

        else:
            st.info(
                "Empty for now — this fills up once "
                "the recovery agent starts taking actions."
            )