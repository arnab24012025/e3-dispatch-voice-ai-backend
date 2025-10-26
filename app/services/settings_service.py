from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.config import settings
from typing import Optional


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a system setting value"""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    return setting.setting_value if setting else default


def set_setting(db: Session, key: str, value: str) -> SystemSettings:
    """Set a system setting value"""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    
    if setting:
        setting.setting_value = value
    else:
        setting = SystemSettings(setting_key=key, setting_value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


def initialize_default_settings(db: Session):
    """Initialize default system settings if they don't exist"""
    defaults = {
        "llm_provider": settings.DEFAULT_LLM_PROVIDER
    }
    
    for key, value in defaults.items():
        existing = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
        if not existing:
            setting = SystemSettings(setting_key=key, setting_value=value)
            db.add(setting)
    
    db.commit()