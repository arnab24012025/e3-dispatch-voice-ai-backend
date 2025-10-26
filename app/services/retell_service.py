from retell import Retell
from typing import Dict, Any, Optional
from app.config import settings


class RetellService:
    """Service for interacting with Retell AI"""
    
    def __init__(self):
        self.client = Retell(api_key=settings.RETELL_API_KEY)
    
    async def create_phone_call(
        self,
        to_number: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        from_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate an outbound phone call"""
        if not from_number and not hasattr(settings, 'RETELL_PHONE_NUMBER'):
            raise ValueError("No phone number configured")
        
        try:
            call = self.client.call.create_phone_call(
                from_number=from_number or settings.RETELL_PHONE_NUMBER,
                to_number=to_number,
                override_agent_id=agent_id,
                retell_llm_dynamic_variables=metadata or {}
            )
            return call.__dict__ if hasattr(call, '__dict__') else {"call_id": str(call)}
        except Exception as e:
            print(f"Error creating phone call: {e}")
            raise
    
    async def create_web_call(
        self,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a web call (browser-based, no phone number needed)
        Uses the create_web_call API endpoint
        """
        try:
            web_call = self.client.call.create_web_call(
                agent_id=agent_id,
                metadata=metadata or {}
            )
            
            if hasattr(web_call, '__dict__'):
                return web_call.__dict__
            elif hasattr(web_call, 'call_id'):
                return {
                    "call_id": web_call.call_id,
                    "access_token": web_call.access_token if hasattr(web_call, 'access_token') else None,
                    "sample_rate": 24000
                }
            else:
                return web_call
                
        except Exception as e:
            print(f"Error creating web call: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """Get call details"""
        try:
            call = self.client.call.retrieve(call_id)
            return call.__dict__ if hasattr(call, '__dict__') else {}
        except Exception as e:
            print(f"Error getting call details: {e}")
            raise
    
    async def create_agent(
        self,
        agent_name: str,
        system_prompt: str,
        initial_message: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an agent in Retell AI using Custom LLM
        
        This creates an agent that uses YOUR WebSocket LLM endpoint
        instead of Retell's built-in LLM
        """
        try:
            # Extract voice settings or use defaults
            voice_id = "11labs-Adrian"  # Default voice
            if voice_settings and "voice_id" in voice_settings:
                voice_id = voice_settings["voice_id"]
            
            # Build Custom LLM WebSocket URL
            # Format: wss://your-domain.com/api/v1/webhook/retell/llm/{call_id}
            llm_websocket_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhook/retell/llm/{{call_id}}"
            
            # Create agent with Custom LLM
            agent_response = self.client.agent.create(
                response_engine={
                    "type": "custom_llm",  # ← Use YOUR LLM via WebSocket
                    "llm_websocket_url": llm_websocket_url,
                    # System prompt and initial message handled in YOUR WebSocket
                },
                voice_id=voice_id,
                agent_name=agent_name,
                language="en-US",
                
                # Advanced settings from voice_settings
                enable_backchannel=voice_settings.get("enable_backchannel", True) if voice_settings else True,
                backchannel_frequency=voice_settings.get("backchannel_frequency", "medium") if voice_settings else "medium",
                backchannel_words=voice_settings.get("backchannel_words", ["mm-hmm", "yeah", "I see"]) if voice_settings else ["mm-hmm", "yeah", "I see"],
                interruption_sensitivity=voice_settings.get("interruption_sensitivity", 5) if voice_settings else 5,
                enable_natural_filler_words=voice_settings.get("enable_filler_words", True) if voice_settings else True,
                responsiveness=voice_settings.get("responsiveness", 1.0) if voice_settings else 1.0,
            )
            
            return {
                "agent_id": agent_response.agent_id,
                "status": "created",
                "llm_websocket_url": llm_websocket_url
            }
            
        except Exception as e:
            print(f"Error creating agent in Retell AI: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def update_agent(
        self,
        agent_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an agent in Retell AI
        """
        try:
            # Extract fields from updates
            update_params = {}
            
            if "name" in updates:
                update_params["agent_name"] = updates["name"]
            
            if "voice_settings" in updates and updates["voice_settings"]:
                vs = updates["voice_settings"]
                if "voice_id" in vs:
                    update_params["voice_id"] = vs["voice_id"]
                if "enable_backchannel" in vs:
                    update_params["enable_backchannel"] = vs["enable_backchannel"]
                if "interruption_sensitivity" in vs:
                    update_params["interruption_sensitivity"] = vs["interruption_sensitivity"]
            
            # Update agent using SDK
            agent_response = self.client.agent.update(
                agent_id=agent_id,
                **update_params
            )
            
            return {
                "agent_id": agent_response.agent_id,
                "status": "updated"
            }
            
        except Exception as e:
            print(f"Error updating agent in Retell AI: {e}")
            import traceback
            traceback.print_exc()
            raise


# Singleton
retell_service = RetellService()