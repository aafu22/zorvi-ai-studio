"""Accounts, login sessions, email verification and password reset (standard library only).

- Passwords are hashed with scrypt and a random per-user salt. The plain password is never stored.
- A successful login returns a random session token. Only its SHA-256 hash is stored, so a leaked
  database file does not reveal usable tokens.
- Verification and reset links contain a random single-use token. Only its hash is stored, and it
  expires (24 hours for verification, 60 minutes for reset by default).
- "Forgot password" and "resend verification" always give the same answer whether or not the email
  exists, so they cannot be used to find out who has an account.
- Failed logins and email requests are throttled in memory per email address (reset on restart).
"""

import base64
import hashlib
import hmac
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.db import connect
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    UserOut,
)
from app.services import email_service

logger = logging.getLogger("zorvi.auth")

SESSION_DAYS = 30
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Brute-force protection: after MAX_FAILURES wrong passwords, wait out the lock window.
MAX_FAILURES = 8
LOCK_SECONDS = 15 * 60
_failures: dict[str, list[float]] = {}

# At most MAX_EMAILS verification / reset emails per address per window.
MAX_EMAILS = 3
EMAIL_WINDOW_SECONDS = 15 * 60
_email_requests: dict[str, list[float]] = {}

GENERIC_RESET_MESSAGE = "If an account exists for that email, we have sent a link to reset the password."
GENERIC_VERIFY_MESSAGE = "If that account needs verification, we have sent a new link."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt_b64),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# A real hash to compare against when the email is unknown, so "no such user" and
# "wrong password" take about the same time and look the same to the caller.
_DUMMY_HASH = hash_password("not-a-real-password")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalise_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise AppError(422, "Please enter a valid email address.")
    return email


def _user_out(row) -> UserOut:
    return UserOut(
        id=row["id"], name=row["name"], email=row["email"], email_verified=bool(row["email_verified"])
    )


def _issue_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (
            _token_hash(token),
            user_id,
            now.isoformat(),
            (now + timedelta(days=SESSION_DAYS)).isoformat(),
        ),
    )
    return token


# --------------------------------------------------------- emailed one-time tokens


def _issue_email_token(conn, user_id: int, purpose: str, lifetime: timedelta) -> str:
    """Create a single-use token; any older unused token for the same user and purpose stops working."""
    token = secrets.token_urlsafe(32)
    now = _now()
    conn.execute("DELETE FROM email_tokens WHERE expires_at < ?", (now.isoformat(),))
    conn.execute("DELETE FROM email_tokens WHERE user_id = ? AND purpose = ?", (user_id, purpose))
    conn.execute(
        "INSERT INTO email_tokens (token_hash, user_id, purpose, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (_token_hash(token), user_id, purpose, now.isoformat(), (now + lifetime).isoformat()),
    )
    return token


def _consume_email_token(conn, token: str, purpose: str) -> int:
    """Return the user id for a valid token and use it up. Raises a clear error otherwise."""
    row = conn.execute(
        "SELECT user_id, expires_at FROM email_tokens WHERE token_hash = ? AND purpose = ?",
        (_token_hash(token), purpose),
    ).fetchone()
    if row is None:
        raise AppError(400, "This link is invalid or has already been used. Please request a new one.")
    conn.execute("DELETE FROM email_tokens WHERE token_hash = ?", (_token_hash(token),))
    if datetime.fromisoformat(row["expires_at"]) < _now():
        raise AppError(400, "This link has expired. Please request a new one.")
    return row["user_id"]


def _email_throttled(email: str) -> bool:
    cutoff = time.time() - EMAIL_WINDOW_SECONDS
    recent = [t for t in _email_requests.get(email, []) if t > cutoff]
    if len(recent) >= MAX_EMAILS:
        _email_requests[email] = recent
        return True
    recent.append(time.time())
    _email_requests[email] = recent
    return False


def _send_verification(conn, user_id: int, name: str, email: str) -> None:
    settings = get_settings()
    token = _issue_email_token(conn, user_id, "verify", timedelta(hours=settings.verification_token_hours))
    link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={quote(token)}"
    subject, body = email_service.verification_email(email, name, link, settings.verification_token_hours)
    email_service.send_email(email, subject, body)


