from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse, Response

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.limiter import limiter


# -----------------------------
# FastAPI docs / openapi toggle
# -----------------------------
docs_on = (settings.ENV == "dev") or (settings.ENV == "prod" and settings.LOCAL_PROD and settings.DOCS_ENABLED)

docs_url = "/docs" if docs_on else None
redoc_url = "/redoc" if docs_on else None
openapi_url = "/openapi.json" if docs_on else None


app = FastAPI(
    title=settings.APP_NAME,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.include_router(api_router)

# -----------------------------
# Rate limit
# -----------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -----------------------------
# Trusted hosts (prod only)
# -----------------------------
if settings.ENV == "prod" and settings.allowed_hosts_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )

# -----------------------------
# CORS
# -----------------------------
if settings.allowed_origins_list:
    strict = (settings.ENV == "prod") and getattr(settings, "CORS_STRICT_IN_PROD", True)

    if strict:
        allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        allow_headers = ["Authorization", "Content-Type"]
    else:
        allow_methods = ["*"]
        allow_headers = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", True),
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )

# -----------------------------
# Security headers (prod only)
# -----------------------------
@app.middleware("http")
async def security_and_docs_guard(request: Request, call_next):
    # 1) Protect docs in prod if enabled (optional but recommended)
    #    - If DOCS_ENABLED true in prod, require x-docs-key == DOCS_KEY
    if settings.ENV == "prod" and request.url.path in ("/docs", "/redoc", "/openapi.json"):
        if settings.DOCS_ENABLED:
            docs_key = getattr(settings, "DOCS_KEY", None)
            if not docs_key:
                return JSONResponse({"detail": "Not found"}, status_code=404)

            provided = request.headers.get("x-docs-key")
            if provided != docs_key:
                return JSONResponse({"detail": "Not found"}, status_code=404)
        else:
            # docs disabled => behave like not found
            return JSONResponse({"detail": "Not found"}, status_code=404)

    resp: Response = await call_next(request)

    # 2) Add security headers (prod only)
    if settings.ENV == "prod" and settings.SECURE_HEADERS:
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"

        # Recommended additional headers
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # API-friendly CSP (ค่อนข้างเข้ม เหมาะกับ backend API)
        resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # HSTS: เปิดเฉพาะตอนขึ้น HTTPS จริงเท่านั้น (อย่าเปิดตอน prod local ที่เป็น http)
        if getattr(settings, "ENABLE_HSTS", False):
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return resp


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}


# dev-only debug endpoint
if settings.ENV == "dev":
    @app.post("/debug/body")
    async def debug_body(req: Request):
        raw = await req.body()
        return {"raw": raw.decode("utf-8", errors="ignore")}
