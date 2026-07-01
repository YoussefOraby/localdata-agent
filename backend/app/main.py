import logging
import traceback

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.graph import run_agent
from app.agent.multi_agent import run_multi_agent
from app.analysis.csv_analyzer import CSVAnalyzer
from app.config import settings
from app.logs.logger import JSONLLogger
from app.models.schemas import AgentAnalyzeResponse, AnalyzeResponse, MultiAgentAnalyzeResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LocalData Agent", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

csv_analyzer = CSVAnalyzer()
jsonl_logger = JSONLLogger()


@app.get("/health")
def health():
    return {"status": "ok", "model": settings.LLM_MODEL}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    analysis_type: str = Form(...),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    if len(contents) > settings.MAX_CSV_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_CSV_SIZE_MB}MB.",
        )

    if analysis_type not in ("summary", "missing_outliers", "best_worst", "basic_chart"):
        raise HTTPException(status_code=400, detail=f"Unknown analysis type: {analysis_type}")

    result = csv_analyzer.analyze(contents, file.filename, analysis_type)

    jsonl_logger.log_run(result)

    return result


@app.post("/agent/analyze", response_model=AgentAnalyzeResponse)
async def agent_analyze(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    if len(contents) > settings.MAX_CSV_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_CSV_SIZE_MB}MB.",
        )

    result = run_agent(contents, file.filename, question)

    jsonl_logger.log_agent_run(result)

    return result


@app.post("/multi-agent/analyze", response_model=MultiAgentAnalyzeResponse)
async def multi_agent_analyze(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    if len(contents) > settings.MAX_CSV_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_CSV_SIZE_MB}MB.",
        )

    result = run_multi_agent(contents, file.filename, question)

    jsonl_logger.log_multi_agent_run(result)

    return result
