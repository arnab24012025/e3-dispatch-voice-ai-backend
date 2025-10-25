from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.call import Call, CallStatus
from app.schemas.call import WebhookEvent
from app.services.transcript_processor import transcript_processor

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/retell")
async def retell_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint for Retell AI events
    
    This endpoint receives real-time updates from Retell AI during calls
    and processes them accordingly.
    """
    # Get request body
    body = await request.json()
    
    event_type = body.get("event")
    call_id = body.get("call_id")
    
    if not call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing call_id in webhook payload"
        )
    
    # Find call in database by Retell call ID
    call = db.query(Call).filter(Call.retell_call_id == call_id).first()
    
    if not call:
        # Log but don't fail - might be a call we don't track
        print(f"Received webhook for unknown call: {call_id}")
        return {"status": "ok", "message": "Call not found in database"}
    
    # Handle different event types
    if event_type == "call_started":
        call.status = CallStatus.IN_PROGRESS
        call.started_at = datetime.utcnow()
    
    elif event_type == "call_ended":
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.utcnow()
        
        # Get transcript and other data
        transcript = body.get("transcript", "")
        call.raw_transcript = transcript
        call.duration = body.get("duration")
        call.recording_url = body.get("recording_url")
        
        # Process transcript to extract structured data
        if transcript:
            try:
                agent_config = call.agent_configuration
                structured_data = transcript_processor.process_transcript(
                    transcript=transcript,
                    scenario_type=agent_config.scenario_type if agent_config else None
                )
                call.structured_results = structured_data
            except Exception as e:
                print(f"Error processing transcript: {e}")
                call.error_message = f"Transcript processing error: {str(e)}"
    
    elif event_type == "call_analyzed":
        # Update with analysis results if provided
        analysis = body.get("analysis", {})
        if analysis:
            # Merge with existing structured results
            if call.structured_results:
                call.structured_results.update(analysis)
            else:
                call.structured_results = analysis
    
    elif event_type == "call_failed":
        call.status = CallStatus.FAILED
        call.error_message = body.get("error_message", "Call failed")
        call.ended_at = datetime.utcnow()
    
    # Save updates
    db.commit()
    
    return {"status": "ok", "message": f"Processed {event_type} event"}


@router.post("/retell/llm")
async def retell_llm_webhook(request: Request, db: Session = Depends(get_db)):
    """
    LLM WebSocket endpoint for Retell AI
    
    This endpoint handles real-time conversation guidance during calls.
    Retell AI sends conversation state and expects guidance on what to say next.
    """
    body = await request.json()
    
    # Extract relevant data
    call_id = body.get("call_id")
    transcript = body.get("transcript", [])
    
    # Get call from database
    call = db.query(Call).filter(Call.retell_call_id == call_id).first()
    
    if not call:
        # Return generic response if call not found
        return {
            "response": "I'm having trouble accessing the call information. Please hold.",
            "end_call": False
        }
    
    # Get agent configuration
    agent_config = call.agent_configuration
    
    if not agent_config:
        return {
            "response": "Configuration error. Connecting you to a human representative.",
            "end_call": True
        }
    
    # Build context for LLM
    context = {
        "driver_name": call.driver_name,
        "load_number": call.load_number,
        "system_prompt": agent_config.system_prompt,
        "scenario_type": agent_config.scenario_type
    }
    
    # Here you would typically:
    # 1. Analyze the transcript so far
    # 2. Determine next action based on agent configuration
    # 3. Check for emergency keywords
    # 4. Generate appropriate response
    
    # For now, return a basic response structure
    # In production, this would use an LLM to generate dynamic responses
    
    return {
        "response": "I understand. Let me help you with that.",
        "end_call": False,
        "context": context
    }