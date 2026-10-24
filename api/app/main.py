import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_base_dir = os.path.abspath(os.path.join(_current_dir, "../.."))
_api_dir = os.path.abspath(os.path.join(_current_dir, ".."))
for _p in [_base_dir, _api_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.app.config import settings
from api.app.schemas.common import ErrorResponse, ErrorPayload, HealthResponse
from api.app.routes import (
    health,
    auth,
    student,
    bcs,
    admin,
    gvcn,
    files,
    notifications,
    internal,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend Shell - Hệ thống Chấm Điểm Rèn Luyện (Giai đoạn 0)"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standard Error Handler for HTTP Exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
    }
    error_code = getattr(exc, "code", code_map.get(exc.status_code, f"HTTP_{exc.status_code}"))
    payload = ErrorPayload(
        code=error_code,
        message=str(exc.detail),
        fields=getattr(exc, "fields", {})
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=payload).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    field_errors = {}
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        field_errors[loc] = err.get("msg", "Invalid value")

    payload = ErrorPayload(
        code="VALIDATION_ERROR",
        message="Dữ liệu gửi lên không đúng định dạng",
        fields=field_errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error=payload).model_dump()
    )


# Root health checks
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def root_health():
    return HealthResponse(status="ok")


# Include API V1 Routers with prefix
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(student.router, prefix=settings.API_V1_PREFIX)
app.include_router(bcs.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(gvcn.router, prefix=settings.API_V1_PREFIX)
app.include_router(files.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
app.include_router(internal.router, prefix=settings.API_V1_PREFIX)
