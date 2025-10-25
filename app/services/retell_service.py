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
            # Use the SDK's create_web_call method
            web_call = self.client.call.create_web_call(
                agent_id=agent_id,
                metadata=metadata or {}
            )
            
            # Return the response - SDK should return call_id and access_token
            if hasattr(web_call, '__dict__'):
                return web_call.__dict__
            elif hasattr(web_call, 'call_id'):
                return {
                    "call_id": web_call.call_id,
                    "access_token": web_call.access_token if hasattr(web_call, 'access_token') else None,
                    "sample_rate": 24000  # Default
                }
            else:
                # If it's already a dict
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


# Singleton
retell_service = RetellService()