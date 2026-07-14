from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import audit, chat, completeness, contradictions, documents, graph, obligations, playbook, redline, report

app = FastAPI(title="LexTwin AI - Contract & SOW Risk Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(completeness.router, prefix="/api/completeness", tags=["completeness"])
app.include_router(contradictions.router, prefix="/api/contradictions", tags=["contradictions"])
app.include_router(redline.router, prefix="/api/redline", tags=["redline"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(playbook.router, prefix="/api/playbook", tags=["playbook"])
app.include_router(obligations.router, prefix="/api/obligations", tags=["obligations"])
app.include_router(report.router, prefix="/api/report", tags=["report"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
