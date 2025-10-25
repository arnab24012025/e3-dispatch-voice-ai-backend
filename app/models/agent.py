from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AgentConfiguration(Base):
    """Agent configuration model - stores prompts and settings"""
    
    __tablename__ = "agent_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # e.g., "Dispatch Check-in Agent"
    description = Column(Text, nullable=True)
    
    # Agent prompts and instructions
    system_prompt = Column(Text, nullable=False)
    initial_message = Column(String, nullable=True)
    
    # Voice settings (Retell AI configuration)
    voice_settings = Column(JSON, nullable=True)  # Stores backchanneling, filler words, etc.
    
    # Retell AI agent ID (if created)
    retell_agent_id = Column(String, nullable=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Scenario type
    scenario_type = Column(String, nullable=True)  # "check-in", "emergency", etc.
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    calls = relationship("Call", back_populates="agent_configuration")
    
    def __repr__(self):
        return f"<AgentConfiguration {self.name}>"