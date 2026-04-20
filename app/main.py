from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
import os

app = FastAPI(
    title="AquilaFAQ API",
    description="Multi-agent FAQ generation system",
    version="1.0.0"
)

# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "AquilaFAQ running"}
