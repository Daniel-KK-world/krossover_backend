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
    role: Optional[str] = 'CUSTOMER'

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
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str

class OTPRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# ─── TOKEN & LOGIN RESPONSE ──────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginResponse(Token):
    """Login response with token and user data"""
    user: UserResponse


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
    """Base booking schema with all required fields"""
    service_id: UUID
    booking_date: datetime
    service_date: datetime
    special_instructions: Optional[str] = None

class BookingCreate(BookingBase):
    """Schema for a user creating a new booking"""
    pass

class BookingStatusUpdate(BaseModel):
    """Schema for Admin updating the status (e.g., PENDING to CONFIRMED)"""
    status: BookingStatusEnum

class BookingResponse(BaseModel):
    """Schema for what gets returned to the frontend"""
    id: UUID
    user_id: UUID
    service_id: UUID
    status: BookingStatusEnum
    booking_date: datetime
    service_date: datetime
    special_instructions: Optional[str] = None
    total_amount: Decimal
    service_name: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PAYMENT SCHEMAS
# ==========================================

class PaymentInitiateResponse(BaseModel):
    """Response when initializing a payment"""
    checkout_url: str
    reference: str
    booking_id: UUID

class PaymentVerifyResponse(BaseModel):
    """Response when verifying a payment"""
    status: str
    message: str
    reference: str


# ==========================================
# REVIEW SCHEMAS
# ==========================================

class ReviewBase(BaseModel):
    """Base review schema"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    comment: Optional[str] = Field(None, max_length=1000, description="Review comment")

class ReviewCreate(ReviewBase):
    """Schema for creating a new review"""
    service_id: UUID
    booking_id: UUID

class ReviewResponse(ReviewBase):
    """Schema for returning review data to the frontend"""
    id: UUID
    user_id: UUID
    service_id: UUID
    booking_id: UUID
    user_name: str  # From User model
    service_name: str  # From Service model
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ReviewUpdate(ReviewBase):
    """Schema for updating a review"""
    pass