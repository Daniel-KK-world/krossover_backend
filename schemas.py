import re
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional

# Import Enums from your models
from models import RoleEnum, ServiceCategoryEnum, BookingStatusEnum
# ----------------------------------------
# USER AUTHENTICATION SCHEMAS
# ----------------------------------------

class UserCreate(BaseModel):
    """Schema for incoming registration data"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    # Capped at 72 characters to prevent the bcrypt crash!
    password: str = Field(..., min_length=8, max_length=72, description="Password must be at least 8 characters")

    # Kept your custom validator because it's great for security
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[\W_]', value):
            raise ValueError('Password must contain at least one special character (e.g., !@#$%)')
        return value

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

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------
# SERVICE CATALOG SCHEMAS
# ----------------------------------------

class ServiceBase(BaseModel):
    category: ServiceCategoryEnum
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0, description="Base price in GHS")
    image_url: Optional[str] = None
    is_active: bool = True

class ServiceCreate(ServiceBase):
    """Schema for Admin creating a new service"""
    pass

class ServiceResponse(ServiceBase):
    """Schema for returning service data to the frontend"""
    id: UUID

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# BOOKING SCHEMAS
# ==========================================

class BookingBase(BaseModel):
    service_id: UUID
    booking_date: datetime
    notes: Optional[str] = None

class BookingCreate(BookingBase):
    """Schema for a user creating a new booking"""
    pass

class BookingStatusUpdate(BaseModel):
    """Schema for Admin updating the status (e.g., PENDING to CONFIRMED)"""
    status: BookingStatusEnum

class BookingResponse(BookingBase):
    """Schema for what gets returned to the frontend"""
    id: UUID
    user_id: UUID
    status: BookingStatusEnum
    total_price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class Token(BaseModel):
    access_token: str
    token_type: str
    