from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import secrets
import random
import resend
import os

# Import local files
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db
import models
import schemas
import security
from schemas import LoginResponse  # ← ADD THIS IMPORT

# ─── Router ──────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# ─── Password Hashing ────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── OTP & Token Generators ─────────────────────────────
def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP"""
    return ''.join(random.choices('0123456789', k=length))

def generate_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

# ─── Resend Email Sending ──────────────────────────────
resend.api_key = os.getenv("RESEND_API_KEY")

def send_otp_email(email: str, otp_code: str, purpose: str = "verification"):
    """Send OTP via Resend"""
    subject = f"Your {purpose} code"
    html = f"""
        <h2>{purpose.capitalize()} Code</h2>
        <p>Your OTP is: <strong>{otp_code}</strong></p>
        <p>It expires in 10 minutes.</p>
    """
    try:
        resend.Emails.send({
            "from": "noreply@kensvic.com",
            "to": email,
            "subject": subject,
            "html": html
        })
        print(f"✅ OTP sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_reset_email(email: str, reset_link: str):
    """Send password reset link via Resend"""
    html = f"""
        <h2>Reset Your Password</h2>
        <p>Click <a href="{reset_link}">here</a> to reset your password.</p>
        <p>This link expires in 15 minutes.</p>
    """
    try:
        resend.Emails.send({
            "from": "noreply@kensvic.com",  # ← FIXED: Use your verified domain
            "to": email,
            "subject": "Password Reset Request",
            "html": html
        })
        print(f"✅ Reset link sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send reset email: {e}")

# ═════════════════════════════════════════════════════════
# 1. REGISTER (with OTP)
# ═════════════════════════════════════════════════════════
@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check existing user
    existing_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.phone_number == user.phone_number)
    ).first()

    if existing_user:
        # If unverified, resend OTP and update password if needed
        if not existing_user.is_verified:
            otp = generate_otp()
            existing_user.otp_code = otp
            existing_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            # Update password if they changed it
            existing_user.password_hash = get_password_hash(user.password)
            db.commit()
            background_tasks.add_task(send_otp_email, existing_user.email, otp, "verification")
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Account exists but unverified. New OTP sent to your email."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone number is already registered."
            )

    # Create new user
    hashed_pwd = get_password_hash(user.password)
    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    new_user = models.User(
        name=user.name,
        email=user.email,
        phone_number=user.phone_number,
        password_hash=hashed_pwd,
        role=user.role,
        is_verified=False,
        otp_code=otp,
        otp_expires_at=otp_expiry,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send OTP in background
    background_tasks.add_task(send_otp_email, new_user.email, otp, "verification")

    return new_user

# ═════════════════════════════════════════════════════════
# 2. VERIFY OTP
# ═════════════════════════════════════════════════════════
@router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Account already verified", "verified": True}
    if user.otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired. Request a new one.")

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    return {"message": "Email verified successfully!", "verified": True}

# ═════════════════════════════════════════════════════════
# 3. RESEND OTP
# ═════════════════════════════════════════════════════════
@router.post("/resend-otp", status_code=status.HTTP_200_OK)
def resend_otp(
    payload: schemas.OTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()

    background_tasks.add_task(send_otp_email, user.email, otp, "verification")
    return {"message": "New OTP sent to your email"}

# ═════════════════════════════════════════════════════════
# 4. LOGIN (with verification & lockout)
# ═════════════════════════════════════════════════════════
@router.post("/login", response_model=LoginResponse)  # ← CHANGED to LoginResponse
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if account is locked (due to too many failed attempts)
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() // 60)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again in {remaining} minutes"
        )

    # Verify password
    if not verify_password(user_credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Too many failed attempts. Account locked for 15 minutes"
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated"
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support"
        )

    # Reset failed attempts on success
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Create token
    access_token = security.create_access_token(
        data={"user_id": str(user.id), "role": user.role}
    )
    
    # ─── RETURN TOKEN + USER DATA ──────────────────────────
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user  # SQLAlchemy model auto-converts to UserResponse
    )

# ═════════════════════════════════════════════════════════
# 5. FORGOT PASSWORD – Request Reset
# ═════════════════════════════════════════════════════════
@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    payload: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    # Always return same message for security (don't reveal if email exists)
    if user:
        token = generate_reset_token()
        user.reset_password_token = token
        user.reset_password_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()
        reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
        background_tasks.add_task(send_reset_email, user.email, reset_link)
    return {"message": "If your email is registered, you will receive a password reset link"}

# ═════════════════════════════════════════════════════════
# 6. RESET PASSWORD – Confirm
# ═════════════════════════════════════════════════════════
@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.reset_password_token == payload.token
    ).first()

    if not user or user.reset_password_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user.password_hash = get_password_hash(payload.new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    user.failed_login_attempts = 0  # reset lockout
    user.locked_until = None
    db.commit()

    return {"message": "Password reset successful. You can now log in."}

# ═════════════════════════════════════════════════════════
# 7. CHANGE PASSWORD (Authenticated)
# ═════════════════════════════════════════════════════════
@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: schemas.PasswordChange,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

# ═════════════════════════════════════════════════════════
# 8. GET CURRENT USER PROFILE
# ═════════════════════════════════════════════════════════
@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

# ═════════════════════════════════════════════════════════
# 9. DEACTIVATE ACCOUNT (Authenticated)
# ═════════════════════════════════════════════════════════
@router.delete("/me", status_code=status.HTTP_200_OK)
def deactivate_account(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully"}