import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.agents.source_manager import SourceManagerAgent
from app.agents.domain_agent import DomainAgent
from app.utils.task_manager import task_manager
from app.utils.background_worker import start_task
from app.auth.auth_handler import decode_access_token, get_password_hash, verify_password, create_access_token
from app.database.mongodb import db

router = APIRouter()
source_manager = SourceManagerAgent()
domain_agent = DomainAgent()

from pydantic import BaseModel, EmailStr

# 🛡️ Auth Models
class UserAuth(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None

class WebIngest(BaseModel):
    url: str

# 🛡️ Dependency to get current user
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        return None
    token = authorization.split(" ")[-1]
    payload = decode_access_token(token)
    if not payload:
        return None
    return payload.get("sub") # returns email as user_id

# =========================
# AUTH ENDPOINTS
# =========================
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

# =========================
# DOCUMENT INGESTION
# =========================
@router.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    # 📏 Limit size to 3MB
    MAX_SIZE = 3 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (Max 3MB)")

    # 🛡️ SECURITY: Use system temp directory instead of local data folder
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        # Ingest and store
        source_id = source_manager.ingest_document(temp_path, user_id=user_id)
        source_data = source_manager.get_source(source_id)
        
        # Detect dynamic topics
        topics = await domain_agent.detect_topics(source_data["content"])

        return {
            "message": "Document ingested successfully",
            "source_id": source_id,
            "topics": topics,
            "filename": file.filename,
            "size": f"{len(content)/1024:.1f} KB"
        }
    finally:
        # 🛡️ ALWAYS cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/ingest/web")
async def ingest_web(data: WebIngest, user_id: str = Depends(get_current_user)):
    source_id = source_manager.ingest_web(data.url, user_id=user_id)
    source_data = source_manager.get_source(source_id)
    topics = await domain_agent.detect_topics(source_data["content"])

    return {
        "source_id": source_id,
        "topics": topics,
        "url": data.url
    }

# =========================
# FAQ GENERATION
# =========================
@router.post("/generate/faq")
async def generate_faq(source_id: str, num_faqs: int = 5, target_domain: str = "auto", user_id: str = Depends(get_current_user)):
    source_data = source_manager.get_source(source_id)
    if not source_data:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Extract friendly name for history
    source_name = source_data.get("filename") or source_data.get("url") or "Document"
    
    task_id = task_manager.create_task(user_id=user_id, source_name=source_name)
    start_task(task_id=task_id, source_data=source_data, num_faqs=num_faqs, target_domain=target_domain)
    
    return {"task_id": task_id}

# =========================
# HISTORY & RESULTS
# =========================
@router.get("/user/history")
async def get_history(user_id: str = Depends(get_current_user)):
    if not user_id:
        return []
    return task_manager.get_user_tasks(user_id)

@router.delete("/task/{task_id}")
async def delete_task(task_id: str, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    success = task_manager.delete_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or not owned by user")
    return {"message": "Task deleted successfully"}

@router.get("/results/{task_id}")
async def get_results(task_id: str, user_id: str = Depends(get_current_user)):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 🛡️ SECURITY: Ensure privacy (Users can only see their own tasks)
    if task.get("user_id") and task["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this task")
        
    return task

@router.get("/health")
def health():
    return {"status": "ok"}
