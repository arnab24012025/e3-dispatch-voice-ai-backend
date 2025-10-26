from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.call import Call, CallStatus
from app.schemas.call import WebhookEvent
from app.services.transcript_processor import transcript_processor
from app.services.llm_service import llm_service
from app.services.settings_service import get_setting
from app.models.agent import AgentConfiguration
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Function definitions for LLM
FUNCTIONS = [
    {
        "name": "update_delivery_status",
        "description": "Update the driver's delivery status with current information",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["driving", "delayed", "arrived", "unloading"],
                    "description": "Current delivery status"
                },
                "eta": {
                    "type": "string",
                    "description": "Estimated time of arrival"
                },
                "location": {
                    "type": "string",
                    "description": "Current location or address"
                },
                "delay_reason": {
                    "type": "string",
                    "description": "Reason for delay if applicable"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or comments"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "report_emergency",
        "description": "Report an emergency situation that requires immediate attention",
        "parameters": {
            "type": "object",
            "properties": {
                "emergency_type": {
                    "type": "string",
                    "enum": ["accident", "breakdown", "medical", "other"],
                    "description": "Type of emergency"
                },
                "location": {
                    "type": "string",
                    "description": "Current location of emergency"
                },
                "safety_status": {
                    "type": "string",
                    "description": "Safety status of driver and others"
                },
                "injury_status": {
                    "type": "string",
                    "description": "Information about any injuries"
                },
                "load_secure": {
                    "type": "boolean",
                    "description": "Whether the load is secure"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the emergency"
                }
            },
            "required": ["emergency_type", "location"]
        }
    },
    {
        "name": "end_conversation",
        "description": "End the conversation when all required information has been collected",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for ending conversation"
                }
            },
            "required": []
        }
    }
]


async def post_process_transcript_with_llm(
    db: Session,
    call: Call,
    transcript: str
) -> dict:
    """
    Post-process transcript using LLM to extract structured data
    This runs AFTER call ends as a safety net
    """
    try:
        # Get current LLM provider
        llm_provider = get_setting(db, "llm_provider", default="groq")
        
        # Get agent configuration
        agent = call.agent_configuration
        if not agent:
            logger.warning(f"No agent configuration for call {call.id}, using basic processing")
            return transcript_processor.process_transcript(transcript, None)
        
        # Build extraction prompt
        extraction_prompt = f"""You are analyzing a completed phone call transcript to extract structured information.

Original Agent Instructions:
{agent.system_prompt}

TASK: Extract all relevant structured data from this transcript. Look for:
- Delivery status (driving, delayed, arrived, unloading)
- ETA information
- Current location
- Delay reasons
- Emergency situations
- Any other relevant logistics information

Return ONLY valid JSON with extracted data. Use null for missing fields.

Transcript:
{transcript}
"""
        
        # Use LLM to extract data
        conversation = [{"role": "user", "content": extraction_prompt}]
        
        llm_response = await llm_service.generate_response(
            conversation_history=conversation,
            system_prompt="You are a data extraction assistant. Extract structured information from transcripts and return valid JSON only.",
            functions=FUNCTIONS,
            primary_provider=llm_provider
        )
        
        # Parse function call or content
        if llm_response.get("function_call"):
            function_call = llm_response["function_call"]
            try:
                arguments = json.loads(function_call.get("arguments", "{}"))
                return arguments
            except:
                logger.error("Failed to parse function arguments in post-processing")
        
        # Try to parse content as JSON
        content = llm_response.get("content", "")
        try:
            # Look for JSON in response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        # Fallback to basic processor
        logger.warning("LLM post-processing failed, using basic transcript processor")
        return transcript_processor.process_transcript(transcript, agent.scenario_type)
        
    except Exception as e:
        logger.error(f"Error in LLM post-processing: {e}")
        # Fallback to basic processing
        return transcript_processor.process_transcript(
            transcript,
            call.agent_configuration.scenario_type if call.agent_configuration else None
        )


