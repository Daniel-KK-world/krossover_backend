from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas
import security

router = APIRouter(prefix="/api/v1/bookings", tags=["Bookings"])

# ─── CREATE BOOKING ──────────────────────────────────────
@router.post("/", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: schemas.BookingCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    # Get the service
    service = db.query(models.Service).filter(
        models.Service.id == booking.service_id,
        models.Service.is_active == True
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or unavailable"
        )
    
    # Calculate total amount
    total_amount = service.base_price
    
    # Create booking
    new_booking = models.Booking(
        user_id=current_user.id,
        service_id=booking.service_id,
        booking_date=booking.booking_date or datetime.now(timezone.utc),
        service_date=booking.service_date or datetime.now(timezone.utc),
        special_instructions=booking.special_instructions,
        total_amount=total_amount,
        status=models.BookingStatusEnum.PENDING
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)  # ← This loads the relationship if eager loading is set
    
    # ─── RETURN WITH ALL FIELDS ──────────────────────────
    return {
        "id": new_booking.id,
        "user_id": new_booking.user_id,
        "service_id": new_booking.service_id,
        "status": new_booking.status,
        "total_amount": new_booking.total_amount,
        "service_name": service.name,  # ← From the service we already have
        "booking_date": new_booking.booking_date,
        "service_date": new_booking.service_date,
        "special_instructions": new_booking.special_instructions
    }


# ─── GET USER'S BOOKINGS ──────────────────────────────────
@router.get("/me", response_model=list[schemas.BookingResponse])
def get_my_bookings(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id
    ).order_by(models.Booking.booking_date.desc()).all()
    
    result = []
    for booking in bookings:
        # Get service name
        service = db.query(models.Service).filter(
            models.Service.id == booking.service_id
        ).first()
        
        result.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "service_id": booking.service_id,
            "status": booking.status,
            "total_amount": booking.total_amount,
            "service_name": service.name if service else "Unknown Service",
            "booking_date": booking.booking_date,
            "service_date": booking.service_date,
            "special_instructions": booking.special_instructions
        })
    
    return result