# routers/reviews.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas
import security

router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])

# ─── CREATE REVIEW ──────────────────────────────────────
@router.post("/", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review: schemas.ReviewCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if booking exists and belongs to user
    booking = db.query(models.Booking).filter(
        models.Booking.id == review.booking_id,
        models.Booking.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if booking is COMPLETED
    if booking.status != models.BookingStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only review completed bookings"
        )
    
    # Check if already reviewed
    existing_review = db.query(models.Review).filter(
        models.Review.booking_id == review.booking_id,
        models.Review.user_id == current_user.id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this booking"
        )
    
    # Verify service exists
    service = db.query(models.Service).filter(
        models.Service.id == review.service_id,
        models.Service.is_active == True
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Create review
    new_review = models.Review(
        user_id=current_user.id,
        service_id=review.service_id,
        booking_id=review.booking_id,
        rating=review.rating,
        comment=review.comment
    )
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    return {
        "id": new_review.id,
        "user_id": new_review.user_id,
        "service_id": new_review.service_id,
        "booking_id": new_review.booking_id,
        "rating": new_review.rating,
        "comment": new_review.comment,
        "user_name": current_user.name,
        "service_name": service.name,
        "created_at": new_review.created_at,
        "updated_at": new_review.updated_at
    }


# ─── GET REVIEWS FOR SERVICE ─────────────────────────────
@router.get("/service/{service_id}", response_model=list[schemas.ReviewResponse])
def get_service_reviews(
    service_id: str,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    reviews = db.query(models.Review).filter(
        models.Review.service_id == service_id
    ).order_by(desc(models.Review.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for review in reviews:
        user = db.query(models.User).filter(models.User.id == review.user_id).first()
        service = db.query(models.Service).filter(models.Service.id == review.service_id).first()
        
        result.append({
            "id": review.id,
            "user_id": review.user_id,
            "service_id": review.service_id,
            "booking_id": review.booking_id,
            "rating": review.rating,
            "comment": review.comment,
            "user_name": user.name if user else "Unknown User",
            "service_name": service.name if service else "Unknown Service",
            "created_at": review.created_at,
            "updated_at": review.updated_at
        })
    
    return result


# ─── GET USER'S REVIEWS ──────────────────────────────────
@router.get("/me", response_model=list[schemas.ReviewResponse])
def get_my_reviews(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(models.Review).filter(
        models.Review.user_id == current_user.id
    ).order_by(desc(models.Review.created_at)).all()
    
    result = []
    for review in reviews:
        service = db.query(models.Service).filter(models.Service.id == review.service_id).first()
        
        result.append({
            "id": review.id,
            "user_id": review.user_id,
            "service_id": review.service_id,
            "booking_id": review.booking_id,
            "rating": review.rating,
            "comment": review.comment,
            "user_name": current_user.name,
            "service_name": service.name if service else "Unknown Service",
            "created_at": review.created_at,
            "updated_at": review.updated_at
        })
    
    return result


# ─── UPDATE REVIEW ──────────────────────────────────────
@router.put("/{review_id}", response_model=schemas.ReviewResponse)
def update_review(
    review_id: str,
    review_update: schemas.ReviewUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission"
        )
    
    review.rating = review_update.rating
    review.comment = review_update.comment
    review.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(review)
    
    user = db.query(models.User).filter(models.User.id == review.user_id).first()
    service = db.query(models.Service).filter(models.Service.id == review.service_id).first()
    
    return {
        "id": review.id,
        "user_id": review.user_id,
        "service_id": review.service_id,
        "booking_id": review.booking_id,
        "rating": review.rating,
        "comment": review.comment,
        "user_name": user.name if user else "Unknown User",
        "service_name": service.name if service else "Unknown Service",
        "created_at": review.created_at,
        "updated_at": review.updated_at
    }


# ─── DELETE REVIEW ──────────────────────────────────────
@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
def delete_review(
    review_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or you don't have permission"
        )
    
    db.delete(review)
    db.commit()
    
    return {"message": "Review deleted successfully"}


# ─── GET AVERAGE RATING ──────────────────────────────────
@router.get("/service/{service_id}/average")
def get_average_rating(
    service_id: str,
    db: Session = Depends(get_db)
):
    result = db.query(
        func.avg(models.Review.rating).label("average_rating"),
        func.count(models.Review.id).label("total_reviews")
    ).filter(models.Review.service_id == service_id).first()
    
    return {
        "service_id": service_id,
        "average_rating": float(result.average_rating) if result.average_rating else 0,
        "total_reviews": result.total_reviews or 0
    }