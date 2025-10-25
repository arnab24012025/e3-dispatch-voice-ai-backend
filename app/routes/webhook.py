from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.call import Call, CallStatus
from app.schemas.call import WebhookEvent
from app.services.transcript_processor import transcript_processor

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/retell")
async def retell_webhook(request: Request, db: Session = Depends(get_db)):
    """HTTP Webhook endpoint for Retell AI call events"""
    body = await request.json()
    
    event_type = body.get("event")
    call_data = body.get("call", {})
    call_id = call_data.get("call_id")
    
    if not call_id:
        return {"status": "ok", "message": "No call_id provided"}
    
    # Find call in database
    call = db.query(Call).filter(Call.retell_call_id == call_id).first()
    
    if not call:
        print(f"Received webhook for unknown call: {call_id}")
        return {"status": "ok", "message": "Call not found"}
    
    # Handle events
    if event_type == "call_started":
        call.status = CallStatus.IN_PROGRESS
        call.started_at = datetime.utcnow()
    
    elif event_type == "call_ended":
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.utcnow()
        call.raw_transcript = call_data.get("transcript", "")
        call.recording_url = call_data.get("recording_url")
        
        # Calculate duration from timestamps
        start_ts = call_data.get("start_timestamp")
        end_ts = call_data.get("end_timestamp")
        if start_ts and end_ts:
            call.duration = (end_ts - start_ts) // 1000
        
        # Process transcript
        if call.raw_transcript:
            try:
                structured_data = transcript_processor.process_transcript(
                    transcript=call.raw_transcript,
                    scenario_type=call.agent_configuration.scenario_type if call.agent_configuration else None
                )
                call.structured_results = structured_data
            except Exception as e:
                print(f"Error processing transcript: {e}")
    
    elif event_type == "call_analyzed":
        call_analysis = call_data.get("call_analysis", {})
        if call_analysis:
            if call.structured_results:
                call.structured_results.update(call_analysis)
            else:
                call.structured_results = call_analysis
    
    db.commit()
    return {"status": "ok"}


@router.websocket("/retell/llm/{call_id}")
async def retell_llm_websocket(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for Retell AI Custom LLM
    
    Based on: https://docs.retellai.com/custom-llm/custom-llm-overview
    """
    await websocket.accept()
    print(f"✅ WebSocket connected for call: {call_id}")
    
    try:
        # CRITICAL: Send initial message immediately upon connection
        # This is required by Retell AI's protocol
        initial_message = {
            "response_id": 0,
            "content": "Hi, this is Dispatch calling about your delivery. How can I help you today?",
            "content_complete": True,
            "end_call": False
        }
        
        print(f"📤 Sending initial message: {initial_message}")
        await websocket.send_json(initial_message)
        
        # Now listen for messages from Retell
        while True:
            data = await websocket.receive_json()
            print(f"📥 RECEIVED from Retell: {data}")
            
            interaction_type = data.get("interaction_type")
            
            # Only respond when Retell explicitly requests a response
            if interaction_type == "response_required":
                response_id = data.get("response_id")
                transcript = data.get("transcript", [])
                
                # Get last user message
                last_user_message = ""
                if transcript:
                    for msg in reversed(transcript):
                        if msg.get("role") == "user":
                            last_user_message = msg.get("content", "")
                            break
                
                # Generate response based on context
                response_text = generate_response(last_user_message)
                
                response_data = {
                    "response_id": response_id,
                    "content": response_text,
                    "content_complete": True,
                    "end_call": False
                }
                
                print(f"📤 SENDING response: {response_data}")
                await websocket.send_json(response_data)
            
            elif interaction_type == "update_only":
                # Just log, don't respond
                print(f"⏭️ Update only - no response needed")
            
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected for call: {call_id}")
    except Exception as e:
        print(f"💥 WebSocket error: {e}")
        import traceback
        traceback.print_exc()


def generate_response(user_message: str) -> str:
    """
    Generate appropriate response based on user message
    
    In production, this would call an LLM like OpenAI GPT-4
    """
    user_message_lower = user_message.lower()
    
    # Simple keyword-based responses for demo
    if any(word in user_message_lower for word in ["hello", "hi", "hey"]):
        return "Hello! Thanks for answering. I'm calling about your delivery. Can you give me a quick status update?"
    
    elif any(word in user_message_lower for word in ["emergency", "accident", "crash", "breakdown"]):
        return "I understand this is an emergency. First, is everyone safe? What's your current location?"
    
    elif any(word in user_message_lower for word in ["delayed", "late", "stuck", "traffic"]):
        return "I see there's a delay. Can you tell me approximately how long you expect to be delayed?"
    
    elif any(word in user_message_lower for word in ["arrived", "here", "delivered"]):
        return "Great! Thank you for confirming delivery. Is there anything else you need assistance with?"
    
    elif any(word in user_message_lower for word in ["yes", "yeah", "yep"]):
        return "Perfect. Can you provide me with more details?"
    
    elif any(word in user_message_lower for word in ["no", "nope", "not really"]):
        return "Understood. Is there anything else I can help you with today?"
    
    else:
        return "I understand. Can you tell me more about your current delivery status?"