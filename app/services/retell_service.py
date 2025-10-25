import httpx
from typing import Dict, Any, Optional
from app.config import settings


class RetellService:
    """Service for interacting with Retell AI API"""
    
    BASE_URL = ""
    
    def __init__(self):
        self.api_key = settings.RETELL_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_phone_call(
        self,
        to_number: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate a phone call via Retell AI
        
        Args:
            to_number: Phone number to call (E.164 format)
            agent_id: Retell AI agent ID
            metadata: Optional metadata to attach to the call
            
        Returns:
            Call creation response from Retell AI
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "to_number": to_number,
                "agent_id": agent_id,
                "metadata": metadata or {}
            }
            
            response = await client.post(
                f"{self.BASE_URL}/create-phone-call",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def create_agent(
        self,
        agent_name: str,
        system_prompt: str,
        initial_message: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new agent in Retell AI
        
        Args:
            agent_name: Name of the agent
            system_prompt: System prompt for the agent
            initial_message: Initial message the agent says
            voice_settings: Voice configuration settings
            
        Returns:
            Agent creation response from Retell AI
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "agent_name": agent_name,
                "llm_websocket_url": f"{settings.API_PREFIX}/webhook/retell",  # Our webhook URL
                "voice_id": voice_settings.get("voice_id") if voice_settings else None,
                "language": "en-US",
                "response_engine": {
                    "type": "retell-llm",
                    "llm_id": "gpt-4"  # or custom model
                }
            }
            
            # Add voice settings if provided
            if voice_settings:
                payload["enable_backchannel"] = voice_settings.get("enable_backchannel", True)
                payload["backchannel_frequency"] = voice_settings.get("backchannel_frequency", "medium")
                payload["enable_filler_words"] = voice_settings.get("enable_filler_words", True)
                payload["interruption_sensitivity"] = voice_settings.get("interruption_sensitivity", 5)
            
            response = await client.post(
                f"{self.BASE_URL}/create-agent",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """
        Get details of a call from Retell AI
        
        Args:
            call_id: Retell AI call ID
            
        Returns:
            Call details from Retell AI
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/get-call/{call_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def update_agent(
        self,
        agent_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing agent in Retell AI
        
        Args:
            agent_id: Retell AI agent ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated agent response from Retell AI
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/update-agent/{agent_id}",
                headers=self.headers,
                json=updates,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# Create singleton instance
retell_service = RetellService()