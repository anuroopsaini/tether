from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.analyses import router

settings = get_settings()
app = FastAPI(
    title="Tether API",
    version="0.1.0",
    description="Evidence-backed claim review for student applications.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

# Keep the dashboard and API in one deployable application. The API routes above
# take precedence; all other root paths resolve to the static frontend.
FRONTEND_DIR = Path(__file__).resolve().parent.parent
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
