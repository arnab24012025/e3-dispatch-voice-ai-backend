from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class CallStatus(str, enum.Enum):
    """Call status enumeration"""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class Call(Base):
    """Call record model - stores call details and results"""
    
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Call context
    driver_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    load_number = Column(String, nullable=False, index=True)
    
    # Agent reference
    agent_configuration_id = Column(Integer, ForeignKey("agent_configurations.id"), nullable=False)
    
    # Retell AI call ID
    retell_call_id = Column(String, nullable=True, index=True)
    
    # Call status
    status = Column(Enum(CallStatus), default=CallStatus.INITIATED)
    
    # Call duration (in seconds)
    duration = Column(Integer, nullable=True)
    
    # Raw transcript from Retell AI
    raw_transcript = Column(Text, nullable=True)
    
    # Structured results (extracted data)
    structured_results = Column(JSON, nullable=True)
    
    # Recording URL (if available)
    recording_url = Column(String, nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    
    # Metadata
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agent_configuration = relationship("AgentConfiguration", back_populates="calls")
    
    def __repr__(self):
        return f"<Call {self.load_number} - {self.driver_name}>"