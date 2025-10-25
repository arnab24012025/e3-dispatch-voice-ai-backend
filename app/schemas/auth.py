from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """Schema for user creation"""
    password: str


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data"""
    user_id: Optional[int] = None
    username: Optional[str] = None