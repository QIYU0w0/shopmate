from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status

from ..config import settings
from ..database import utc_now_iso


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return digest.hex()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}${_hash_password(password, salt)}"


def verify_password(password: str, encoded_password: str) -> bool:
    salt_hex, stored_hash = encoded_password.split("$", 1)
    candidate_hash = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(stored_hash, candidate_hash)


def create_user(connection: sqlite3.Connection, username: str, password: str) -> dict:
    now = utc_now_iso()
    try:
        cursor = connection.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username.strip(), hash_password(password), now),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在，请更换后重试。",
        ) from exc
    return get_user_by_id(connection, int(cursor.lastrowid))


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> dict:
    row = connection.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在。")
    return dict(row)


def login_user(connection: sqlite3.Connection, username: str, password: str) -> dict:
    row = connection.execute(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误。",
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.token_ttl_days)
    token = secrets.token_urlsafe(32)
    connection.execute("DELETE FROM auth_tokens WHERE user_id = ?", (row["id"],))
    connection.execute(
        "INSERT INTO auth_tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, row["id"], now.isoformat(), expires_at.isoformat()),
    )
    connection.commit()
    return {
        "token": token,
        "user": {"id": row["id"], "username": row["username"], "created_at": row["created_at"]},
    }


def get_user_by_token(connection: sqlite3.Connection, token: str) -> Optional[dict]:
    row = connection.execute(
        """
        SELECT u.id, u.username, u.created_at, t.expires_at
        FROM auth_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.token = ?
        """,
        (token,),
    ).fetchone()
    if not row:
        return None

    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        connection.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        connection.commit()
        return None

    return {"id": row["id"], "username": row["username"], "created_at": row["created_at"]}
