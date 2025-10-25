from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.call import Call, CallStatus
from app.models.agent import AgentConfiguration
from app.models.user import User
from app.schemas.call import CallCreate, CallResponse, CallListResponse
from app.utils.dependencies import get_current_user
from app.services.retell_service import retell_service

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(
    call_data: CallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiate a new call to a driver
    """
    # Get agent configuration
    agent = db.query(AgentConfiguration).filter(
        AgentConfiguration.id == call_data.agent_configuration_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent configuration not found"
        )
    
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent configuration is not active"
        )
    
    # Create call record
    db_call = Call(
        driver_name=call_data.driver_name,
        phone_number=call_data.phone_number,
        load_number=call_data.load_number,
        agent_configuration_id=call_data.agent_configuration_id,
        initiated_by=current_user.id,
        status=CallStatus.INITIATED
    )
    
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    
    # Initiate call via Retell AI
    try:
        # Prepare metadata
        metadata = {
            "call_id": db_call.id,
            "driver_name": call_data.driver_name,
            "load_number": call_data.load_number
        }
        
        # Use agent's Retell AI ID or fallback to configured agent ID
        agent_id = agent.retell_agent_id or "default-agent-id"
        
        retell_response = await retell_service.create_phone_call(
            to_number=call_data.phone_number,
            agent_id=agent_id,
            metadata=metadata
        )
        
        # Update call with Retell call ID
        db_call.retell_call_id = retell_response.get("call_id")
        db_call.status = CallStatus.RINGING
        db_call.started_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_call)
        
    except Exception as e:
        # Mark call as failed
        db_call.status = CallStatus.FAILED
        db_call.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )
    
    return db_call


@router.get("/", response_model=CallListResponse)
async def list_calls(
    skip: int = 0,
    limit: int = 100,
    load_number: str = None,
    status_filter: CallStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all calls with optional filters
    """
    query = db.query(Call)
    
    # Apply filters
    if load_number:
        query = query.filter(Call.load_number == load_number)
    
    if status_filter:
        query = query.filter(Call.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    calls = query.order_by(Call.created_at.desc()).offset(skip).limit(limit).all()
    
    return CallListResponse(calls=calls, total=total)


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific call by ID
    """
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return call


@router.get("/{call_id}/refresh", response_model=CallResponse)
async def refresh_call_status(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refresh call status from Retell AI
    """
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    if not call.retell_call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call does not have a Retell AI call ID"
        )
    
    try:
        # Get call details from Retell AI
        retell_call = await retell_service.get_call_details(call.retell_call_id)
        
        # Update call status
        call.status = CallStatus(retell_call.get("status", "completed"))
        call.duration = retell_call.get("duration")
        call.raw_transcript = retell_call.get("transcript")
        call.recording_url = retell_call.get("recording_url")
        
        if call.status == CallStatus.COMPLETED:
            call.ended_at = datetime.utcnow()
        
        db.commit()
        db.refresh(call)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh call status: {str(e)}"
        )
    
    return call