from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class LLMProviderUpdate(BaseModel):
    """Schema for updating LLM provider"""
    llm_provider: Literal["groq", "openai"]


class LLMProviderResponse(BaseModel):
    """Schema for LLM provider response"""
    llm_provider: str
    message: str = ""


class AvailableLLMsResponse(BaseModel):
    """Schema for available LLMs"""
    providers: list[str]
    default: str


class SystemSettingResponse(BaseModel):
    """Schema for system setting"""
    setting_key: str
    setting_value: str
    updated_at: datetime
    
    class Config:
        from_attributes = True