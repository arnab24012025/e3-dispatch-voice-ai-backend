import re
from typing import Dict, Any, Optional
from app.schemas.call import CheckInResult, EmergencyResult


class TranscriptProcessor:
    """Service for processing call transcripts and extracting structured data"""
    
    # Emergency keywords
    EMERGENCY_KEYWORDS = [
        "emergency", "accident", "crash", "blowout", "breakdown",
        "medical", "injured", "hurt", "sick", "fire", "help"
    ]
    
    # Status keywords
    STATUS_KEYWORDS = {
        "driving": ["driving", "on the road", "en route", "heading", "moving"],
        "delayed": ["delayed", "stuck", "waiting", "traffic", "late"],
        "arrived": ["arrived", "here", "at the location", "made it", "pulled in"],
        "unloading": ["unloading", "unload", "getting unloaded", "at the dock"]
    }
    
    def process_transcript(
        self,
        transcript: str,
        scenario_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process transcript and extract structured data
        
        Args:
            transcript: Raw call transcript
            scenario_type: Type of scenario (check-in, emergency)
            
        Returns:
            Structured data dictionary
        """
        # Check if it's an emergency call
        is_emergency = self._detect_emergency(transcript)
        
        if is_emergency:
            return self._extract_emergency_data(transcript)
        else:
            return self._extract_checkin_data(transcript)
    
    def _detect_emergency(self, transcript: str) -> bool:
        """Detect if transcript contains emergency keywords"""
        transcript_lower = transcript.lower()
        return any(keyword in transcript_lower for keyword in self.EMERGENCY_KEYWORDS)
    
    def _extract_checkin_data(self, transcript: str) -> Dict[str, Any]:
        """Extract structured data for check-in scenario"""
        transcript_lower = transcript.lower()
        
        # Determine driver status
        driver_status = "Unknown"
        for status, keywords in self.STATUS_KEYWORDS.items():
            if any(keyword in transcript_lower for keyword in keywords):
                driver_status = status.capitalize()
                break
        
        # Determine call outcome
        if driver_status.lower() in ["arrived", "unloading"]:
            call_outcome = "Arrival Confirmation"
        else:
            call_outcome = "In-Transit Update"
        
        # Extract location (simple pattern matching)
        current_location = self._extract_location(transcript)
        
        # Extract ETA
        eta = self._extract_eta(transcript)
        
        # Extract delay reason
        delay_reason = self._extract_delay_reason(transcript)
        
        # Extract unloading status
        unloading_status = self._extract_unloading_status(transcript)
        
        # Check POD reminder acknowledgment
        pod_acknowledged = self._check_pod_acknowledgment(transcript)
        
        result = CheckInResult(
            call_outcome=call_outcome,
            driver_status=driver_status,
            current_location=current_location,
            eta=eta,
            delay_reason=delay_reason,
            unloading_status=unloading_status,
            pod_reminder_acknowledged=pod_acknowledged
        )
        
        return result.model_dump()
    
    def _extract_emergency_data(self, transcript: str) -> Dict[str, Any]:
        """Extract structured data for emergency scenario"""
        transcript_lower = transcript.lower()
        
        # Determine emergency type
        emergency_type = "Other"
        if any(word in transcript_lower for word in ["accident", "crash", "hit"]):
            emergency_type = "Accident"
        elif any(word in transcript_lower for word in ["breakdown", "blowout", "broke down"]):
            emergency_type = "Breakdown"
        elif any(word in transcript_lower for word in ["medical", "sick", "injured", "hurt"]):
            emergency_type = "Medical"
        
        # Extract safety status
        safety_status = self._extract_safety_status(transcript)
        
        # Extract injury status
        injury_status = self._extract_injury_status(transcript)
        
        # Extract location
        emergency_location = self._extract_location(transcript)
        
        # Check if load is secure
        load_secure = self._check_load_secure(transcript)
        
        result = EmergencyResult(
            call_outcome="Emergency Escalation",
            emergency_type=emergency_type,
            safety_status=safety_status,
            injury_status=injury_status,
            emergency_location=emergency_location,
            load_secure=load_secure,
            escalation_status="Connected to Human Dispatcher"
        )
        
        return result.model_dump()
    
    def _extract_location(self, transcript: str) -> Optional[str]:
        """Extract location from transcript"""
        # Look for common location patterns
        patterns = [
            r"(?:at|near|on)\s+([A-Z][A-Za-z0-9\s\-]+(?:Highway|Interstate|I-\d+|Route|Road|Street))",
            r"mile\s+marker\s+(\d+)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s*[A-Z]{2})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_eta(self, transcript: str) -> Optional[str]:
        """Extract ETA from transcript"""
        # Look for time patterns
        patterns = [
            r"(?:arrive|get there|be there)\s+(?:by|around|at)?\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)",
            r"(?:tomorrow|tonight|today)\s+(?:at|around)?\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)",
            r"in\s+(\d+\s+(?:hours?|minutes?))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_delay_reason(self, transcript: str) -> Optional[str]:
        """Extract delay reason from transcript"""
        transcript_lower = transcript.lower()
        
        reasons = {
            "Heavy Traffic": ["traffic", "congestion", "jam"],
            "Weather": ["weather", "rain", "snow", "storm", "fog"],
            "Mechanical": ["mechanical", "truck issue", "problem with"],
            "None": ["no delay", "on time", "on schedule"]
        }
        
        for reason, keywords in reasons.items():
            if any(keyword in transcript_lower for keyword in keywords):
                return reason
        
        return None
    
    def _extract_unloading_status(self, transcript: str) -> Optional[str]:
        """Extract unloading status from transcript"""
        transcript_lower = transcript.lower()
        
        if "door" in transcript_lower:
            door_match = re.search(r"door\s+(\d+)", transcript_lower)
            if door_match:
                return f"In Door {door_match.group(1)}"
        
        if any(word in transcript_lower for word in ["waiting", "lumper"]):
            return "Waiting for Lumper"
        
        if "detention" in transcript_lower:
            return "Detention"
        
        return "N/A"
    
    def _check_pod_acknowledgment(self, transcript: str) -> bool:
        """Check if driver acknowledged POD reminder"""
        transcript_lower = transcript.lower()
        acknowledgment_words = ["yes", "sure", "okay", "got it", "will do", "understood"]
        pod_words = ["pod", "proof of delivery", "paperwork"]
        
        has_pod_mention = any(word in transcript_lower for word in pod_words)
        has_acknowledgment = any(word in transcript_lower for word in acknowledgment_words)
        
        return has_pod_mention and has_acknowledgment
    
    def _extract_safety_status(self, transcript: str) -> Optional[str]:
        """Extract safety status from transcript"""
        transcript_lower = transcript.lower()
        
        if any(word in transcript_lower for word in ["safe", "okay", "fine", "unharmed"]):
            return "Driver confirmed everyone is safe"
        elif any(word in transcript_lower for word in ["unsafe", "danger", "not safe"]):
            return "Safety concerns reported"
        
        return None
    
    def _extract_injury_status(self, transcript: str) -> Optional[str]:
        """Extract injury status from transcript"""
        transcript_lower = transcript.lower()
        
        if any(word in transcript_lower for word in ["no injuries", "not hurt", "not injured", "everyone's fine"]):
            return "No injuries reported"
        elif any(word in transcript_lower for word in ["injured", "hurt", "bleeding", "pain"]):
            return "Injuries reported"
        
        return None
    
    def _check_load_secure(self, transcript: str) -> Optional[bool]:
        """Check if load is secure"""
        transcript_lower = transcript.lower()
        
        if any(word in transcript_lower for word in ["load is secure", "cargo safe", "freight okay"]):
            return True
        elif any(word in transcript_lower for word in ["load damaged", "cargo shift", "freight issue"]):
            return False
        
        return None


# Create singleton instance
transcript_processor = TranscriptProcessor()