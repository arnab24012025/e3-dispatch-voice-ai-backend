from typing import Dict, Any, Optional, List
from app.services.llm_service import llm_service
import logging
import json
import re

logger = logging.getLogger(__name__)


class CallAnalysisService:
    """Service for analyzing completed calls"""
    
    async def analyze_call(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        raw_transcript: str,
        structured_results: Optional[Dict[str, Any]],
        llm_provider: str = "groq"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive post-call analysis
        
        Returns:
        {
            "sentiment": "positive|negative|neutral",
            "sentiment_confidence": 0.85,
            "quality_score": 8.5,
            "summary": "Brief summary...",
            "key_topics": ["topic1", "topic2"],
            "goal_achieved": true,
            "cooperation_level": "high|medium|low"
        }
        """
        try:
            # Run all analyses
            sentiment_result = await self._analyze_sentiment(
                conversation_history, raw_transcript, llm_provider
            )
            
            quality_score = self._calculate_quality_score(
                conversation_history, structured_results, sentiment_result
            )
            
            summary = await self._generate_summary(
                conversation_history, structured_results, llm_provider
            )
            
            key_topics = await self._extract_key_topics(
                raw_transcript, llm_provider
            )
            
            goal_achieved = self._check_goal_achievement(structured_results)
            
            cooperation_level = self._assess_cooperation(
                conversation_history, sentiment_result
            )
            
            return {
                "sentiment": sentiment_result["sentiment"],
                "sentiment_confidence": sentiment_result["confidence"],
                "quality_score": quality_score,
                "summary": summary,
                "key_topics": key_topics,
                "goal_achieved": goal_achieved,
                "cooperation_level": cooperation_level,
                "analysis_timestamp": None  # Will be set by caller
            }
            
        except Exception as e:
            logger.error(f"Error in call analysis: {e}")
            return {
                "sentiment": "unknown",
                "sentiment_confidence": 0.0,
                "quality_score": 0.0,
                "summary": "Analysis failed",
                "key_topics": [],
                "goal_achieved": False,
                "cooperation_level": "unknown",
                "error": str(e)
            }
    
    async def _analyze_sentiment(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        raw_transcript: str,
        llm_provider: str
    ) -> Dict[str, Any]:
        """Analyze sentiment of the call"""
        try:
            # Build analysis prompt
            prompt = f"""Analyze the sentiment of this phone call between a dispatcher and a driver.

Conversation:
{raw_transcript if raw_transcript else self._format_conversation(conversation_history)}

Determine the overall sentiment (positive, negative, or neutral) and provide a confidence score (0.0 to 1.0).

Respond ONLY with valid JSON in this exact format:
{{"sentiment": "positive", "confidence": 0.85, "reasoning": "brief explanation"}}"""
            
            response = await llm_service.generate_response(
                conversation_history=[{"role": "user", "content": prompt}],
                system_prompt="You are a sentiment analysis expert. Return only valid JSON.",
                functions=None,
                primary_provider=llm_provider
            )
            
            content = response.get("content", "")
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return {
                    "sentiment": result.get("sentiment", "neutral"),
                    "confidence": result.get("confidence", 0.5)
                }
            
            # Fallback to keyword-based sentiment
            return self._keyword_sentiment_fallback(raw_transcript or "")
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {"sentiment": "neutral", "confidence": 0.5}
    
    def _keyword_sentiment_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback sentiment analysis using keywords"""
        text_lower = text.lower()
        
        positive_words = ["thank", "great", "good", "perfect", "sure", "yes", "okay", "fine"]
        negative_words = ["problem", "issue", "late", "delay", "stuck", "emergency", "accident"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {"sentiment": "positive", "confidence": 0.6}
        elif negative_count > positive_count:
            return {"sentiment": "negative", "confidence": 0.6}
        else:
            return {"sentiment": "neutral", "confidence": 0.5}
    
    def _calculate_quality_score(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        structured_results: Optional[Dict[str, Any]],
        sentiment_result: Dict[str, Any]
    ) -> float:
        """Calculate call quality score (0-10)"""
        score = 5.0  # Base score
        
        # Goal achievement (+3 points)
        if structured_results:
            if structured_results.get("status"):
                score += 2.0
            if structured_results.get("eta"):
                score += 1.0
        
        # Sentiment bonus (+1.5 points for positive, -1 for negative)
        sentiment = sentiment_result.get("sentiment")
        if sentiment == "positive":
            score += 1.5
        elif sentiment == "negative":
            score -= 1.0
        
        # Conversation length (optimal: 5-10 messages)
        if conversation_history:
            msg_count = len(conversation_history)
            if 5 <= msg_count <= 10:
                score += 1.0  # Good length
            elif msg_count < 3:
                score -= 0.5  # Too short
            elif msg_count > 15:
                score -= 0.5  # Too long
        
        # Emergency handling bonus
        if structured_results and structured_results.get("emergency"):
            score += 0.5  # Handled emergency
        
        # Clamp between 0 and 10
        return max(0.0, min(10.0, round(score, 1)))
    
    async def _generate_summary(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        structured_results: Optional[Dict[str, Any]],
        llm_provider: str
    ) -> str:
        """Generate 1-2 sentence call summary"""
        try:
            # Build context
            context = ""
            if structured_results:
                context = f"Extracted Data: {json.dumps(structured_results, indent=2)}\n\n"
            
            if conversation_history:
                context += f"Conversation:\n{self._format_conversation(conversation_history)}"
            
            prompt = f"""Summarize this dispatch call in 1-2 sentences. Focus on the outcome and key information.

{context}

Provide a concise summary (max 2 sentences):"""
            
            response = await llm_service.generate_response(
                conversation_history=[{"role": "user", "content": prompt}],
                system_prompt="You are a concise summarization expert. Be brief and factual.",
                functions=None,
                primary_provider=llm_provider
            )
            
            summary = response.get("content", "").strip()
            
            # Limit length
            if len(summary) > 200:
                summary = summary[:197] + "..."
            
            return summary or "Call completed successfully."
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Call completed."
    
    async def _extract_key_topics(
        self,
        raw_transcript: str,
        llm_provider: str
    ) -> List[str]:
        """Extract key topics/themes from call"""
        try:
            prompt = f"""Extract 3-5 key topics discussed in this call. Return ONLY a JSON array of topic strings.

Transcript:
{raw_transcript[:1000]}  # Limit to avoid token limits

Example response: ["delay", "traffic", "eta_update", "location"]

Your response (JSON array only):"""
            
            response = await llm_service.generate_response(
                conversation_history=[{"role": "user", "content": prompt}],
                system_prompt="Extract key topics. Return only JSON array of strings.",
                functions=None,
                primary_provider=llm_provider
            )
            
            content = response.get("content", "")
            
            # Extract JSON array
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                topics = json.loads(json_match.group(0))
                return topics[:5]  # Max 5 topics
            
            # Fallback to keyword extraction
            return self._keyword_topic_fallback(raw_transcript)
            
        except Exception as e:
            logger.error(f"Topic extraction error: {e}")
            return []
    
    def _keyword_topic_fallback(self, text: str) -> List[str]:
        """Fallback topic extraction using keywords"""
        text_lower = text.lower()
        topics = []
        
        topic_keywords = {
            "delay": ["delay", "late", "behind"],
            "traffic": ["traffic", "congestion", "jam"],
            "location": ["location", "where", "mile marker"],
            "eta": ["eta", "arrive", "time"],
            "emergency": ["emergency", "accident", "breakdown"],
            "delivery": ["deliver", "unload", "dock"],
            "weather": ["weather", "rain", "snow"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
        
        return topics[:5]
    
    def _check_goal_achievement(
        self,
        structured_results: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if call achieved its goal"""
        if not structured_results:
            return False
        
        # Goal achieved if we got status information
        has_status = bool(structured_results.get("status"))
        has_emergency_info = bool(structured_results.get("emergency_type"))
        
        return has_status or has_emergency_info
    
    def _assess_cooperation(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        sentiment_result: Dict[str, Any]
    ) -> str:
        """Assess driver cooperation level"""
        if not conversation_history:
            return "unknown"
        
        # Count user responses
        user_messages = [m for m in conversation_history if m.get("role") == "user"]
        
        if len(user_messages) < 2:
            return "low"
        
        # Check sentiment
        sentiment = sentiment_result.get("sentiment")
        
        if sentiment == "positive" and len(user_messages) >= 3:
            return "high"
        elif sentiment == "negative":
            return "low"
        else:
            return "medium"
    
    def _format_conversation(
        self,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """Format conversation history for LLM prompts"""
        if not conversation_history:
            return ""
        
        formatted = []
        for msg in conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "assistant":
                formatted.append(f"Agent: {content}")
            elif role == "user":
                formatted.append(f"Driver: {content}")
        
        return "\n".join(formatted)


# Singleton
call_analysis_service = CallAnalysisService()