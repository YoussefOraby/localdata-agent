# LocalData Agent

Free-first local AI data analyst agent for CSV analysis, charts, insights, web search, and multi-agent workflows using Ollama, FastAPI, Streamlit, LangGraph, and Python.

---

## Project Overview

LocalData Agent is a **free-first**, locally runnable AI data analyst. Upload CSV files and ask questions in natural language. The agent analyzes data, generates charts, runs Python code safely, searches the web, and coordinates multi-agent workflows — all without paid APIs.

The entire stack runs locally using Ollama for LLM inference, DuckDuckGo for web search, and open-source Python libraries for data analysis.

---

## Business Problem

Small businesses, startups, and non-technical teams often have CSV files with valuable data but struggle to analyze them. Writing custom Python scripts is time-consuming, and cloud AI tools (ChatGPT Code Interpreter, etc.) cost money and send data to third parties.

**LocalData Agent solves this** by providing a local, privacy-preserving, free alternative that anyone can run on their own machine.

---

## Solution

Users upload CSV files and ask natural language questions. The system:

1. **Routes** the question to the right analysis tools using keyword matching or LLM reasoning
2. **Executes** Python code in a restricted sandbox to compute accurate results (not LLM-hallucinated numbers)
3. **Generates** explanations using a local LLM (Ollama)
4. **Optionally searches** the web via DuckDuckGo for external context
5. **Returns** results, charts, sources, and a natural language answer

---

## Key Features

- **CSV upload and preview** — upload any CSV, preview in Streamlit
- **Template Analysis** — choose from 4 analysis types (summary, missing values, best/worst, charts)
- **Ask Agent** — free-text question with automatic tool routing
- **Multi-Agent** — 5-agent deterministic workflow (Manager, Data Analyst, Visualization, Research, Reviewer)
- **Python sandbox** — restricted code execution for accurate computation
- **LangGraph routing** — stateful graph-based agent coordination
- **Free web search** — DuckDuckGo integration with query fallbacks
- **Charts** — auto-generated bar, line, or histogram charts via matplotlib
- **Sources display** — web search results with titles, URLs, snippets
- **Local JSONL logging** — all runs logged to `logs/agent_runs.jsonl`
- **Docker Compose** — one-command deployment
- **Ollama local LLM** — no API keys, no cloud dependency
- **No paid API dependency** — 100% free and open-source tools

---

## Architecture Summary

```
User (Browser)
    │
    ▼
Streamlit UI (port 8501/8505)
    │  HTTP / REST
    ▼
FastAPI Backend (port 8000/8010)
    │
    ├── LangGraph Agent ──→ CSVAnalyzer, PythonSandbox, WebSearchTool, OllamaClient
    │
    ├── Multi-Agent ──→ Manager → Data Analyst / Research / Visualization → Reviewer
    │
    └── Template Analysis ──→ CSVAnalyzer + PythonSandbox
            │
            ▼
      JSONL Logger → logs/agent_runs.jsonl
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams and data flows.

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| LLM | Ollama + qwen2.5-coder:7b |
| Fallback Model | llama3.2:3b |
| Agent Framework | LangGraph |
| Data Analysis | pandas, numpy, matplotlib |
| Web Search | duckduckgo_search |
| Code Sandbox | AST validation + multiprocessing |
| Logging | JSONL |
| Deployment | Docker Compose |
| Testing | pytest |

---

## Project Modes

### Template Analysis
Choose from 4 manual analysis types: Summary, Missing Values & Outliers, Best/Worst Values, or Basic Chart. Results include computed data, explanation, and generated chart.

### Ask Agent
Type a free-text question. The agent uses keyword matching and optional LLM reasoning to select analysis tools (CSV analysis, chart generation, web search), executes them, and returns a combined answer.

### Multi-Agent
A deterministic 5-agent workflow:
1. **Manager Agent** — routes the question to appropriate agents
2. **Data Analyst Agent** — runs CSV analysis templates
3. **Visualization Agent** — generates charts
4. **Research Agent** — performs web search
5. **Reviewer Agent** — validates the output quality

---

## Setup — Local without Docker

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com) installed locally

### Install Ollama models
```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b   # optional fallback
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8010 --host 127.0.0.1
```

### Frontend (new terminal)
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

The frontend connects to `http://127.0.0.1:8010` by default.

