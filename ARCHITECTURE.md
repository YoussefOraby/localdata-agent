# Architecture

## High-Level System Architecture

```mermaid
flowchart TD
    User["Browser User"] -->|Upload CSV + Ask Question| Streamlit["Streamlit UI\nPort 8501/8505"]
    Streamlit -->|HTTP POST multipart/form-data| FastAPI["FastAPI Backend\nPort 8000/8010"]

    FastAPI --> Router["POST /analyze\nPOST /agent/analyze\nPOST /multi-agent/analyze"]

    Router --> Template["Template Analysis\nCSVAnalyzer"]
    Router --> Agent["Ask Agent\nLangGraph Workflow"]
    Router --> MultiAgent["Multi-Agent\nDeterministic Workflow"]

    Template --> Sandbox["PythonSandbox\n(multiprocess + AST validate)"]
    Agent --> Sandbox
    MultiAgent --> Sandbox

    Sandbox -->|exec result| Response["JSON Response\nresults + charts + answer"]

    Agent --> WebSearch["WebSearchTool\nDuckDuckGo"]
    MultiAgent --> WebSearch

    Agent --> Ollama["OllamaClient\nqwen2.5-coder:7b"]
    MultiAgent --> Ollama
    Template --> Ollama

    FastAPI --> Logger["JSONLLogger\nlogs/agent_runs.jsonl"]
```

## Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| **Streamlit Frontend** | `frontend/app.py` | CSV upload, 3-tab UI (Template/Agent/Multi-Agent), display results/charts/sources |
| **FastAPI Backend** | `backend/app/main.py` | 4 REST endpoints, CORS, global error handling, request routing |
| **CSVAnalyzer** | `backend/app/analysis/csv_analyzer.py` | Read CSV via pandas, select template, run sandboxed code, generate LLM explanation |
| **PythonSandbox** | `backend/app/executor/sandbox.py` | AST validation, import whitelist, blocked builtins, multiprocess isolation, timeout, output capping, result serialization |
| **LangGraph Agent** | `backend/app/agent/graph.py` | 3-node state graph: route → analyze → compose answer |
| **Multi-Agent** | `backend/app/agent/multi_agent.py` | 5 deterministic agents: Manager, Data Analyst, Visualization, Research, Reviewer |
| **Router** | `backend/app/agent/router.py` | Keyword matching + optional LLM routing to select analysis types |
| **WebSearchTool** | `backend/app/search/web_search.py` | DuckDuckGo search with retry fallbacks |
| **OllamaClient** | `backend/app/llm/ollama_client.py` | Ollama API wrapper with model fallback |
| **JSONLLogger** | `backend/app/logs/logger.py` | Append-only JSONL logging for all run modes |

## Endpoint Flow

```mermaid
sequenceDiagram
    participant User as User
    participant UI as Streamlit
    participant API as FastAPI
    participant Agent as LangGraph/Multi-Agent
    participant Tools as Tools (Sandbox/Search/LLM)
    participant Log as JSONL Logger

    User->>UI: Upload CSV + Question
    UI->>API: POST /agent/analyze (multipart)
    API->>API: Validate file (CSV, size, non-empty)
    API->>Agent: run_agent(contents, filename, question)
    Agent->>Agent: route_question() → LLM/keyword routing
    Agent->>Tools: execute selected analyses
    Tools->>Sandbox: run Python template code
    Tools->>Ollama: generate explanation
    Tools->>WebSearch: search DuckDuckGo
    Tools->>Agent: return results
    Agent->>Agent: compose final answer
    API->>Log: log_agent_run(result)
    API->>UI: JSON response (results, chart, sources, answer)
    UI->>User: Display results in tabs
```

## Agent Routing Flow

```mermaid
flowchart LR
    Q["User Question"] --> Router{"route_question()"}
    Router -->|LLM available| LLM["Ollama JSON response"]
    Router -->|Fallback| Keyword["Keyword matching"]
    LLM --> Merge["_merge_types()\nmerge LLM + keyword results"]
    Keyword --> Merge

    Merge --> Types["['summary', 'chart', 'web_search', ...]"]
    Types --> Graph["LangGraph execution"]

    Graph --> Summary["summary analysis"]
    Graph --> Missing["missing_outliers analysis"]
    Graph --> Chart["basic_chart analysis"]
    Graph --> Search["web_search (DuckDuckGo)"]
    Graph --> BestWorst["best_worst analysis"]

    Summary --> Compose["_compose_answer()"]
    Missing --> Compose
    Chart --> Compose
    Search --> Compose
    BestWorst --> Compose

    Compose --> Answer["Final answer + chart + sources"]
```

## Multi-Agent Workflow

```mermaid
flowchart TD
    Q["User Question"] --> Manager["Manager Agent\nroute_question() → select types & agents"]

    Manager --> DA["Data Analyst Agent\nRun CSV analysis templates"]
    Manager --> Viz["Visualization Agent\nRun basic_chart analysis"]
    Manager --> Research["Research Agent\nDuckDuckGo web search"]

    DA --> Results["Results dict"]
    Viz --> Results
    Research --> Results

    Results --> ComposeMA["Compose Final Answer"]
    ComposeMA --> Reviewer["Reviewer Agent\nValidate output quality"]

    Reviewer -->|passed| Final["Return success + answer"]
    Reviewer -->|issues| Final["Return with review notes"]
```

## Docker Architecture

```mermaid
flowchart LR
    Host["Host Machine"] --> Ollama["Ollama (host.docker.internal:11434)"]

    subgraph Docker["Docker Compose"]
        Frontend["frontend:8505\nStreamlit\nBACKEND_API_URL=http://backend:8000"]
        Backend["backend:8010\nFastAPI\nOLLAMA_BASE_URL=http://host.docker.internal:11434"]
    end

    Browser["Browser"] --> Frontend
    Frontend -->|HTTP| Backend
    Backend -->|HTTP| Ollama
```

## Directory Structure

```
localdata/
├── backend/
│   ├── app/
│   │   ├── agent/          # LangGraph agent, multi-agent, router, state
│   │   ├── analysis/       # CSVAnalyzer, templates
│   │   ├── executor/       # PythonSandbox
│   │   ├── llm/            # OllamaClient
│   │   ├── logs/           # JSONLLogger
│   │   ├── models/         # Pydantic schemas
│   │   ├── search/         # WebSearchTool
│   │   ├── config.py       # Settings
│   │   └── main.py         # FastAPI app + routes
│   ├── tests/              # pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── app.py              # Streamlit UI
│   └── requirements.txt
├── data/samples/           # Sample CSV datasets
├── logs/                   # JSONL log output
├── docker-compose.yml
├── Dockerfile              # backend
└── Dockerfile              # frontend (in frontend/ dir, referenced by compose)
```
