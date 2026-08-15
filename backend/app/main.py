from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import chat, documents, eval as eval_router
from app.services.ingest import ensure_upload_dir

app = FastAPI(
    title="SpecGround",
    description="Grounded Q&A over engineering standards, datasheets, and manuals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(eval_router.router)


@app.on_event("startup")
def on_startup():
    ensure_upload_dir()
    init_db()


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "name": "SpecGround",
        "anthropic_configured": settings.anthropic_configured,
        "llm": "anthropic" if settings.anthropic_configured else "none",
    }
