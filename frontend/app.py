import json

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="LocalData Agent", page_icon="📊")

st.title("LocalData Agent")
st.markdown(
    "Free-first local AI data analyst. Upload CSVs and ask questions about your data."
)

with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("Backend URL", value=API_BASE)
    st.divider()
    st.markdown("**Supported analysis types:**")
    st.markdown("- Summary")
    st.markdown("- Missing Values & Outliers")
    st.markdown("- Best/Worst Values")
    st.markdown("- Basic Chart")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df_preview = pd.read_csv(uploaded_file, nrows=5)
        uploaded_file.seek(0)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    rows_estimate = None
    try:
        df_full = pd.read_csv(uploaded_file)
        uploaded_file.seek(0)
        rows_estimate = len(df_full)
        cols_estimate = len(df_full.columns)
    except Exception:
        rows_estimate = len(df_preview)

    st.subheader("File Preview")
    st.info(f"**{uploaded_file.name}** — {rows_estimate} rows, {len(df_preview.columns)} columns")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.dataframe(df_preview, use_container_width=True)
    with col2:
        st.markdown("**Columns**")
        for c in df_preview.columns:
            dtype = str(df_preview[c].dtype)
            st.markdown(f"- `{c}` ({dtype})")

    st.divider()

    analysis_type_map = {
        "Summary": "summary",
        "Missing Values & Outliers": "missing_outliers",
        "Best/Worst Values": "best_worst",
        "Basic Chart": "basic_chart",
    }

    selected_label = st.selectbox(
        "Choose analysis type",
        options=list(analysis_type_map.keys()),
    )
    analysis_type = analysis_type_map[selected_label]

    if st.button("Analyze", type="primary"):
        with st.spinner("Analyzing..."):
            uploaded_file.seek(0)
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
            data = {"analysis_type": analysis_type}

            try:
                resp = requests.post(
                    f"{api_url}/analyze",
                    files=files,
                    data=data,
                    timeout=120,
                )
                resp.raise_for_status()
                result = resp.json()
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to backend at {api_url}. Make sure the backend is running.")
                st.stop()
            except Exception as e:
                st.error(f"Request failed: {e}")
                st.stop()

        if not result.get("success"):
            st.error(result.get("explanation", "Analysis failed."))
            if result.get("generated_code"):
                with st.expander("Generated Code"):
                    st.code(result["generated_code"], language="python")
            st.stop()

        st.subheader("Analysis Results")

        steps = result.get("steps", [])
        step_icons = {
            "Reading CSV file": "📁",
            "Inspecting columns": "🔍",
            "Running Python analysis": "🐍",
            "Preparing chart/result": "📊",
            "Analysis completed": "✅",
        }
        step_col1, step_col2 = st.columns([1, 5])
        with step_col1:
            for s in steps:
                icon = step_icons.get(s, "•")
                st.markdown(f"{icon}")
        with step_col2:
            for s in steps:
                st.markdown(f"{s}")

        if result.get("execution_time_seconds") is not None:
            st.caption(f"Execution time: {result['execution_time_seconds']:.2f}s")

        explanation = result.get("explanation")
        if explanation:
            st.markdown(explanation)

        result_data = result.get("result") or {}
        metrics = result_data.get("metrics") or {}
        if metrics:
            st.subheader("Metrics")
            m_cols = st.columns(min(len(metrics), 4))
            for i, (key, value) in enumerate(metrics.items()):
                col_idx = i % len(m_cols)
                with m_cols[col_idx]:
                    label = key.replace("_", " ").title()
                    st.metric(label=label, value=value if value is not None else "—")

        tables = result_data.get("tables") or {}
        for table_key, table_value in tables.items():
            if table_value:
                with st.expander(f"{table_key.replace('_', ' ').title()}"):
                    if isinstance(table_value, dict):
                        st.json(table_value)
                    elif isinstance(table_value, list):
                        st.write(table_value)

        insights = result_data.get("insights") or []
        if insights:
            st.subheader("Key Insights")
            for ins in insights:
                st.markdown(f"- {ins}")

        chart = result.get("chart")
        if chart and chart.get("x") and chart.get("y"):
            st.subheader("Chart")
            chart_data = pd.DataFrame(
                {"label": chart["x"], "value": chart["y"]}
            )
            chart_type = chart.get("type", "bar")
            if chart_type == "line":
                st.line_chart(chart_data, x="label", y="value")
            else:
                st.bar_chart(chart_data, x="label", y="value")
            st.caption(f"{chart.get('title', '')} | X: {chart.get('x_label', '')}, Y: {chart.get('y_label', '')}")

        if result.get("generated_code"):
            with st.expander("Generated Python Code"):
                st.code(result["generated_code"], language="python")
else:
    st.info("Upload a CSV file to get started.")
