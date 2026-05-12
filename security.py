import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

# Import your local files
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db
import models

# ==========================================
# SECURITY CONFIGURATION
# ==========================================
SECRET_KEY = "krossover_super_secret_key_2026" # Later will move this to a secure .env file
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # Token lasts for 24 hours

#tell FastAPI to look for a "Bearer" token in the request headers
token_auth_scheme = HTTPBearer()

def create_access_token(data: dict):
    """Generates the JWT Token when a user logs in."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: HTTPAuthorizationCredentials = Depends(token_auth_scheme), db: Session = Depends(get_db)):
    """The Bouncer: Protects routes by checking if the token is valid and finding the user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token to get the user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    # Fetch the actual user from the Supabase database
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    return user