import logging
import time

import pyodbc
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .domain import DomainError
from .routes import private, public
from .services import AuthError, NotFound

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("env07")

app = FastAPI(title="ENV-07 Quản lý nước tưới", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.FRONTEND_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(DomainError)
async def on_domain(_, e):
    return JSONResponse(status_code=400, content={"detail": str(e)})


@app.exception_handler(AuthError)
async def on_auth(_, e):
    return JSONResponse(status_code=401, content={"detail": str(e)})


@app.exception_handler(NotFound)
async def on_not_found(_, e):
    return JSONResponse(status_code=404, content={"detail": str(e)})


FIELD_VI = {
    "moisture_min": "Ẩm thấp nhất (%)", "moisture_max": "Ẩm cao nhất (%)", "duration_days": "Số ngày",
    "daily_quota_liters": "Hạn mức (lít / ngày)", "max_liters_per_watering": "Tối đa mỗi lần tưới (lít)",
    "liters": "Số lít", "volume_liters": "Lượng nước (lít)", "planted_date": "Ngày trồng",
    "soil_moisture": "Độ ẩm đất (%)", "crop_id": "Loại cây", "name": "Tên", "reason": "Lý do",
    "dim": "Độ tối lớp phủ", "pumped_sec": "Số giây bơm",
}


def _vi(err: dict) -> str:
    field = next((str(x) for x in reversed(err.get("loc", [])) if isinstance(x, str) and x != "body"), "")
    label = FIELD_VI.get(field, field)
    ctx = err.get("ctx") or {}
    t = err.get("type", "")
    if t == "greater_than_equal":
        why = f"phải lớn hơn hoặc bằng {ctx.get('ge')}"
    elif t == "less_than_equal":
        why = f"không được lớn hơn {ctx.get('le')}"
    elif t == "greater_than":
        why = f"phải lớn hơn {ctx.get('gt')}"
    elif t == "less_than":
        why = f"phải nhỏ hơn {ctx.get('lt')}"
    elif t == "missing":
        why = "chưa nhập"
    elif t in ("float_parsing", "int_parsing", "float_type", "int_type", "int_from_float"):
        why = "phải là số hợp lệ"
    elif t.startswith("date"):
        why = "không phải ngày hợp lệ"
    elif t in ("string_too_short", "string_too_long"):
        why = "có độ dài không hợp lệ"
    else:
        why = "không hợp lệ"
    return f"{label} {why}".strip()


@app.exception_handler(RequestValidationError)
async def on_validation(_, e: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "; ".join(dict.fromkeys(_vi(x) for x in e.errors()))})


@app.exception_handler(pyodbc.Error)
async def on_db(_, e):
    log.error("SQL Server: %s", e)
    return JSONResponse(status_code=500, content={"detail": "Lỗi SQL Server, xem cửa sổ backend"})


app.include_router(public)
app.include_router(private)


@app.get("/", include_in_schema=False)
def root():
    return {"app": "ENV-07 backend", "docs": "/docs", "frontend": "http://localhost:5173"}
