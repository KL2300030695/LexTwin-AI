from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import documents

app = FastAPI(title="LexTwin AI - Contract & SOW Risk Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
