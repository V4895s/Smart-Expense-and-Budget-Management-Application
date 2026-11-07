import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from db import SessionLocal
from models.password_reset_token import PasswordResetToken
from models.user import User
from schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_TOKEN_EXPIRE_MINUTES = 15

PASSWORD_RESET_CONSOLE = (
    os.getenv("PASSWORD_RESET_CONSOLE", "false").strip().lower()
    == "true"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
).rstrip("/")

PASSWORD_RESET_MESSAGE = (
    "If an account exists with that email address, "
    "password reset instructions have been generated."
)


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
        db.rollback()

        logger.error(
            "Database error during authentication: %s",
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


@router.post("/password-reset/request")
def request_password_reset(request: PasswordResetRequest):
    db = get_database_session()

    try:
        normalized_email = str(request.email).strip().lower()

        user = db.scalar(
            select(User).where(User.email == normalized_email)
        )

        # Always return the same response for existing and
        # non-existing email addresses.
        if user is None:
            return {"message": PASSWORD_RESET_MESSAGE}

        now = datetime.now(timezone.utc)

        # Invalidate previously generated unused tokens.
        previous_tokens = db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()

        for previous_token in previous_tokens:
            previous_token.used_at = now

        # Generate a cryptographically secure random token.
        raw_token = secrets.token_urlsafe(32)

        # Store only the SHA-256 hash in the database.
        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(
                minutes=RESET_TOKEN_EXPIRE_MINUTES
            ),
        )

        db.add(reset_token)
        db.commit()

        # Development/demo delivery only.
        # Never expose the raw token in the API response.
        if PASSWORD_RESET_CONSOLE:
            reset_url = (
                f"{FRONTEND_URL}/reset-password"
                f"?token={raw_token}"
            )

            logger.info(
                "Development password reset link: %s",
                reset_url,
            )

        return {"message": PASSWORD_RESET_MESSAGE}

    except SQLAlchemyError as exc:
        db.rollback()

        original_error = getattr(exc, "orig", None)
        diagnostic = getattr(original_error, "diag", None)

        database_message = getattr(
            diagnostic,
            "message_primary",
            None,
        )

        if not database_message and original_error is not None:
            database_message = str(original_error)

        sqlstate = (
            getattr(original_error, "sqlstate", None)
            or getattr(original_error, "pgcode", None)
        )

        logger.error(
            "Password reset database error: type=%s sqlstate=%s message=%s",
            type(exc).__name__,
            sqlstate,
            database_message or "No additional database details available.",
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not process your request. Please try again later.",
        ) from None

    finally:
        db.close()


@router.post("/password-reset/confirm")
def confirm_password_reset(request: PasswordResetConfirm):
    if not request.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    db = get_database_session()

    try:
        token_hash = hashlib.sha256(
            request.token.encode("utf-8")
        ).hexdigest()

        # Lock the token row where supported by the database.
        reset_token = db.scalar(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
            .with_for_update()
        )

        if reset_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link.",
            )

        now = datetime.now(timezone.utc)
        expires_at = reset_token.expires_at

        # SQLite may return naive datetimes even when timezone=True.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link.",
            )

        user = db.get(User, reset_token.user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link.",
            )

        # Update the password using the existing Argon2 helper.
        user.password_hash = hash_password(request.password)

        # Mark this token as used.
        reset_token.used_at = now

        # Invalidate any other outstanding tokens for this user.
        other_tokens = db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.id != reset_token.id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()

        for other_token in other_tokens:
            other_token.used_at = now

        db.commit()

        return {
            "message": (
                "Password has been reset successfully. "
                "You can now log in."
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as exc:
        db.rollback()

        logger.error(
            "Database error during password reset confirmation: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reset your password. Please try again later.",
        ) from None

    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
    )


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    db = get_database_session()

    try:
        # Load the authenticated user into this session.
        user = db.get(User, current_user.id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        normalized_email = str(request.email).strip().lower()

        # Prevent another user from using the same email.
        existing_user = db.scalar(
            select(User).where(
                User.email == normalized_email,
                User.id != user.id,
            )
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email address is already registered.",
            )

        user.full_name = request.full_name.strip()
        user.email = normalized_email

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
            "Database integrity error during profile update: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered.",
        ) from None

    except SQLAlchemyError as exc:
        db.rollback()

        logger.error(
            "Database error during profile update: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update your profile. Please try again later.",
        ) from None

    finally:
        db.close()