# Demo Script

A step-by-step walkthrough showing all features of LocalData Agent.

---

## Prerequisites

- Ollama running with `qwen2.5-coder:7b` (and optionally `llama3.2:3b`)
- Docker Compose (preferred) OR local backend + frontend running
- Sample dataset at `data/samples/sample_sales.csv`

---

## 1. Start the System

### Option A: Docker Compose
```bash
cd localdata
docker compose up -d
```

### Option B: Local
```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --port 8010 --host 127.0.0.1

# Terminal 2 — Frontend
cd frontend
streamlit run app.py
```

---

## 2. Open the UI

Navigate to **http://localhost:8505** (Docker) or **http://localhost:8501** (local).

---

## 3. Upload the Sample Dataset

1. Click **"Browse files"** in the sidebar
2. Select `data/samples/sample_sales.csv`
3. Verify the preview table loads with 25 rows and 6 columns

---

## 4. Template Analysis — Summary

1. Go to **Tab 1: Template Analysis**
2. Select **"Summary"** from the dropdown
3. Click **"Run Analysis"**
4. **Expected result:** Dataset overview, column types, numeric summaries, no missing values (except revenue column), row/column counts

---

## 5. Template Analysis — Missing Values & Outliers

1. Go to **Tab 1: Template Analysis**
2. Select **"Missing Values & Outliers"**
3. Click **"Run Analysis"**
4. **Expected result:** Shows missing values in revenue column, outlier detection with IQR method

---

## 6. Template Analysis — Basic Chart

1. Go to **Tab 1: Template Analysis**
2. Select **"Basic Chart"**
3. Click **"Run Analysis"**
4. **Expected result:** A chart is displayed (line or bar depending on data structure)

---

## 7. Ask Agent — Summarize

1. Go to **Tab 2: Ask Agent**
2. Type: `"Summarize this dataset."`
3. Click **"Ask Agent"**
4. **Expected result:** Dataset summary with rows, columns, numeric/categorical breakdown

---

## 8. Ask Agent — Find Missing Values

1. Go to **Tab 2: Ask Agent**
2. Type: `"Find missing values and outliers."`
3. Click **"Ask Agent"**
4. **Expected result:** Analysis of missing values and outlier detection

---

## 9. Ask Agent — Chart + Web Search

1. Go to **Tab 2: Ask Agent**
2. Type: `"Show me a chart and search for current e-commerce trends."`
3. Click **"Ask Agent"**
4. **Expected result:** Chart generated + web search results (if DuckDuckGo returns results) or graceful message about search being unavailable

---

## 10. Multi-Agent — Full Workflow

1. Go to **Tab 3: Multi-Agent**
2. Type: `"Analyze this dataset, show a chart, and search for current sales improvement strategies."`
3. Click **"Run Multi-Agent"**
4. **Expected result:**
   - Agents used list: Data Analyst Agent, Visualization Agent, Research Agent, Reviewer Agent
   - Dataset insights from CSV analysis
   - Chart displayed
   - Web context with sources (if available) or graceful fallback message
   - Reviewer status: "all checks passed" or review notes

---

## 11. Check the Logs

```bash
cat logs/agent_runs.jsonl
```

Each run is logged as a JSON line with:
- Timestamp
- Mode (template / agent / multi_agent)
- File name, question, tools used
- Success status, execution time
- Search queries (if applicable)

---

## 12. Check API Docs

Open **http://localhost:8010/docs** in a browser to see the interactive Swagger UI for all 4 endpoints.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| "Ollama not available" | Ollama not running | Start Ollama, verify `ollama list` |
| Web search returns 0 results | DuckDuckGo rate limit / no results | Try a simpler query, or check internet |
| Backend 404 | Wrong port | Use 8010 for Docker, 8000 for local backend |
| Frontend shows error connecting | BACKEND_API_URL wrong | Check frontend .env or env var |
| Chart not generated | No suitable columns for visualization | Use sample_sales.csv which has date + numeric columns |
