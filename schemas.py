from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from models import RoleEnum # Importing the Enum from the models

# ----------------------------------------
# USER AUTHENTICATION SCHEMAS
# ----------------------------------------

class UserCreate(BaseModel):
    """Schema for incoming registration data"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

class UserLogin(BaseModel):
    """Schema for incoming login data"""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Schema for outgoing user data (NO need for PASSWORD here!)"""
    id: UUID
    name: str
    email: EmailStr
    phone_number: str
    role: RoleEnum
    created_at: datetime

    # This config tells Pydantic it's okay to read data directly from an SQLAlchemy model, 
    # not just a standard Python dictionary. This is crucial for FastAPI!
    model_config = ConfigDict(from_attributes=True)