@router.post("/retell")
async def retell_webhook(request: Request, db: Session = Depends(get_db)):
    """
    HTTP Webhook endpoint for Retell AI call events
    Handles call lifecycle events and post-call processing
    """
    body = await request.json()
    
    event_type = body.get("event")
    call_data = body.get("call", {})
    call_id = call_data.get("call_id")
    
    if not call_id:
        return {"status": "ok", "message": "No call_id provided"}
    
    # Find call in database
    call = db.query(Call).filter(Call.retell_call_id == call_id).first()
    
    if not call:
        logger.warning(f"Received webhook for unknown call: {call_id}")
        return {"status": "ok", "message": "Call not found"}
    
    # Handle events
    if event_type == "call_started":
        call.status = CallStatus.IN_PROGRESS
        call.started_at = datetime.utcnow()
        logger.info(f"Call started: {call_id}")
    
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
        
        logger.info(f"Call ended: {call_id}, duration: {call.duration}s")
        
        # Process transcript intelligently
        if call.raw_transcript:
            # Check if WebSocket already extracted data
            has_websocket_data = (
                call.structured_results and 
                isinstance(call.structured_results, dict) and 
                len(call.structured_results) > 0 and
                "llm_fallbacks" not in call.structured_results  # Not just metadata
            )
            
            if has_websocket_data:
                # WebSocket already extracted data - just log it
                logger.info(f"Using structured data from WebSocket for call {call_id}")
                # Mark as processed by WebSocket
                if not isinstance(call.structured_results, dict):
                    call.structured_results = {}
                call.structured_results["data_source"] = "websocket_realtime"
            else:
                # WebSocket failed or didn't extract data - use LLM post-processing
                logger.info(f"WebSocket data missing, using LLM post-processing for call {call_id}")
                try:
                    structured_data = await post_process_transcript_with_llm(
                        db=db,
                        call=call,
                        transcript=call.raw_transcript
                    )
                    
                    # Merge with any existing data
                    if call.structured_results and isinstance(call.structured_results, dict):
                        call.structured_results.update(structured_data)
                    else:
                        call.structured_results = structured_data
                    
                    # Mark as processed by webhook
                    call.structured_results["data_source"] = "webhook_postprocessing"
                    
                except Exception as e:
                    logger.error(f"Error in post-processing for call {call_id}: {e}")
                    # Store error info
                    call.structured_results = {
                        "error": "post_processing_failed",
                        "message": str(e),
                        "data_source": "error"
                    }
    
    elif event_type == "call_analyzed":
        # Retell's own analysis - merge with our data
        call_analysis = call_data.get("call_analysis", {})
        if call_analysis:
            if call.structured_results and isinstance(call.structured_results, dict):
                # Merge without overwriting our extracted data
                call.structured_results["retell_analysis"] = call_analysis
            else:
                call.structured_results = {"retell_analysis": call_analysis}
        
        logger.info(f"Call analyzed: {call_id}")
    
    db.commit()
    return {"status": "ok"}


