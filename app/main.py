from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

docs_url = "/docs" if (settings.ENV == "dev" or settings.DOCS_ENABLED) else None
redoc_url = "/redoc" if (settings.ENV == "dev" or settings.DOCS_ENABLED) else None
openapi_url = "/openapi.json" if (settings.ENV == "dev" or settings.DOCS_ENABLED) else None

app = FastAPI(
    title=settings.APP_NAME,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.include_router(api_router)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.ENV == "prod" and settings.allowed_hosts_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )

if settings.ALLOWED_ORIGINS_LIST:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.middleware("http")
async def secure_headers(request: Request, call_next):
    resp = await call_next(request)
    if settings.ENV == "prod" and settings.SECURE_HEADERS:
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
    return resp

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}

if settings.ENV == "dev":
    @app.post("/debug/body")
    async def debug_body(req: Request):
        raw = await req.body()
        return {"raw": raw.decode("utf-8", errors="ignore")}
