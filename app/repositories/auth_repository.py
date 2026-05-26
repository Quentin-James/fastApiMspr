from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from hmac import compare_digest

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account, LoginRequest, SignupRequest


class AuthRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        password_salt = salt or secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            password_salt.encode("utf-8"),
            120_000,
        ).hex()
        return password_salt, password_hash

    @staticmethod
    def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
        _, computed_hash = AuthRepository._hash_password(password, salt)
        return compare_digest(computed_hash, stored_hash)

    def create_account(self, payload: SignupRequest) -> Account:
        existing = self.session.scalar(select(Account).where(Account.email == payload.email))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un compte existe déjà avec cet email.",
            )

        password_salt, password_hash = self._hash_password(payload.password)
        account = Account(
            email=payload.email,
            full_name=payload.full_name,
            password_salt=password_salt,
            password_hash=password_hash,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def authenticate(self, payload: LoginRequest) -> Account:
        account = self.session.scalar(select(Account).where(Account.email == payload.email))
        if account is None or not self._verify_password(payload.password, account.password_salt, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe invalide.",
            )

        account.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.session.commit()
        self.session.refresh(account)
        return account

    @staticmethod
    def build_token(account: Account) -> str:
        return secrets.token_urlsafe(24) + f".{account.id}"
