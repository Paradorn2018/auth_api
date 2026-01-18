from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from fastapi import Request

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}


@app.post("/debug/body")
async def debug_body(req: Request):
    raw = await req.body()
    return {"raw": raw.decode("utf-8", errors="ignore")}
