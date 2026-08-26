import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.agents.source_manager import SourceManagerAgent
from app.agents.domain_agent import DomainAgent
from app.agents.language_agent import LanguageAgent
from app.agents.translator_agent import TranslatorAgent
from app.utils.task_manager import task_manager
from app.utils.background_worker import start_task, start_learn_task
from app.auth.auth_handler import decode_access_token, get_password_hash, verify_password, create_access_token
from app.database.mongodb import db
from app.config import SUPPORTED_LANGUAGES, STUDY_MODES, ALLOWED_DOC_EXTS, ALLOWED_IMAGE_EXTS, MAX_FILE_SIZE_DOC, MAX_FILE_SIZE_IMAGE
import tempfile
import os

router = APIRouter()
source_manager = SourceManagerAgent()
domain_agent = DomainAgent()
language_agent = LanguageAgent()
translator_agent = TranslatorAgent()

from pydantic import BaseModel, EmailStr

class UserAuth(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None

class WebIngest(BaseModel):
    url: str

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        return None
    token = authorization.split(" ")[-1]
    payload = decode_access_token(token)
    if not payload:
        return None
    return payload.get("sub")

@router.post("/auth/signup")
async def signup(user: UserAuth):
    email = user.email.lower()
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)
    db.users.insert_one({
        "name": user.name,
        "email": email,
        "password": hashed_pw,
        "created_at": datetime.utcnow()
    })
    return {"message": "User created successfully"}

