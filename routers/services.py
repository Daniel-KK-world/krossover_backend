from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

# Import local files
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/api/v1/services",
    tags=["Services"]
)

# 1. GET ALL SERVICES (For the frontend catalog)
@router.get("/", response_model=List[schemas.ServiceResponse])
def get_all_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Only return active services
    services = db.query(models.Service).filter(models.Service.is_active == True).offset(skip).limit(limit).all()
    return services

# 2. GET A SPECIFIC SERVICE
@router.get("/{service_id}", response_model=schemas.ServiceResponse)
def get_service(service_id: UUID, db: Session = Depends(get_db)):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Service not found"
        )
    return service

# 3. CREATE A SERVICE (To populate the DB)
@router.post("/", response_model=schemas.ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(get_db)):
    # Note: Later we will lock this down so ONLY Admins can hit this endpoint.
    new_service = models.Service(**service.model_dump())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service