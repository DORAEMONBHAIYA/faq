import uuid
from datetime import datetime, timedelta
from app.database.mongodb import db
from app.agents.document_agent import DocumentAgent
from app.agents.web_agent import WebAgent

class SourceManagerAgent:
    def __init__(self):
        self.doc_agent = DocumentAgent()
        self.web_agent = WebAgent()
        self.collection = db.sources

    def ingest_document(self, file_path: str, user_id: str = None):
        """Ingests PDF and stores content in MongoDB with TTL."""
        res = self.doc_agent.ingest(file_path)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        
        # Retention Policy: 7 days for logged-in users, 1 hour for anonymous
        retention_days = 7 if user_id else 0
        retention_hours = 0 if user_id else 1
        expires_at = datetime.utcnow() + timedelta(days=retention_days, hours=retention_hours)

        source_data = {
            "source_id": source_id,
            "user_id": user_id,
            "type": "document",
            "filename": file_path.split("/")[-1].split("\\")[-1],
            "content": res["content"],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        
        self.collection.insert_one(source_data)
        return source_id

    def ingest_web(self, url: str, user_id: str = None):
        """Ingests Web URL and stores content in MongoDB with TTL."""
        # 🧪 OPTIMIZATION: Check if same user already ingested this URL recently (1 hour)
        existing = self.collection.find_one({
            "url": url, 
            "user_id": user_id, 
            "created_at": {"$gt": datetime.utcnow() - timedelta(hours=1)}
        })
        if existing:
            return existing["source_id"]

        res = self.web_agent.ingest(url)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        
        retention_days = 7 if user_id else 0
        retention_hours = 0 if user_id else 1
        expires_at = datetime.utcnow() + timedelta(days=retention_days, hours=retention_hours)

        source_data = {
            "source_id": source_id,
            "user_id": user_id,
            "type": "web",
            "url": url,
            "content": res["content"],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        
        self.collection.insert_one(source_data)
        return source_id

    def get_source(self, source_id: str):
        source = self.collection.find_one({"source_id": source_id})
        if source:
            source.pop("_id", None)
            return source
        return None

    def get_user_history(self, user_id: str):
        """Fetch valid (non-expired) source history for a user."""
        return list(self.collection.find(
            {"user_id": user_id, "expires_at": {"$gt": datetime.utcnow()}},
            {"_id": 0, "content": 0} # Don't return huge content in history list
        ).sort("created_at", -1))
