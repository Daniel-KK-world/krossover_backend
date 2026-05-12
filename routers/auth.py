from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Import local files (we have to go up one directory level)
import sys
import os
import security
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas

# Create the router
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

# Setup the password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

# --- THE REGISTER ENDPOINT ---
@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    # 1. Check if a user with this email or phone already exists
    existing_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.phone_number == user.phone_number)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone number is already registered."
        )

    # 2. Hash the password securely
    hashed_pwd = get_password_hash(user.password)

    # 3. Create the SQLAlchemy model instance
    new_user = models.User(
        name=user.name,
        email=user.email,
        phone_number=user.phone_number,
        password_hash=hashed_pwd
        # Note: The role defaults to CUSTOMER automatically based on your models.py
    )

    # 4. Save to the Supabase database
    db.add(new_user)
    db.commit()
    db.refresh(new_user) # Grabs the newly generated UUID and timestamps from Postgres

    # 5. Return the user (FastAPI uses schemas.UserResponse to filter out the password_hash!)
    return new_user

# --- THE LOGIN ENDPOINT ---
@router.post("/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    
    # 1. Find the user by email
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    
    # If no user is found, throw a 403 error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials" # Security best practice: Never say "Email not found"
        )
        
    # 2. Verify the password matches the hash in the database
    if not pwd_context.verify(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
        
    # 3. Create the JWT Token with their ID and Role inside it
    access_token = security.create_access_token(
        data={"user_id": str(user.id), "role": user.role}
    )
    
    # 4. Hand the token back to the user
    return {"access_token": access_token, "token_type": "bearer"} 