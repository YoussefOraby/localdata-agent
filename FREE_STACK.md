# Free Stack Rationale

## Why Free-First?

LocalData Agent is built on the principle that powerful AI data analysis should be accessible to everyone without recurring API costs.

- **Zero API cost** — no OpenAI, Claude, Tavily, or LangSmith bills
- **Local privacy** — data never leaves your machine
- **Offline-friendly** — works without internet for CSV analysis
- **Accessible** — easier for students, hobbyists, and developers to run
- **No vendor lock-in** — fully open-source, self-contained stack

---

## Paid Alternative vs Free Replacement

| Component | Paid Option | Free Replacement | Tradeoff |
|---|---|---|---|
| **LLM** | OpenAI GPT-4 / Anthropic Claude | Ollama + qwen2.5-coder:7b | Lower quality, requires local GPU/CPU |
| **Web Search** | Tavily Search API | DuckDuckGo Search (duckduckgo_search) | May return 0 results, rate limits |
| **Code Execution** | OpenAI Code Interpreter | PythonSandbox (AST + multiprocess) | Needs manual hardening, no hosted infra |
| **Observability** | LangSmith hosted | Local JSONL logs | No hosted dashboard, manual inspection |
| **Agent Framework** | LangGraph + LangSmith cloud | LangGraph (open-source) + local | No cloud tracing |
| **Deployment** | Cloud hosting (AWS, GCP, Railway) | Docker Compose (local) | Local-only by default |

---

## How We Compensate

### Code-First Approach (Not LLM-First)
Instead of asking an LLM to compute statistics (which it will hallucinate), the system generates and runs actual Python code in a restricted sandbox. The LLM is used only for:
- Routing questions to the right tools
- Explaining results in plain language

This means **all numbers are real**, computed by pandas/numpy, not guessed by the LLM.

### Deterministic Routing Fallback
The router uses keyword matching as the primary mechanism. LLM routing is attempted but never required. If the LLM is unavailable or returns invalid JSON, keyword routing takes over seamlessly.

### Strict JSON Prompt for LLM Routing
The LLM prompt requests a strict JSON format. If the response is malformed, the parser safely falls back to keyword routing — no crashes.

### Search Query Cleaning and Fallback Retries
Web search queries are cleaned (removing "search for", "current", CSV references) and retried with progressively shorter queries if the first attempt returns no results.

### Graceful Search Failure
If DuckDuckGo is unavailable or returns no results, the system still returns results from CSV analysis with a clear note that web search was unavailable. No error bubbles up to the user.

### Local Logging
All runs (template, agent, multi-agent) are logged to a local JSONL file with metadata including mode, success status, execution time, and tool usage. No external logging service needed.

### Sandbox Hardening
The Python sandbox blocks dangerous imports (`os`, `sys`, `subprocess`, etc.) and builtins (`open`, `eval`, `exec`), enforces timeouts, and caps output — all without needing a cloud code execution service.

### Tests for Offline Deterministic Behavior
All 149 tests run without Ollama or internet. They use mocks and deterministic data, making the test suite fast and reliable.

---

## Known Free Tool Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| DuckDuckGo may return 0 results | User gets no web context | System shows clear message; CSV analysis still works |
| DuckDuckGo rate limits | Repeated searches may fail | Fallback retries with shorter queries |
| Ollama requires local setup | Barrier to entry | Docker setup is documented and tested |
| Local models slower/weaker than GPT-4 | Lower quality explanations | Code-first approach ensures correct computation; LLM used for explanation only |
| Search is optional, not core | Web search adds value but isn't required | System never depends on search for core CSV analysis |
| Python sandbox is local-only | Not suitable for public SaaS deployment | Stronger isolation (Docker-in-Docker) is a documented future improvement |

---

## Design Principle

> **CSV analysis is the core value. Web search is secondary and optional.**

The system is designed so that:
- Everything works with zero internet access (for CSV analysis)
- Web search adds context but is never required
- The LLM explains results but never computes them
- All computations are accurate (pandas/numpy), not hallucinated
- The free alternatives are good enough for local/individual use
- Paid upgrades exist but are not needed for the core workflow
