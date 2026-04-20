import uuid
from datetime import datetime
from app.database.mongodb import db
from app.agents.document_agent import DocumentAgent
from app.agents.web_agent import WebAgent

class SourceManagerAgent:
    def __init__(self):
        self.doc_agent = DocumentAgent()
        self.web_agent = WebAgent()
        self.collection = db.sources

    def ingest_document(self, file_path: str):
        res = self.doc_agent.ingest(file_path)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        
        source_data = {
            "source_id": source_id,
            "type": "document",
            "path": file_path,
            "content": res["content"],
            "created_at": datetime.utcnow()
        }
        
        self.collection.insert_one(source_data)
        return source_id

    def ingest_web(self, url: str):
        res = self.web_agent.ingest(url)
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        
        source_data = {
            "source_id": source_id,
            "type": "web",
            "url": url,
            "content": res["content"],
            "created_at": datetime.utcnow()
        }
        
        self.collection.insert_one(source_data)
        return source_id

    def get_source(self, source_id: str):
        source = self.collection.find_one({"source_id": source_id})
        if source:
            source.pop("_id", None)
            return source
        return None
