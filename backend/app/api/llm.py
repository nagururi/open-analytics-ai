from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.services.llm_service import LLMService

router = APIRouter()
llm = LLMService()


@router.get("/models")
async def list_models(user=Depends(get_current_user)):
    models = await llm.list_models()
    return {"models": models}


@router.get("/status")
async def llm_status(user=Depends(get_current_user)):
    models = await llm.list_models()
    return {
        "connected": len(models) > 0,
        "models": models,
        "default_model": llm.model,
        "ollama_url": llm.base_url,
    }
