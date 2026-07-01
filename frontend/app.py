from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8000"
EXPECTED_HEALTH_FIELDS = {"status", "model"}


def _render_steps(steps: list[str]):
    step_icons = {
        "Reading CSV file": "\U0001f4c1",
        "Inspecting columns": "\U0001f50d",
        "Running Python analysis": "\U0001f40d",
        "Preparing chart/result": "\U0001f4ca",
        "Analysis completed": "\u2705",
        "Composing final answer": "\u2705",
    }
    for s in steps:
        for key, icon in step_icons.items():
            if key in s:
                st.markdown(f"{icon} {s}")
                break
        else:
            st.markdown(f"\u2022 {s}")


def _render_chart(result: dict):
    chart = result.get("chart")
    if chart and chart.get("x") and chart.get("y"):
        st.subheader("Chart")
        chart_data = pd.DataFrame({"label": chart["x"], "value": chart["y"]})
        chart_type = chart.get("type", "bar")
        if chart_type == "line":
            st.line_chart(chart_data, x="label", y="value")
        else:
            st.bar_chart(chart_data, x="label", y="value")
        st.caption(f"{chart.get('title', '')} | X: {chart.get('x_label', '')}, Y: {chart.get('y_label', '')}")


def _display_template_result(result: dict):
    if not result.get("success"):
        st.error(result.get("explanation", "Analysis failed."))
        if result.get("generated_code"):
            with st.expander("Generated Code"):
                st.code(result["generated_code"], language="python")
        return

    st.subheader("Analysis Results")
    steps = result.get("steps", [])
    _render_steps(steps)

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
                st.metric(label=label, value=value if value is not None else "--")

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

    _render_chart(result)

    if result.get("generated_code"):
        with st.expander("Generated Python Code"):
            st.code(result["generated_code"], language="python")


def _display_agent_result(result: dict):
    if not result.get("success"):
        st.error(result.get("error", "Agent analysis failed."))
        return

    st.subheader("Agent Results")
    selected = result.get("selected_analysis_types", [])
    if selected:
        st.info(f"Agent selected: {', '.join(selected)}")

    steps = result.get("steps", [])
    _render_steps(steps)

    if result.get("execution_time_seconds") is not None:
        st.caption(f"Execution time: {result['execution_time_seconds']:.2f}s")

    final_answer = result.get("final_answer")
    if final_answer:
        st.markdown(final_answer)

    results_list = result.get("results", [])
    for i, r in enumerate(results_list):
        with st.expander(f"Analysis: {r.get('analysis_type', 'unknown')}"):
            if r.get("success"):
                rd = r.get("result") or {}
                metrics = rd.get("metrics") or {}
                if metrics:
                    st.subheader("Metrics")
                    m_cols = st.columns(min(len(metrics), 4))
                    for j, (key, value) in enumerate(metrics.items()):
                        col_idx = j % len(m_cols)
                        with m_cols[col_idx]:
                            label = key.replace("_", " ").title()
                            st.metric(label=label, value=value if value is not None else "--")

                tables = rd.get("tables") or {}
                for tk, tv in tables.items():
                    if tv:
                        st.markdown(f"**{tk.replace('_', ' ').title()}**")
                        if isinstance(tv, dict):
                            st.json(tv)
                        elif isinstance(tv, list):
                            st.write(tv)

                insights = rd.get("insights") or []
                if insights:
                    st.subheader("Key Insights")
                    for ins in insights:
                        st.markdown(f"- {ins}")
            else:
                st.error(r.get("error", "Analysis failed."))

    _render_chart(result)

    search_query = result.get("search_query")
    if search_query:
        st.caption(f"Search query used: `{search_query}`")

    sources = result.get("sources") or []
    selected = result.get("selected_analysis_types", [])
    if sources:
        st.subheader("Sources")
        for src in sources:
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            snippet = src.get("snippet")
            st.markdown(f"**{title}**")
            if url:
                st.markdown(f"[{url}]({url})")
            if snippet:
                st.markdown(f"> {snippet}")
            st.divider()
    elif "web_search" in selected:
        st.warning("No web results found. Try a broader question.")

    with st.expander("Raw Response"):
        st.json(result)


st.set_page_config(page_title="LocalData Agent", page_icon="\U0001f4ca")

st.title("LocalData Agent")
st.markdown(
    "Free-first local AI data analyst. Upload CSVs and ask questions about your data."
)

with st.sidebar:
    st.header("Settings")
    raw_url = st.text_input("Backend URL", value=API_BASE)

    parsed = urlparse(raw_url.rstrip("/"))
    api_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else raw_url.rstrip("/")
    analyze_url = f"{api_url}/analyze"
    agent_url = f"{api_url}/agent/analyze"

    st.caption(f"`{analyze_url}`")
    st.caption(f"`{agent_url}`")

    try:
        r = requests.get(f"{api_url}/health", timeout=5)
        if r.status_code == 200:
            body = r.json()
            if EXPECTED_HEALTH_FIELDS.issubset(body.keys()):
                st.success(f"Backend connected (model: {body.get('model', '?')})")
            else:
                st.error(f"Port responds but is not the LocalData backend (unexpected response: {body})")
        else:
            st.error("Backend not reachable")
    except requests.exceptions.RequestException:
        st.error("Backend not reachable")

    st.divider()
    st.markdown("**Supported analysis types:**")
    st.markdown("- Summary")
    st.markdown("- Missing Values & Outliers")
    st.markdown("- Best/Worst Values")
    st.markdown("- Basic Chart")
    st.markdown("- Web Search (free DuckDuckGo, may be unavailable)")

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

    tab1, tab2 = st.tabs(["Template Analysis", "Ask Agent"])

    with tab1:
        analysis_type_map = {
            "Summary": "summary",
            "Missing Values & Outliers": "missing_outliers",
            "Best/Worst Values": "best_worst",
            "Basic Chart": "basic_chart",
        }

        selected_label = st.selectbox(
            "Choose analysis type",
            options=list(analysis_type_map.keys()),
            key="tab1_select",
        )
        analysis_type = analysis_type_map[selected_label]

        if st.button("Analyze", type="primary", key="tab1_btn"):
            with st.spinner("Analyzing..."):
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                data = {"analysis_type": analysis_type}

                try:
                    resp = requests.post(analyze_url, files=files, data=data, timeout=120)
                    resp.raise_for_status()
                    result = resp.json()
                except requests.exceptions.ConnectionError:
                    st.error(f"Cannot connect to backend at {analyze_url}. Make sure the backend is running.")
                    st.stop()
                except Exception as e:
                    st.error(f"Request failed: {e}")
                    st.stop()

            _display_template_result(result)

    with tab2:
        st.markdown("Ask a question about your CSV in plain language.")
        question = st.text_area(
            "Your question",
            placeholder="e.g. Summarize this dataset and search for current sales improvement strategies.",
            key="tab2_question",
        )

        if st.button("Ask Agent", type="primary", key="tab2_btn"):
            if not question.strip():
                st.warning("Please enter a question.")
                st.stop()

            with st.spinner("Agent is thinking..."):
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                data = {"question": question}

                try:
                    resp = requests.post(agent_url, files=files, data=data, timeout=300)
                    resp.raise_for_status()
                    result = resp.json()
                except requests.exceptions.ConnectionError:
                    st.error(f"Cannot connect to backend at {agent_url}. Make sure the backend is running.")
                    st.stop()
                except Exception as e:
                    st.error(f"Request failed: {e}")
                    st.stop()

            _display_agent_result(result)

else:
    st.info("Upload a CSV file to get started.")
