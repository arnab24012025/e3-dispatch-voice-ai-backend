from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.settings import (
    LLMProviderUpdate,
    LLMProviderResponse,
    AvailableLLMsResponse
)
from app.utils.dependencies import get_current_user
from app.services.settings_service import get_setting, set_setting

from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMProviderResponse)
async def get_current_llm_provider(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current LLM provider setting"""
    provider = get_setting(db, "llm_provider", default="groq")
    return LLMProviderResponse(
        llm_provider=provider,
        message=f"Current LLM provider is {provider}"
    )


@router.put("/llm", response_model=LLMProviderResponse)
async def update_llm_provider(
    update_data: LLMProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update LLM provider setting (admin only)"""
    
    # Validate provider
    if update_data.llm_provider not in ["groq", "openai"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid LLM provider. Must be 'groq' or 'openai'"
        )
    
    # Check if API key is configured for selected provider
    if update_data.llm_provider == "groq" and not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Groq API key not configured in environment"
        )
    
    if update_data.llm_provider == "openai" and not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI API key not configured in environment"
        )
    
    # Update setting
    set_setting(db, "llm_provider", update_data.llm_provider)
    
    return LLMProviderResponse(
        llm_provider=update_data.llm_provider,
        message=f"LLM provider updated to {update_data.llm_provider}"
    )


@router.get("/llms/available", response_model=AvailableLLMsResponse)
async def get_available_llms(
    current_user: User = Depends(get_current_user)
):
    """Get list of available LLM providers"""
    available = []
    
    if settings.GROQ_API_KEY:
        available.append("groq")
    
    if settings.OPENAI_API_KEY:
        available.append("openai")
    
    return AvailableLLMsResponse(
        providers=available,
        default="groq"
    )