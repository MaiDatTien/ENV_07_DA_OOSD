import logging
import time

import pyodbc
from fastapi import FastAPI, Request
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


@app.exception_handler(pyodbc.Error)
async def on_db(_, e):
    log.error("SQL Server: %s", e)
    return JSONResponse(status_code=500, content={"detail": "Lỗi SQL Server, xem cửa sổ backend"})


app.include_router(public)
app.include_router(private)


@app.get("/", include_in_schema=False)
def root():
    return {"app": "ENV-07 backend", "docs": "/docs", "frontend": "http://localhost:5173"}
