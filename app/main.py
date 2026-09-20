from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Return the stable API error envelope consumed by browser clients."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("error"), dict):
        error = detail["error"]
        return error_response(
            exc.status_code,
            str(error.get("code", "HTTP_ERROR")),
            str(error.get("message", "Request failed")),
        )
    return error_response(exc.status_code, "HTTP_ERROR", str(detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "Invalid request")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "Internal server error")

# Keep the dashboard and API in one deployable application. The API routes above
# take precedence; all other root paths resolve to the static frontend.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "dist"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
