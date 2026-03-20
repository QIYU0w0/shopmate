from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_current_user, get_db
from ..schemas import ProductDetailResponse, SessionStatsResponse
from ..services.session import get_product_detail, get_stats


router = APIRouter(prefix="/products", tags=["products"])


@router.get("/stats", response_model=SessionStatsResponse)
def stats(
    session_id: str = Query(...),
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> SessionStatsResponse:
    return get_stats(connection, user["id"], session_id)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def detail(
    product_id: str,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> ProductDetailResponse:
    return get_product_detail(connection, user["id"], product_id)
