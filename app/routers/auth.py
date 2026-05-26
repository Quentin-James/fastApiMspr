from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.account import LoginRequest, LoginResponse, SignupRequest, SignupResponse, UserSummary
from app.relational_db import get_session
from app.repositories.auth_repository import AuthRepository

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_repo(session: Session = Depends(get_session)) -> AuthRepository:
    return AuthRepository(session)


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(payload: SignupRequest, repo: AuthRepository = Depends(get_auth_repo)) -> SignupResponse:
    account = repo.create_account(payload)
    return SignupResponse(user=UserSummary.model_validate(account))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, repo: AuthRepository = Depends(get_auth_repo)) -> LoginResponse:
    account = repo.authenticate(payload)
    return LoginResponse(
        token=repo.build_token(account),
        user=UserSummary.model_validate(account),
    )
