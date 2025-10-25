from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class VoiceSettings(BaseModel):
    """Voice settings for Retell AI agent"""
    enable_backchannel: bool = True
    backchannel_frequency: str = "medium"  # low, medium, high
    enable_filler_words: bool = True
    interruption_sensitivity: int = 5  # 1-10 scale
    voice_speed: float = 1.0
    voice_id: Optional[str] = None


class AgentConfigurationBase(BaseModel):
    """Base schema for agent configuration"""
    name: str
    description: Optional[str] = None
    system_prompt: str
    initial_message: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    scenario_type: Optional[str] = None


class AgentConfigurationCreate(AgentConfigurationBase):
    """Schema for creating agent configuration"""
    pass


class AgentConfigurationUpdate(BaseModel):
    """Schema for updating agent configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    initial_message: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    scenario_type: Optional[str] = None
    is_active: Optional[bool] = None


class AgentConfigurationResponse(AgentConfigurationBase):
    """Schema for agent configuration response"""
    id: int
    retell_agent_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True