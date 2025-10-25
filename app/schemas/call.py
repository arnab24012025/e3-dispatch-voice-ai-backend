from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.call import CallStatus


class CallCreate(BaseModel):
    """Schema for initiating a call"""
    driver_name: str
    phone_number: str
    load_number: str
    agent_configuration_id: int


class CallResponse(BaseModel):
    """Schema for call response"""
    id: int
    driver_name: str
    phone_number: str
    load_number: str
    agent_configuration_id: int
    retell_call_id: Optional[str] = None
    status: CallStatus
    duration: Optional[int] = None
    raw_transcript: Optional[str] = None
    structured_results: Optional[Dict[str, Any]] = None
    recording_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    """Schema for list of calls"""
    calls: list[CallResponse]
    total: int


class WebhookEvent(BaseModel):
    """Schema for Retell AI webhook events"""
    event_type: str
    call_id: str
    data: Dict[str, Any]


# Structured result schemas for different scenarios
class CheckInResult(BaseModel):
    """Structured result for check-in scenario"""
    call_outcome: str  # "In-Transit Update" OR "Arrival Confirmation"
    driver_status: str  # "Driving" OR "Delayed" OR "Arrived" OR "Unloading"
    current_location: Optional[str] = None
    eta: Optional[str] = None
    delay_reason: Optional[str] = None
    unloading_status: Optional[str] = None
    pod_reminder_acknowledged: bool = False


class EmergencyResult(BaseModel):
    """Structured result for emergency scenario"""
    call_outcome: str = "Emergency Escalation"
    emergency_type: str  # "Accident" OR "Breakdown" OR "Medical" OR "Other"
    safety_status: Optional[str] = None
    injury_status: Optional[str] = None
    emergency_location: Optional[str] = None
    load_secure: Optional[bool] = None
    escalation_status: str = "Connected to Human Dispatcher"