"""`/api/auth/*` and `/api/me` routers (STORY-006).

Thin FastAPI adapters over `app.domain.users.auth_service.AuthService` — no
business logic lives here, only request/response shaping and domain-error ->
HTTP-status translation (Dependency Inversion: this module depends on
`AuthService`/`IUserRepository` via `app.api.deps`, never on a concrete
repository/JWT/Redis implementation).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_auth_service, get_current_user
from app.domain.users.auth_service import AuthService
from app.domain.users.entities import Role, User
from app.domain.users.errors import (
    InvalidCredentialsError,
    TokenRejectedError,
    UserAlreadyExistsError,
)

router = APIRouter(tags=["auth"])


class SignupRequest(BaseModel):
    """Request body for `POST /api/auth/signup`."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    """Request body for `POST /api/auth/refresh` and `POST /api/auth/logout`."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response body for `POST /api/auth/login` and `POST /api/auth/refresh`."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public-safe `User` projection — never includes `hashed_password`."""

    id: UUID
    email: str
    name: str
    role: str
    org_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=Role(user.role).value,
            org_id=user.org_id,
            created_at=user.created_at,
        )


@router.post(
    "/api/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: SignupRequest, auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """Register a new user with a bcrypt-hashed password."""
    try:
        user = await auth_service.signup(email=body.email, password=body.password, name=body.name)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserResponse.from_domain(user)


@router.post("/api/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with email (as `username`) + password; issue a token pair.

    Uses the standard OAuth2 password-grant form body so Swagger UI's
    "Authorize" flow works against this endpoint out of the box.
    """
    try:
        pair = await auth_service.login(email=form_data.username, password=form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Rotate a refresh token: the old one is blacklisted, a new pair is issued."""
    try:
        pair = await auth_service.refresh(body.refresh_token)
    except TokenRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    """Blacklist a refresh token so it can no longer be used to refresh."""
    try:
        await auth_service.logout(body.refresh_token)
    except TokenRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/api/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated caller's own profile."""
    return UserResponse.from_domain(current_user)