# --------------------------------------------------------------------- accounts


def signup(req: SignupRequest) -> SignupResponse:
    settings = get_settings()
    name = req.name.strip()
    if not name:
        raise AppError(422, "Please enter your name.")
    email = _normalise_email(req.email)
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise AppError(409, "An account with this email already exists. Try signing in.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at, email_verified) VALUES (?, ?, ?, ?, 0)",
            (name, email, hash_password(req.password), _now().isoformat()),
        )
        user_id = cur.lastrowid
        _email_requests.setdefault(email, []).append(time.time())
        _send_verification(conn, user_id, name, email)
        user = UserOut(id=user_id, name=name, email=email, email_verified=False)
        if settings.require_email_verification:
            return SignupResponse(user=user, verification_required=True)
        return SignupResponse(user=user, verification_required=False, token=_issue_session(conn, user_id))


def _check_not_locked(email: str) -> None:
    cutoff = time.time() - LOCK_SECONDS
    recent = [t for t in _failures.get(email, []) if t > cutoff]
    _failures[email] = recent
    if len(recent) >= MAX_FAILURES:
        raise AppError(429, "Too many failed attempts. Please wait a few minutes and try again.")


def login(req: LoginRequest) -> AuthResponse:
    settings = get_settings()
    email = req.email.strip().lower()
    _check_not_locked(email)
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash, email_verified FROM users WHERE email = ?", (email,)
        ).fetchone()
        ok = verify_password(req.password, row["password_hash"] if row else _DUMMY_HASH)
        if not row or not ok:
            _failures.setdefault(email, []).append(time.time())
            raise AppError(401, "Incorrect email or password.")
        _failures.pop(email, None)
        # Checked only after the password is right, so this cannot be used to discover accounts.
        if settings.require_email_verification and not row["email_verified"]:
            raise AppError(
                403, "Please verify your email address before signing in. Check your inbox for the link."
            )
        token = _issue_session(conn, row["id"])
    return AuthResponse(token=token, user=_user_out(row))


def user_for_token(token: str) -> UserOut | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.email_verified, s.expires_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_token_hash(token),),
        ).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < _now():
        return None
    return _user_out(row)


def logout(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# ------------------------------------------------------------ email verification


def verify_email(token: str) -> str:
    with connect() as conn:
        user_id = _consume_email_token(conn, token, "verify")
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    return "Your email is verified. You can now sign in."


def resend_verification(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email) or _email_throttled(email):
        return GENERIC_VERIFY_MESSAGE
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, email_verified FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row and not row["email_verified"]:
            _send_verification(conn, row["id"], row["name"], row["email"])
    return GENERIC_VERIFY_MESSAGE


# --------------------------------------------------------------- password reset


def forgot_password(email: str) -> str:
    settings = get_settings()
    email = email.strip().lower()
    if not _EMAIL_RE.match(email) or _email_throttled(email):
        return GENERIC_RESET_MESSAGE
    with connect() as conn:
        row = conn.execute("SELECT id, name, email FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            token = _issue_email_token(
                conn, row["id"], "reset", timedelta(minutes=settings.reset_token_minutes)
            )
            link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={quote(token)}"
            subject, body = email_service.reset_email(
                row["email"], row["name"], link, settings.reset_token_minutes
            )
            email_service.send_email(row["email"], subject, body)
    return GENERIC_RESET_MESSAGE


def reset_password(req: ResetPasswordRequest) -> str:
    with connect() as conn:
        user_id = _consume_email_token(conn, req.token, "reset")
        row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
        # Clicking the emailed link also proves the person owns this address.
        conn.execute(
            "UPDATE users SET password_hash = ?, email_verified = 1 WHERE id = ?",
            (hash_password(req.password), user_id),
        )
        # Sign the account out everywhere: whoever had the old password (or a stolen session) loses access.
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        # Other unused reset/verify links for this account stop working too.
        conn.execute("DELETE FROM email_tokens WHERE user_id = ?", (user_id,))
    if row:
        _failures.pop(row["email"], None)
    return "Your password has been changed. Please sign in with the new password."
