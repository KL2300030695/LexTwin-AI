from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.routers import auth, audit, chat, completeness, contradictions, documents, graph, obligations, playbook, redline, report

app = FastAPI(title="LexTwin AI - Contract & SOW Risk Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every route below requires a verified Firebase ID token (get_current_user)
# at minimum -- there is no endpoint left open to an unauthenticated caller.
# audit.py and playbook.py additionally layer role checks (require_role) on
# top of this on specific routes (see those routers), since "authenticated"
# and "authorized for this specific action" are different questions.
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"], dependencies=[Depends(get_current_user)])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"], dependencies=[Depends(get_current_user)])
app.include_router(completeness.router, prefix="/api/completeness", tags=["completeness"], dependencies=[Depends(get_current_user)])
app.include_router(contradictions.router, prefix="/api/contradictions", tags=["contradictions"], dependencies=[Depends(get_current_user)])
app.include_router(redline.router, prefix="/api/redline", tags=["redline"], dependencies=[Depends(get_current_user)])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(playbook.router, prefix="/api/playbook", tags=["playbook"])
app.include_router(obligations.router, prefix="/api/obligations", tags=["obligations"], dependencies=[Depends(get_current_user)])
app.include_router(report.router, prefix="/api/report", tags=["report"], dependencies=[Depends(get_current_user)])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"], dependencies=[Depends(get_current_user)])


@app.get("/api/health")
def health():
    return {"status": "ok"}
