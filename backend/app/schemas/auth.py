from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    email_verified: bool = False


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class SignupResponse(BaseModel):
    user: UserOut
    # True when the account must verify its email before signing in. In that case there is no token yet.
    verification_required: bool
    token: str | None = None


class MessageResponse(BaseModel):
    message: str
