
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from db import SessionLocal
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, UserResponse
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_database_session() -> Session:
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured yet.",
        )
    return SessionLocal()


def authenticate_user(email: str, password: str) -> User:
    db = get_database_session()
    try:
        normalized_email = email.strip().lower()
        user = db.scalar(
            select(User).where(User.email == normalized_email)
        )

        if user is None or not verify_password(
            password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Database error during login: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify your login. Please try again later.",
        ) from None
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: RegisterRequest):
    if not request.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    db = get_database_session()
    try:
        email = str(request.email).strip().lower()

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            full_name=request.full_name,
            email=email,
            password_hash=hash_password(request.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
        )

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "Database integrity error during registration: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error during registration: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the account. Please try again later.",
        ) from None
    finally:
        db.close()


@router.post("/login")
def login_user(request: LoginRequest):
    user = authenticate_user(
        str(request.email),
        request.password,
    )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": 30 * 60,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
        },
    }


@router.post("/token")
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = authenticate_user(
        form_data.username,
        form_data.password,
    )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
    )
