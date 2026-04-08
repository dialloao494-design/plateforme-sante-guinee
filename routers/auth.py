from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.user import User
from schemas.user import UserCreate, UserLogin, UserResponse, Token
from security import (
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with email, password, and role.
    
    - email: Valid email address (will be stored lowercase)
    - password: Minimum 6 characters
    - role: One of 'patient', 'doctor', 'admin' (defaults to 'patient')
    
    Raises:
    - 409: Email already registered
    - 422: Validation error (invalid email, password, or role format)
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user.email}' is already registered. Try logging in or use another email.",
        )

    # Hash password with bcrypt
    hashed_pw = hash_password(user.password)
    new_user = User(
        email=user.email.lower().strip(),
        hashed_password=hashed_pw,
        role=user.role,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        db.rollback()
        if "email" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user. Please try again.",
        )


def authenticate_user(email: str, password: str, db: Session, attempt_limit: int = 1000):
    """
    Authenticate user by email and password.
    
    Returns User object if credentials are valid, None otherwise.
    Uses constant-time password comparison to prevent timing attacks.
    """
    # Normalize email input
    email = email.lower().strip()
    
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        # Use constant-time comparison with dummy hash to prevent timing attacks
        verify_password(password, hash_password("dummy"))
        return None
        
    if not verify_password(password, db_user.hashed_password):
        return None
        
    return db_user


def create_token_response(user: User):
    """
    Create JWT token response for authenticated user.
    
    Includes:
    - access_token: JWT token for Bearer authentication
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: User's email address
    """
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
    }


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login endpoint using OAuth2 form (application/x-www-form-urlencoded).

    **Parameters:**
    - username: Email address (sent as 'username' field in OAuth2 form)
    - password: Password (sent as 'password' field in OAuth2 form)

    **Returns:**
    - access_token: JWT token for API authentication (use in Authorization: Bearer header)
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: Confirmed email address
    
    **Errors:**
    - 401: Invalid email or password
    
    **Note:** This endpoint uses standard OAuth2 form encoding. For JSON body, use /login-json
    """
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )
    
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_token_response(user)


@router.post("/login-json", response_model=Token)
def login_json(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint accepting JSON body.

    **Parameters:** (JSON body)
    - email: User's email address
    - password: User's password

    **Returns:**
    - access_token: JWT token for API authentication (use in Authorization: Bearer header)
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: Confirmed email address
    
    **Errors:**
    - 401: Invalid email or password
    
    **Note:** This endpoint accepts JSON body. For form-encoded data, use /login
    """
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )
    
    user = authenticate_user(credentials.email, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_token_response(user)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    
    **Authentication:** Requires valid Bearer token in Authorization header
    
    **Returns:**
    - id: User's unique identifier
    - email: User's email address
    - role: User's role (patient, doctor, admin)
    
    **Errors:**
    - 401: No token provided or invalid token
    """
    return current_user
