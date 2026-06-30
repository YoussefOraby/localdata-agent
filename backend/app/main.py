import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.csv_analyzer import CSVAnalyzer
from app.config import settings
from app.logs.logger import JSONLLogger
from app.models.schemas import AnalyzeResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LocalData Agent", version="0.1.0")

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
