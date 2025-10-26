from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.call import Call, CallStatus
from app.models.user import User
from app.utils.dependencies import get_current_user
from typing import Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard analytics
    """
    # Total calls
    total_calls = db.query(Call).count()
    
    # Completed calls
    completed_calls = db.query(Call).filter(Call.status == CallStatus.COMPLETED).count()
    
    # Average call duration
    avg_duration_result = db.query(func.avg(Call.duration)).filter(
        Call.duration.isnot(None)
    ).scalar()
    avg_duration = round(avg_duration_result, 1) if avg_duration_result else 0
    
    # Sentiment distribution
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0}
    
    calls_with_analysis = db.query(Call).filter(
        Call.post_call_analysis.isnot(None)
    ).all()
    
    for call in calls_with_analysis:
        if call.post_call_analysis and isinstance(call.post_call_analysis, dict):
            sentiment = call.post_call_analysis.get("sentiment", "unknown")
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
    
    # Average quality score
    quality_scores = []
    for call in calls_with_analysis:
        if call.post_call_analysis and isinstance(call.post_call_analysis, dict):
            score = call.post_call_analysis.get("quality_score")
            if score is not None:
                quality_scores.append(score)
    
    avg_quality_score = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0
    
    # Goal achievement rate
    goals_achieved = sum(
        1 for call in calls_with_analysis
        if call.post_call_analysis and 
        isinstance(call.post_call_analysis, dict) and
        call.post_call_analysis.get("goal_achieved") is True
    )
    goal_achievement_rate = round((goals_achieved / len(calls_with_analysis) * 100), 1) if calls_with_analysis else 0
    
    # Emergency frequency
    emergency_calls = db.query(Call).filter(
        Call.structured_results.contains({"emergency": True})
    ).count()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_calls = db.query(Call).filter(
        Call.created_at >= seven_days_ago
    ).count()
    
    # Top topics
    topic_counts = {}
    for call in calls_with_analysis:
        if call.post_call_analysis and isinstance(call.post_call_analysis, dict):
            topics = call.post_call_analysis.get("key_topics", [])
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "avg_duration_seconds": avg_duration,
        "sentiment_distribution": sentiment_counts,
        "avg_quality_score": avg_quality_score,
        "goal_achievement_rate": goal_achievement_rate,
        "emergency_calls": emergency_calls,
        "recent_calls_7_days": recent_calls,
        "top_topics": [{"topic": topic, "count": count} for topic, count in top_topics]
    }


@router.get("/sentiment-trend")
async def get_sentiment_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sentiment trend over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    calls = db.query(Call).filter(
        Call.created_at >= start_date,
        Call.post_call_analysis.isnot(None)
    ).order_by(Call.created_at).all()
    
    trend_data = []
    for call in calls:
        if call.post_call_analysis and isinstance(call.post_call_analysis, dict):
            trend_data.append({
                "date": call.created_at.isoformat(),
                "sentiment": call.post_call_analysis.get("sentiment"),
                "quality_score": call.post_call_analysis.get("quality_score")
            })
    
    return {"trend_data": trend_data}