@router.websocket("/retell/llm/{call_id}")
async def retell_llm_websocket(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for Retell AI Custom LLM with real LLM integration
    Handles real-time conversation with LLM and function calling
    """
    await websocket.accept()
    logger.info(f"✅ WebSocket connected for call: {call_id}")
    
    # Get database session
    db = next(get_db())
    
    # Get call from database
    call = db.query(Call).filter(Call.retell_call_id == call_id).first()
    if not call:
        logger.error(f"Call not found: {call_id}")
        await websocket.close()
        return
    
    # Get agent configuration
    agent = call.agent_configuration
    if not agent:
        logger.error(f"Agent configuration not found for call: {call_id}")
        await websocket.close()
        return
    
    # Get current LLM provider
    llm_provider = get_setting(db, "llm_provider", default="groq")
    logger.info(f"Using LLM provider: {llm_provider}")
    
    # Conversation history
    conversation_history = []
    
    # Track if conversation should end
    should_end_call = False
    
    try:
        # Send initial message
        initial_message = agent.initial_message or "Hi, this is Dispatch calling. How can I help you today?"
        
        initial_response = {
            "response_id": 0,
            "content": initial_message,
            "content_complete": True,
            "end_call": False
        }
        
        logger.info(f"📤 Sending initial message")
        await websocket.send_json(initial_response)
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            logger.info(f"📥 RECEIVED from Retell")
            
            interaction_type = data.get("interaction_type")
            
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
                
                if last_user_message:
                    conversation_history.append({
                        "role": "user",
                        "content": last_user_message
                    })
                
                # Generate response using LLM
                try:
                    llm_response = await llm_service.generate_response(
                        conversation_history=conversation_history,
                        system_prompt=agent.system_prompt,
                        functions=FUNCTIONS,
                        primary_provider=llm_provider
                    )
                    
                    response_text = llm_response.get("content", "")
                    function_call = llm_response.get("function_call")
                    provider_used = llm_response.get("provider_used")
                    fallback_used = llm_response.get("fallback_used")
                    
                    # Log LLM usage
                    logger.info(f"LLM Response - Provider: {provider_used}, Fallback: {fallback_used}")
                    
                    # Store fallback info in call metadata
                    if fallback_used:
                        if not call.structured_results:
                            call.structured_results = {}
                        if "llm_fallbacks" not in call.structured_results:
                            call.structured_results["llm_fallbacks"] = []
                        call.structured_results["llm_fallbacks"].append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "primary": llm_provider,
                            "used": provider_used
                        })
                        db.commit()
                    
                    # Handle function call
                    if function_call:
                        function_name = function_call.get("name")
                        arguments_str = function_call.get("arguments", "{}")
                        
                        try:
                            arguments = json.loads(arguments_str)
                        except:
                            arguments = {}
                        
                        logger.info(f"🔧 Function called: {function_name} with args: {arguments}")
                        
                        # Execute function
                        if function_name == "update_delivery_status":
                            # Update call with structured data
                            if not call.structured_results:
                                call.structured_results = {}
                            call.structured_results.update(arguments)
                            call.structured_results["data_source"] = "websocket_realtime"
                            db.commit()
                            
                            response_text = "Got it, I've updated your status. Thank you!"
                        
                        elif function_name == "report_emergency":
                            # Update call with emergency data
                            if not call.structured_results:
                                call.structured_results = {}
                            call.structured_results.update({
                                "emergency": True,
                                **arguments
                            })
                            call.structured_results["data_source"] = "websocket_realtime"
                            db.commit()
                            
                            response_text = "I understand this is an emergency. I'm connecting you to a dispatcher now."
                            should_end_call = True
                        
                        elif function_name == "end_conversation":
                            response_text = "Thank you for the update. Drive safely!"
                            should_end_call = True
                    
                    # Add assistant response to history
                    conversation_history.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    
                    # Send response
                    response_data = {
                        "response_id": response_id,
                        "content": response_text,
                        "content_complete": True,
                        "end_call": should_end_call
                    }
                    
                    logger.info(f"📤 SENDING response (end_call={should_end_call})")
                    await websocket.send_json(response_data)
                    
                    if should_end_call:
                        break
                
                except Exception as e:
                    logger.error(f"Error generating LLM response: {e}")
                    # Send fallback response
                    error_response = {
                        "response_id": response_id,
                        "content": "I'm having trouble processing that. Can you repeat?",
                        "content_complete": True,
                        "end_call": False
                    }
                    await websocket.send_json(error_response)
            
            elif interaction_type == "update_only":
                logger.debug("ℹ️ Update only - no response needed")
        
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for call: {call_id}")
    except Exception as e:
        logger.error(f"💥 WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()