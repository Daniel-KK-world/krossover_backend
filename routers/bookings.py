from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

# Import your local files
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas
import security

router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["Bookings"]
)

# 1. CREATE A BOOKING (Requires Auth)
@router.post("/", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: schemas.BookingCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # The Bouncer!
):
    # First, check if the service actually exists
    service = db.query(models.Service).filter(models.Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
        
    # Create the new booking. We pull the user_id straight from the token!
    new_booking = models.Booking(
        user_id=current_user.id,
        service_id=booking.service_id,
        booking_date=booking.booking_date,
        service_date=booking.booking_date, # Assuming service date is same as booking date for now
        special_instructions=booking.special_instructions, 
        total_amount=service.base_price, # <-- Changed to match  models.py
        status=models.BookingStatusEnum.PENDING
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

# 2. GET MY BOOKINGS (Requires Auth)
@router.get("/me", response_model=List[schemas.BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # Only return bookings that belong to the logged-in user
    bookings = db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()
    return bookings

# 3. UPDATE BOOKING STATUS (Admin Only)
@router.patch("/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking_status(
    booking_id: UUID,
    status_update: schemas.BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # Security Check: Is this user an Admin?
    if current_user.role != models.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to perform this action."
        )
        
    # Find the booking
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # Update the status and save
    booking.status = status_update.status
    db.commit()
    db.refresh(booking)
    return booking