Open the frontend at: **http://localhost:8501**

---

## Setup — Docker Compose

```bash
docker compose build
docker compose up
```

### URLs
| Service | URL |
|---|---|
| Frontend | http://localhost:8505 |
| Backend health | http://localhost:8010/health |
| API docs | http://localhost:8010/docs |

Docker assumes Ollama is running on the host machine at `http://host.docker.internal:11434`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check, returns model name |
| POST | `/analyze` | Template analysis with file upload + analysis type |
| POST | `/agent/analyze` | Free-text agent analysis with file upload + question |
| POST | `/multi-agent/analyze` | Multi-agent analysis with file upload + question |

All POST endpoints accept `multipart/form-data` with a CSV file and a text parameter (`analysis_type` or `question`).

---

## Sample Dataset

`data/samples/sample_sales.csv` is a synthetic 25-row sales dataset including:
- Date column daily from 2024-01-01
- Numeric columns: price, units_sold, revenue, rating
- Categorical columns: product, category
- One intentionally missing revenue value
- One outlier row (very high units_sold)

---

## Example Questions

### Template Mode
- **Summary** — Overview of rows, columns, data types
- **Missing Values & Outliers** — Detect gaps and statistical outliers
- **Best/Worst Values** — Find max, min, mean per numeric column
- **Basic Chart** — Auto-generated bar/line/histogram

### Ask Agent
- "Summarize this dataset."
- "Find missing values and outliers."
- "Show me a chart and search for current e-commerce trends."
- "Search for current sales improvement strategies."
- "What were the best and worst months for sales?"

### Multi-Agent
- "Analyze this dataset, show a chart, and search for current sales improvement strategies."

---

## Testing

```bash
cd backend
pytest -q
```

**Current result: 149 tests passed**

Tests are deterministic, offline-friendly, and do not require a running Ollama instance or internet connection.

---

## Security and Reliability

- **Restricted Python sandbox** — AST validation blocks dangerous imports
- **Import whitelist** — only pandas, numpy, matplotlib, math, statistics, json, re, collections, datetime
- **Blocked builtins** — `open`, `exec`, `eval`, `compile`, `input` are disabled
- **Timeout enforcement** — sandboxed code is killed after 30 seconds
- **Output limits** — stdout/stderr capped at 50,000 characters
- **Controlled API errors** — all endpoints return clean JSON errors, no raw stack traces
- **No raw CSV in logs** — logging captures metadata only
- **No paid API dependency** — 100% free and open-source
- **Dangerous context keys filtered** — context injection cannot override security

---

## Known Limitations

- **DuckDuckGo free search** may return 0 results or be rate-limited under heavy use
- **Local LLM quality** depends on the model and hardware; results may be less reliable than GPT-4/Claude
- **Ollama must be installed locally** — not included in Docker containers
- **Local models** can be slower than cloud-hosted LLMs
- **Python sandbox** is hardened for local use but should not be exposed publicly without stronger isolation (e.g., containerization)

---

## Future Improvements

- Stronger sandbox isolation with container-based execution
- Better chart type selection and customization
- SearXNG support as an alternative web search backend
- Authentication and multi-user support
- Export reports to PDF/Excel
- Better observability dashboard for agent runs

---

## Portfolio / CV Summary

> Built a free-first local AI data analyst agent using Ollama, FastAPI, Streamlit, LangGraph, and Python sandbox execution. The system analyzes CSV files, generates charts, performs web search, supports multi-agent workflows, and runs locally through Docker Compose without paid APIs.

---

## License

This project is for educational and portfolio purposes.
