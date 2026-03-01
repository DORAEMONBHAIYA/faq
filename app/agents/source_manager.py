from app.agents.document_agent import DocumentAgent
from app.agents.web_agent import WebAgent

class SourceManagerAgent:
    def __init__(self):
        self.doc_agent = DocumentAgent()
        self.web_agent = WebAgent()

    def ingest_document(self, file_path: str):
        return self.doc_agent.ingest(file_path)

    def ingest_web(self, url: str):
        return self.web_agent.ingest(url)
