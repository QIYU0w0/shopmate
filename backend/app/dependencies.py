from __future__ import annotations

import sqlite3
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from .database import get_connection
from .services.auth import get_user_by_token


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


def get_current_user(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    connection: sqlite3.Connection = Depends(get_db),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供登录凭证。")
    token = authorization.split(" ", 1)[1]
    user = get_user_by_token(connection, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录。")
    return user
