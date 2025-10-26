from groq import Groq
from openai import OpenAI
from typing import Dict, Any, Optional, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM interactions with Groq and OpenAI"""
    
    def __init__(self):
        self.groq_client = None
        self.openai_client = None
        
        # Initialize Groq if API key available
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Initialize OpenAI if API key available
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        functions: Optional[List[Dict[str, Any]]] = None,
        primary_provider: str = "groq"
    ) -> Dict[str, Any]:
        """
        Generate response using primary LLM with automatic fallback
        
        Args:
            conversation_history: List of messages [{"role": "user", "content": "..."}]
            system_prompt: System instructions for the LLM
            functions: Optional function definitions for function calling
            primary_provider: "groq" or "openai"
        
        Returns:
            {
                "content": "response text",
                "function_call": {...} or None,
                "provider_used": "groq" or "openai",
                "fallback_used": True/False
            }
        """
        fallback_provider = "openai" if primary_provider == "groq" else "groq"
        fallback_used = False
        provider_used = primary_provider
        
        try:
            # Try primary provider
            if primary_provider == "groq":
                result = await self._groq_generate(conversation_history, system_prompt, functions)
            else:
                result = await self._openai_generate(conversation_history, system_prompt, functions)
            
            result["provider_used"] = provider_used
            result["fallback_used"] = fallback_used
            return result
            
        except Exception as e:
            # Log primary failure
            logger.warning(f"Primary LLM ({primary_provider}) failed: {str(e)}, attempting fallback to {fallback_provider}")
            fallback_used = True
            provider_used = fallback_provider
            
            try:
                # Try fallback provider
                if fallback_provider == "groq":
                    result = await self._groq_generate(conversation_history, system_prompt, functions)
                else:
                    result = await self._openai_generate(conversation_history, system_prompt, functions)
                
                result["provider_used"] = provider_used
                result["fallback_used"] = fallback_used
                logger.info(f"Fallback to {fallback_provider} successful")
                return result
                
            except Exception as e2:
                # Both failed
                logger.error(f"Both LLM providers failed. Primary ({primary_provider}): {e}, Fallback ({fallback_provider}): {e2}")
                raise Exception(f"All LLM providers failed: {str(e2)}")
    
    async def _groq_generate(
        self,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        functions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate response using Groq"""
        if not self.groq_client:
            raise Exception("Groq API key not configured")
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        # Prepare request parameters
        request_params = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 150,
        }
        
        # Add function calling if provided
        if functions:
            request_params["tools"] = [
                {"type": "function", "function": func} for func in functions
            ]
            request_params["tool_choice"] = "auto"
        
        # Make request
        response = self.groq_client.chat.completions.create(**request_params)
        
        # Parse response
        message = response.choices[0].message
        
        result = {
            "content": message.content or "",
            "function_call": None
        }
        
        # Check for function call
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            result["function_call"] = {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            }
        
        return result
    
    async def _openai_generate(
        self,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        functions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        if not self.openai_client:
            raise Exception("OpenAI API key not configured")
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        # Prepare request parameters
        request_params = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 150,
        }
        
        # Add function calling if provided
        if functions:
            request_params["tools"] = [
                {"type": "function", "function": func} for func in functions
            ]
            request_params["tool_choice"] = "auto"
        
        # Make request
        response = self.openai_client.chat.completions.create(**request_params)
        
        # Parse response
        message = response.choices[0].message
        
        result = {
            "content": message.content or "",
            "function_call": None
        }
        
        # Check for function call
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            result["function_call"] = {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            }
        
        return result


# Singleton
llm_service = LLMService()