@router.post("/auth/login")
async def login(user: UserAuth):
    email = user.email.lower()
    db_user = db.users.find_one({"email": email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": email})
    return {"access_token": token, "token_type": "bearer"}

def _ext_from_filename(name: str) -> str:
    return os.path.splitext(name.lower())[1] if name else ""

@router.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    ext = _ext_from_filename(file.filename or "")
    is_image = ext in ALLOWED_IMAGE_EXTS
    max_size = MAX_FILE_SIZE_IMAGE if is_image else MAX_FILE_SIZE_DOC

    if ext and ext not in ALLOWED_DOC_EXTS and ext not in ALLOWED_IMAGE_EXTS:

        ext = ".pdf" if (file.filename or "").lower().endswith(".pdf") or not ext else ext
        if ext not in ALLOWED_DOC_EXTS and ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type {ext}. Allowed: {ALLOWED_DOC_EXTS | ALLOWED_IMAGE_EXTS}")

    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large (Max {max_size//(1024*1024)}MB)")

    suffix = ext if ext else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:

        if is_image:
            source_id = await source_manager.ingest_image(temp_path, user_id=user_id)
        elif ext in {".txt", ".docx", ".pptx"}:
            source_id = source_manager.ingest_file(temp_path, ext, user_id=user_id)
        else:
            source_id = source_manager.ingest_document(temp_path, user_id=user_id)

        source_data = source_manager.get_source(source_id)

        topics = await domain_agent.detect_topics(source_data["content"])

        all_text = " ".join([b.get("text","") for b in source_data["content"]])[:3000]
        detected_lang = await language_agent.detect(all_text)

        from app.database.mongodb import db as _db
        _db.sources.update_one({"source_id": source_id}, {"$set": {"language": detected_lang}})

        return {
            "message": "Document ingested successfully",
            "source_id": source_id,
            "topics": topics,
            "detected_language": detected_lang,
            "language_name": SUPPORTED_LANGUAGES.get(detected_lang, detected_lang),
            "filename": file.filename,
            "size": f"{len(content)/1024:.1f} KB"
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/ingest/web")
async def ingest_web(data: WebIngest, user_id: str = Depends(get_current_user)):

    from urllib.parse import urlparse
    parsed = urlparse(data.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")
    if any(x in parsed.netloc for x in ["localhost", "127.0.0.1", "0.0.0.0", "::1", "10.", "192.168."]):

        if "localhost" in parsed.netloc or parsed.netloc.startswith("127.") or parsed.netloc.startswith("10.") :
            raise HTTPException(status_code=400, detail="Private URL not allowed")
    source_id = source_manager.ingest_web(data.url, user_id=user_id)
    source_data = source_manager.get_source(source_id)
    topics = await domain_agent.detect_topics(source_data["content"])
    all_text = " ".join([b.get("text","") for b in source_data["content"]])[:3000]
    detected_lang = await language_agent.detect(all_text)
    from app.database.mongodb import db as _db2
    _db2.sources.update_one({"source_id": source_id}, {"$set": {"language": detected_lang}})
    return {
        "source_id": source_id,
        "topics": topics,
        "detected_language": detected_lang,
        "language_name": SUPPORTED_LANGUAGES.get(detected_lang, detected_lang),
        "url": data.url
    }

@router.get("/languages")
def list_languages():
    return SUPPORTED_LANGUAGES

@router.get("/modes")
def list_modes():
    return {"modes": STUDY_MODES}

@router.post("/generate/learn")
async def generate_learn(
    source_id: str,
    mode: str = "faq",
    num_items: int = 5,
    target_domain: str = "auto",
    language: str = "auto",
    user_id: str = Depends(get_current_user)
):
    mode = mode.lower().strip()
    if mode not in STUDY_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode {mode}. Allowed: {STUDY_MODES}")
    language = language_agent.normalize(language)
    if language != "auto" and language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language {language}")

    source_data = source_manager.get_source(source_id)
    if not source_data:
        raise HTTPException(status_code=404, detail="Source not found")

    if language == "auto":

        language = source_data.get("language") or "auto"
        if language == "auto":
            all_text = " ".join([b.get("text","") for b in source_data["content"]])[:2000]
            language = await language_agent.detect(all_text)

    from app.config import MAX_NUM_FAQS, MAX_NUM_CARDS, MAX_NUM_QUIZ
    caps = {"faq": MAX_NUM_FAQS, "flashcards": MAX_NUM_CARDS, "quiz": MAX_NUM_QUIZ}
    num_items = max(1, min(num_items, caps.get(mode, 15)))

    source_name = source_data.get("filename") or source_data.get("url") or "Document"
    task_id = task_manager.create_task(user_id=user_id, source_name=source_name, mode=mode, language=language, source_id=source_id)
    start_learn_task(task_id=task_id, source_data=source_data, num_items=num_items, target_domain=target_domain, target_language=language, mode=mode)
    return {"task_id": task_id, "mode": mode, "language": language, "source_id": source_id}

@router.post("/generate/faq")
async def generate_faq(source_id: str, num_faqs: int = 5, target_domain: str = "auto", user_id: str = Depends(get_current_user)):

    return await generate_learn(source_id=source_id, mode="faq", num_items=num_faqs, target_domain=target_domain, language="auto", user_id=user_id)

@router.post("/generate/flashcards")
async def generate_flashcards(source_id: str, num_cards: int = 8, target_domain: str = "auto", language: str = "auto", user_id: str = Depends(get_current_user)):
    return await generate_learn(source_id=source_id, mode="flashcards", num_items=num_cards, target_domain=target_domain, language=language, user_id=user_id)

@router.post("/generate/quiz")
async def generate_quiz(source_id: str, num_questions: int = 5, target_domain: str = "auto", language: str = "auto", user_id: str = Depends(get_current_user)):
    return await generate_learn(source_id=source_id, mode="quiz", num_items=num_questions, target_domain=target_domain, language=language, user_id=user_id)

@router.get("/user/history")
async def get_history(user_id: str = Depends(get_current_user)):
    if not user_id:
        return []
    return task_manager.get_user_tasks(user_id)

@router.delete("/task/{task_id}")
async def delete_task(task_id: str, user_id: str = Depends(get_current_user)):

    success = task_manager.delete_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or permission denied")
    return {"message": "Task deleted successfully"}

@router.get("/results/{task_id}")
async def get_results(task_id: str, user_id: str = Depends(get_current_user)):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.get("user_id") and task["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this task")

    return task

class TranslateRequest(BaseModel):
    target_language: str = "en"

@router.post("/translate/{task_id}")
async def translate_task(task_id: str, body: TranslateRequest, user_id: str = Depends(get_current_user)):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.get("user_id") and task["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    target = body.target_language.lower().strip()
    if target not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language {target}")
    if task.get("language") == target:
        return {"translated": task.get("result", []), "target_language": target}

    translated = await translator_agent.translate_task(task, target)
    if translated is None:
        raise HTTPException(status_code=500, detail="Translation failed")
    return {"translated": translated, "target_language": target, "mode": task.get("mode"), "original_language": task.get("language")}

@router.get("/health")
def health():
    from app.config import LLM_PROVIDER, ACTIVE_MODEL
    return {"status": "ok", "provider": LLM_PROVIDER, "model": ACTIVE_MODEL}
