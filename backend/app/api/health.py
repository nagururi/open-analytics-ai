from fastapi import APIRouter
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@router.get("/ollama")
async def ollama_health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "message": str(e)}
