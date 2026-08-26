import uuid
import os
from datetime import datetime, timedelta
from app.database.mongodb import db
from app.agents.document_agent import DocumentAgent
from app.agents.web_agent import WebAgent
from app.agents.file_agent import FileAgent

class SourceManagerAgent:
    def __init__(self):
        self.doc_agent = DocumentAgent()
        self.web_agent = WebAgent()
        self.file_agent = FileAgent()
        self.collection = db.sources

    def _make_source_doc(self, source_id, user_id, doc_type, content, language="auto", extra=None):
        retention_days = 7 if user_id else 0
        retention_hours = 0 if user_id else 1
        expires_at = datetime.utcnow() + timedelta(days=retention_days, hours=retention_hours)
        doc = {
            "source_id": source_id,
            "user_id": user_id,
            "type": doc_type,
            "content": content,
            "language": language,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        if extra:
            doc.update(extra)
        return doc

    def ingest_document(self, file_path: str, user_id: str = None, language: str = "auto"):
        """Ingests PDF and stores content in MongoDB with TTL."""
        res = self.doc_agent.ingest(file_path)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        source_data = self._make_source_doc(
            source_id, user_id, "document", res["content"], language,
            extra={"filename": file_path.split("/")[-1].split("\\")[-1]}
        )
        self.collection.insert_one(source_data)
        return source_id

    def ingest_file(self, file_path: str, ext: str, user_id: str = None, language: str = "auto"):
        """Ingest txt/docx/pptx via FileAgent."""
        res = self.file_agent.ingest(file_path, ext)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        source_data = self._make_source_doc(
            source_id, user_id, "document", res["content"], language,
            extra={"filename": os.path.basename(file_path)}
        )
        self.collection.insert_one(source_data)
        return source_id

    async def ingest_image(self, file_path: str, user_id: str = None, language: str = "auto"):
        """Ingest image via Gemini Vision OCR."""
        from app.agents.image_agent import ImageAgent
        agent = ImageAgent()
        res = await agent.ingest(file_path)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        source_data = self._make_source_doc(
            source_id, user_id, "image", res["content"], language,
            extra={"filename": os.path.basename(file_path)}
        )
        self.collection.insert_one(source_data)
        return source_id

    def ingest_web(self, url: str, user_id: str = None, language: str = "auto"):
        """Ingests Web URL and stores content in MongoDB with TTL."""
        existing = self.collection.find_one({
            "url": url,
            "user_id": user_id,
            "created_at": {"$gt": datetime.utcnow() - timedelta(hours=1)}
        })
        if existing:
            return existing["source_id"]
        res = self.web_agent.ingest(url)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        source_data = self._make_source_doc(
            source_id, user_id, "web", res["content"], language,
            extra={"url": url}
        )
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
            {"_id": 0, "content": 0}
        ).sort("created_at", -1))
