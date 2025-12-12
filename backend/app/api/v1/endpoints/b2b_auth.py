"""
B2B Authentication Endpoints.

Separate authentication system for hospital administrators.
Completely independent from B2C auth.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import jwt

from app.db.session import get_db
from app.models.hospital_admin import HospitalAdmin, HospitalAdminInvite
from app.models.pricing import Hospital
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for B2B (separate from B2C)
b2b_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/b2b/auth/login", auto_error=False)

# JWT settings
B2B_SECRET_KEY = settings.SECRET_KEY + "_b2b"  # Different secret for B2B
B2B_ALGORITHM = "HS256"
B2B_TOKEN_EXPIRE_HOURS = 24


# ============================================
# Schemas
# ============================================

class B2BRegisterRequest(BaseModel):
    """Hospital admin registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    designation: str = Field(..., min_length=2)
    phone: Optional[str] = None
    
    # Hospital info (for new hospital registration)
    hospital_name: str = Field(..., min_length=2)
    hospital_city: str = Field(..., min_length=2)
    hospital_state: str = Field(..., min_length=2)
    hospital_type: str = "private"


class B2BLoginRequest(BaseModel):
    """Hospital admin login request."""
    email: EmailStr
    password: str


class B2BTokenResponse(BaseModel):
    """B2B authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: dict


class B2BAdminResponse(BaseModel):
    """Hospital admin profile response."""
    id: int
    email: str
    full_name: str
    designation: str
    hospital_id: int
    hospital_name: str
    hospital_city: str
    is_verified: bool
    is_primary: bool
    permissions: list[str]


class B2BChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# ============================================
# Helper Functions
# ============================================

def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_b2b_token(admin_id: int) -> tuple[str, datetime]:
    """Create a JWT token for B2B admin."""
    expires = datetime.now(timezone.utc) + timedelta(hours=B2B_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(admin_id),
        "type": "b2b",
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, B2B_SECRET_KEY, algorithm=B2B_ALGORITHM)
    return token, expires


def verify_b2b_token(token: str) -> Optional[int]:
    """Verify a B2B JWT token and return admin ID."""
    try:
        payload = jwt.decode(token, B2B_SECRET_KEY, algorithms=[B2B_ALGORITHM])
        if payload.get("type") != "b2b":
            return None
        admin_id = payload.get("sub")
        return int(admin_id) if admin_id else None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_b2b_admin(
    token: Optional[str] = Depends(b2b_oauth2_scheme),
    db: Session = Depends(get_db),
) -> HospitalAdmin:
    """Get the current B2B admin from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin_id = verify_b2b_token(token)
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin = db.query(HospitalAdmin).filter(
        HospitalAdmin.id == admin_id,
        HospitalAdmin.is_active == True,
    ).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account not found or inactive",
        )
    
    return admin


# ============================================
# Endpoints
# ============================================

@router.post("/register", response_model=B2BTokenResponse)
async def register_hospital_admin(
    request: B2BRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new hospital admin account.
    
    Creates both the hospital (if new) and admin account.
    The registering admin becomes the primary admin.
    """
    # Check if email already exists
    existing = db.query(HospitalAdmin).filter(
        HospitalAdmin.email == request.email.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Find or create hospital
    hospital = db.query(Hospital).filter(
        Hospital.name == request.hospital_name,
        Hospital.city == request.hospital_city,
    ).first()
    
    if not hospital:
        # Create new hospital
        hospital = Hospital(
            name=request.hospital_name,
            normalized_name=request.hospital_name.lower().strip(),
            city=request.hospital_city,
            state=request.hospital_state,
            hospital_type=request.hospital_type,
        )
        db.add(hospital)
        db.flush()
        logger.info(f"Created new hospital: {hospital.name} in {hospital.city}")
    
    # Check if hospital already has a primary admin
    existing_primary = db.query(HospitalAdmin).filter(
        HospitalAdmin.hospital_id == hospital.id,
        HospitalAdmin.is_primary == True,
    ).first()
    
    # Create admin account
    admin = HospitalAdmin(
        email=request.email.lower(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        designation=request.designation,
        phone=request.phone,
        hospital_id=hospital.id,
        is_primary=not existing_primary,  # First admin is primary
        is_verified=True,  # Auto-verify for now (add email verification later)
        verified_at=datetime.now(timezone.utc),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    logger.info(f"B2B Admin registered: {admin.email} for hospital {hospital.name}")
    
    # Generate token
    token, expires = create_b2b_token(admin.id)
    
    return B2BTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=B2B_TOKEN_EXPIRE_HOURS * 3600,
        admin={
            "id": admin.id,
            "email": admin.email,
            "full_name": admin.full_name,
            "designation": admin.designation,
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "is_primary": admin.is_primary,
        }
    )


@router.post("/login", response_model=B2BTokenResponse)
async def login_hospital_admin(
    request: B2BLoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Login for hospital administrators.
    
    Returns a JWT token for B2B dashboard access.
    """
    # Find admin by email
    admin = db.query(HospitalAdmin).filter(
        HospitalAdmin.email == request.email.lower()
    ).first()
    
    if not admin or not verify_password(request.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last login
    admin.last_login_at = datetime.now(timezone.utc)
    admin.last_login_ip = http_request.client.host if http_request.client else None
    db.commit()
    
    # Get hospital info
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    
    # Generate token
    token, expires = create_b2b_token(admin.id)
    
    logger.info(f"B2B Admin login: {admin.email}")
    
    return B2BTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=B2B_TOKEN_EXPIRE_HOURS * 3600,
        admin={
            "id": admin.id,
            "email": admin.email,
            "full_name": admin.full_name,
            "designation": admin.designation,
            "hospital_id": admin.hospital_id,
            "hospital_name": hospital.name if hospital else "Unknown",
            "hospital_city": hospital.city if hospital else "Unknown",
            "is_primary": admin.is_primary,
            "permissions": admin.get_permissions(),
        }
    )


@router.get("/me", response_model=B2BAdminResponse)
async def get_current_admin(
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """Get current B2B admin profile."""
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    
    return B2BAdminResponse(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        designation=admin.designation,
        hospital_id=admin.hospital_id,
        hospital_name=hospital.name if hospital else "Unknown",
        hospital_city=hospital.city if hospital else "Unknown",
        is_verified=admin.is_verified,
        is_primary=admin.is_primary,
        permissions=admin.get_permissions(),
    )


@router.post("/change-password")
async def change_password(
    request: B2BChangePasswordRequest,
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """Change admin password."""
    if not verify_password(request.current_password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    admin.hashed_password = hash_password(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout_admin(
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
):
    """
    Logout B2B admin.
    
    Note: JWT tokens are stateless, so this is just for client-side cleanup.
    In production, you'd add the token to a blacklist.
    """
    return {"message": "Logged out successfully"}

