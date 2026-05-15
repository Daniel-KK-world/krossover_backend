import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

# --- ENUMS ---
class RoleEnum(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"

class ServiceCategoryEnum(str, enum.Enum):
    BUS_HIRE = "BUS_HIRE"
    TOWING = "TOWING"
    DELIVERY = "DELIVERY"
    DRIVING_SCHOOL = "DRIVING_SCHOOL"
    TRAVEL_TOUR = "TRAVEL_TOUR"
    MECHANIC = "MECHANIC"

class BookingStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class PaymentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class PaymentMethodEnum(str, enum.Enum):
    MOMO = "MOMO"
    CARD = "CARD"

# --- MODELS ---
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.CUSTOMER)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="user")


class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(SQLEnum(ServiceCategoryEnum), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    base_price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String)
    is_active = Column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="service")
    reviews = relationship("Review", back_populates="service")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"))
    status = Column(SQLEnum(BookingStatusEnum), default=BookingStatusEnum.PENDING)
    booking_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    service_date = Column(DateTime, nullable=False)
    special_instructions = Column(Text)
    total_amount = Column(Numeric(10, 2), nullable=False)

    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True)
    gateway_reference = Column(String, unique=True) # From Paystack/Hubtel
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="GHS")
    status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    payment_method = Column(SQLEnum(PaymentMethodEnum))

    booking = relationship("Booking", back_populates="payment")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)

    user = relationship("User", back_populates="reviews")
    service = relationship("Service", back_populates="reviews")