from fastapi import APIRouter, Depends, Header, Response

from app.core import rate_limit
from app.core.errors import AppError
from app.schemas.auth import (
    AuthResponse,
    EmailRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def get_current_user(authorization: str | None = Header(default=None)) -> UserOut:
    """Dependency for routes that need a signed-in user:

        @router.get("/x")
        def x(user: UserOut = Depends(get_current_user)): ...
    """
    token = _bearer_token(authorization)
    user = auth_service.user_for_token(token) if token else None
    if user is None:
        raise AppError(401, "Please sign in to continue.")
    return user


def get_optional_user(authorization: str | None = Header(default=None)) -> UserOut | None:
    """Like get_current_user, but returns None for signed-out visitors instead of failing.

    For routes that work for everyone and only add something extra (such as the Brand Kit logo) when signed in.
    """
    token = _bearer_token(authorization)
    return auth_service.user_for_token(token) if token else None


def get_ai_user(user: UserOut = Depends(get_current_user)) -> UserOut:
    """Signed-in user who is also within the AI usage limits. Use on every route that calls a paid AI model."""
    rate_limit.check_ai_limit(user.id)
    return user


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(request: SignupRequest) -> SignupResponse:
    return auth_service.signup(request)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    return auth_service.login(request)


@router.get("/me", response_model=UserOut)
def me(authorization: str | None = Header(default=None)) -> UserOut:
    return get_current_user(authorization)


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)) -> Response:
    token = _bearer_token(authorization)
    if token:
        auth_service.logout(token)
    return Response(status_code=204)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(request: TokenRequest) -> MessageResponse:
    return MessageResponse(message=auth_service.verify_email(request.token))


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(request: EmailRequest) -> MessageResponse:
    return MessageResponse(message=auth_service.resend_verification(request.email))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: EmailRequest) -> MessageResponse:
    return MessageResponse(message=auth_service.forgot_password(request.email))


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(request: ResetPasswordRequest) -> MessageResponse:
    return MessageResponse(message=auth_service.reset_password(request))
