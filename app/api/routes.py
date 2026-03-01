import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict

from app.agents.source_manager import SourceManagerAgent
from app.utils.task_manager import task_manager
from app.utils.background_worker import start_task

router = APIRouter()

# =========================
# INITIALIZE CORE OBJECTS
# =========================
source_manager = SourceManagerAgent()


# =========================
# IN-MEMORY SOURCE STORAGE
# =========================
INGESTED_SOURCES: Dict[str, dict] = {}

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# HEALTH CHECK
# =========================
@router.get("/")
def health():
    return {
        "status": "AquilaFAQ running",
        "sources_loaded": len(INGESTED_SOURCES)
    }

# =========================
# DOCUMENT INGESTION
# =========================
@router.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    source_data = source_manager.ingest_document(file_path)
    INGESTED_SOURCES[source_data["source_id"]] = source_data

    return {
        "message": "Document ingested successfully",
        "source_id": source_data["source_id"],
        "type": "document"
    }

# =========================
# WEB INGESTION
# =========================
@router.post("/ingest/web")
def ingest_web(url: str):
    if not url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL"
        )

    source_data = source_manager.ingest_web(url)
    INGESTED_SOURCES[source_data["source_id"]] = source_data

    return {
        "message": "Web content ingested successfully",
        "source_id": source_data["source_id"],
        "type": "web",
        "domain": source_data.get("domain")
    }

# =========================
# FAQ GENERATION (ASYNC)
# =========================
@router.post("/generate/faq")
def generate_faq(source_id: str, num_faqs: int = 5):
    if source_id not in INGESTED_SOURCES:
        raise HTTPException(
            status_code=404,
            detail="Source ID not found"
        )

    if num_faqs < 1 or num_faqs > 20:
        raise HTTPException(
            status_code=400,
            detail="num_faqs must be between 1 and 20"
        )

    task_id = task_manager.create_task()

    # Start background processing
    start_task(
        task_id=task_id,
        source_data=INGESTED_SOURCES[source_id],
        num_faqs=num_faqs
    )

    return {
        "message": "FAQ generation started",
        "task_id": task_id,
        "status": "queued"
    }

# =========================
# FETCH RESULTS
# =========================
@router.get("/results/{task_id}")
def get_results(task_id: str):
    task = task_manager.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task ID not found"
        )

    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task.get("result")
    }
