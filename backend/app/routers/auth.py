from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user, get_db
from ..schemas import AuthResponse, UserCredentials, UserOut
from ..services.auth import create_user, login_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: UserCredentials, connection: sqlite3.Connection = Depends(get_db)) -> dict:
    user = create_user(connection, payload.username, payload.password)
    auth_payload = login_user(connection, payload.username, payload.password)
    auth_payload["user"] = user
    return auth_payload


@router.post("/login", response_model=AuthResponse)
def login(payload: UserCredentials, connection: sqlite3.Connection = Depends(get_db)) -> dict:
    return login_user(connection, payload.username, payload.password)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> dict:
    return user
