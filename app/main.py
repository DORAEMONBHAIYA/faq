from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="AquilaFAQ API",
    description="Multi-agent FAQ generation system",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def health():
    return {"status": "AquilaFAQ running"}
