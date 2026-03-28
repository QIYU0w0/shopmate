from __future__ import annotations

import json
import sqlite3
import uuid
from collections import Counter, defaultdict
from typing import Optional

from fastapi import HTTPException, status

from ..database import utc_now_iso
from ..schemas import ChatMessageOut, ProductDetailResponse, ProductOut, SessionFacetResponse, SessionStatsResponse
from .search import ProductCandidate


def _row_to_message(row: sqlite3.Row) -> ChatMessageOut:
    return ChatMessageOut(id=row["id"], role=row["role"], content=row["content"], created_at=row["created_at"])


def _session_summary_from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    message_row = connection.execute(
        "SELECT content FROM chat_messages WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
        (row["id"],),
    ).fetchone()
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_message_preview": (message_row["content"][:42] if message_row else ""),
    }


def _load_product_sources(connection: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = connection.execute(
        "SELECT source_name, provider, source_url, notes FROM product_sources WHERE product_id = ?",
        (product_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _load_product_facets(connection: sqlite3.Connection, product_id: str) -> dict[str, list[str]]:
    rows = connection.execute(
        "SELECT facet_key, facet_value FROM product_facets WHERE product_id = ? ORDER BY facet_key, facet_value",
        (product_id,),
    ).fetchall()
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[row["facet_key"]].append(row["facet_value"])
    return dict(grouped)


def _product_from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> ProductOut:
    return ProductOut(
        id=row["id"],
        title=row["title"],
        brand=row["brand"],
        platform=row["platform"],
        price=row["price"],
        image_url=row["image_url"],
        product_url=row["product_url"],
        source_count=row["source_count"],
        matched_keywords=json.loads(row["matched_keywords_json"]),
        score=row["score"],
        category=row["category"],
        highlights=json.loads(row["highlights_json"]),
        dynamic_facets=_load_product_facets(connection, row["id"]),
        source_records=_load_product_sources(connection, row["id"]),
    )


def create_session(connection: sqlite3.Connection, user_id: int, title: Optional[str] = None) -> dict:
    if not title:
        reusable_session = connection.execute(
            """
            SELECT s.id
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            LEFT JOIN products p ON p.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY s.id
            HAVING COUNT(m.id) = 0 AND COUNT(p.id) = 0
            ORDER BY s.updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if reusable_session:
            return get_session_summary(connection, user_id, reusable_session["id"])

    now = utc_now_iso()
    session_id = str(uuid.uuid4())
    final_title = title.strip() if title else "新的购物会话"
    connection.execute(
        """
        INSERT INTO chat_sessions (id, user_id, title, category, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, user_id, final_title, "general", now, now),
    )
    connection.commit()
    return get_session_summary(connection, user_id, session_id)


def get_session(connection: sqlite3.Connection, user_id: int, session_id: str) -> dict:
    row = connection.execute(
        "SELECT id, title, category, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")
    return dict(row)


def get_session_summary(connection: sqlite3.Connection, user_id: int, session_id: str) -> dict:
    row = connection.execute(
        "SELECT id, title, category, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")
    return _session_summary_from_row(connection, row)


def list_sessions(connection: sqlite3.Connection, user_id: int) -> list[dict]:
    session_rows = connection.execute(
        """
        SELECT id, title, category, created_at, updated_at
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [_session_summary_from_row(connection, row) for row in session_rows]


def list_messages(connection: sqlite3.Connection, user_id: int, session_id: str) -> list[ChatMessageOut]:
    get_session(connection, user_id, session_id)
    rows = connection.execute(
        "SELECT id, role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    return [_row_to_message(row) for row in rows]


def add_message(connection: sqlite3.Connection, session_id: str, role: str, content: str) -> dict:
    message_id = str(uuid.uuid4())
    now = utc_now_iso()
    connection.execute(
        "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (message_id, session_id, role, content, now),
    )
    connection.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    connection.commit()
    return {"id": message_id, "role": role, "content": content, "created_at": now}


def delete_session(connection: sqlite3.Connection, user_id: int, session_id: str) -> None:
    get_session(connection, user_id, session_id)
    product_rows = connection.execute(
        "SELECT id FROM products WHERE session_id = ?",
        (session_id,),
    ).fetchall()

    for row in product_rows:
        connection.execute("DELETE FROM product_sources WHERE product_id = ?", (row["id"],))
        connection.execute("DELETE FROM product_facets WHERE product_id = ?", (row["id"],))

    connection.execute("DELETE FROM products WHERE session_id = ?", (session_id,))
    connection.execute("DELETE FROM search_tasks WHERE session_id = ?", (session_id,))
    connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    connection.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    connection.commit()


def rename_session(connection: sqlite3.Connection, user_id: int, session_id: str, title: str) -> dict:
    session = get_session(connection, user_id, session_id)
    final_title = title.strip()
    if not final_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会话标题不能为空。")
    touch_session(connection, session_id, title=final_title, category=session["category"])
    return get_session_summary(connection, user_id, session_id)


def touch_session(
    connection: sqlite3.Connection,
    session_id: str,
    *,
    title: Optional[str] = None,
    category: Optional[str] = None,
) -> None:
    current = connection.execute("SELECT title, category FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if not current:
        return
    connection.execute(
        "UPDATE chat_sessions SET title = ?, category = ?, updated_at = ? WHERE id = ?",
        (
            title if title is not None else current["title"],
            category if category is not None else current["category"],
            utc_now_iso(),
            session_id,
        ),
    )
    connection.commit()


def create_search_task(connection: sqlite3.Connection, session_id: str, query_text: str, keywords: list[str], category: str) -> str:
    task_id = str(uuid.uuid4())
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO search_tasks (id, session_id, query_text, keywords_json, category, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, session_id, query_text, json.dumps(keywords, ensure_ascii=False), category, "running", now, now),
    )
    connection.commit()
    return task_id


def update_search_task_status(connection: sqlite3.Connection, task_id: str, status_value: str) -> None:
    connection.execute(
        "UPDATE search_tasks SET status = ?, updated_at = ? WHERE id = ?",
        (status_value, utc_now_iso(), task_id),
    )
    connection.commit()


def replace_products(connection: sqlite3.Connection, session_id: str, task_id: str, category: str, products: list[ProductCandidate]) -> None:
    old_rows = connection.execute("SELECT id FROM products WHERE session_id = ?", (session_id,)).fetchall()
    for row in old_rows:
        connection.execute("DELETE FROM product_sources WHERE product_id = ?", (row["id"],))
        connection.execute("DELETE FROM product_facets WHERE product_id = ?", (row["id"],))
    connection.execute("DELETE FROM products WHERE session_id = ?", (session_id,))

    now = utc_now_iso()
    for product in products:
        connection.execute(
            """
            INSERT INTO products (
                id, session_id, task_id, title, brand, platform, price, image_url, product_url,
                source_count, matched_keywords_json, score, category, highlights_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.id,
                session_id,
                task_id,
                product.title,
                product.brand,
                product.platform,
                product.price,
                product.image_url,
                product.product_url,
                product.source_count,
                json.dumps(product.matched_keywords, ensure_ascii=False),
                product.score,
                category,
                json.dumps(product.highlights, ensure_ascii=False),
                now,
            ),
        )
        for source in product.source_records:
            connection.execute(
                "INSERT INTO product_sources (product_id, source_name, provider, source_url, notes) VALUES (?, ?, ?, ?, ?)",
                (product.id, source.source_name, source.provider, source.source_url, source.notes),
            )
        for facet_key, values in product.dynamic_facets.items():
            for value in values:
                connection.execute(
                    "INSERT INTO product_facets (product_id, facet_key, facet_value, facet_type) VALUES (?, ?, ?, ?)",
                    (product.id, facet_key, value, "enum"),
                )
    connection.commit()


def list_products(connection: sqlite3.Connection, user_id: int, session_id: str) -> list[ProductOut]:
    get_session(connection, user_id, session_id)
    rows = connection.execute(
        "SELECT * FROM products WHERE session_id = ? ORDER BY score DESC, price ASC",
        (session_id,),
    ).fetchall()
    return [_product_from_row(connection, row) for row in rows]


def get_facets(connection: sqlite3.Connection, user_id: int, session_id: str) -> SessionFacetResponse:
    session = get_session(connection, user_id, session_id)
    products = list_products(connection, user_id, session_id)

    brand_counter = Counter(product.brand for product in products)
    platform_counter = Counter(product.platform for product in products)
    price_ranges = Counter()
    dynamic_counter: dict[str, Counter] = defaultdict(Counter)

    for product in products:
        if product.price < 200:
            price_ranges["200元以下"] += 1
        elif product.price < 500:
            price_ranges["200-499元"] += 1
        elif product.price < 1000:
            price_ranges["500-999元"] += 1
        else:
            price_ranges["1000元以上"] += 1
        for facet_key, values in product.dynamic_facets.items():
            for value in values:
                dynamic_counter[facet_key][value] += 1

    fixed = [
        {
            "key": "brand",
            "label": "品牌",
            "type": "enum",
            "chart": "bar",
            "options": [{"value": value, "count": count} for value, count in brand_counter.most_common()],
        },
        {
            "key": "platform",
            "label": "平台",
            "type": "enum",
            "chart": "pie",
            "options": [{"value": value, "count": count} for value, count in platform_counter.most_common()],
        },
        {
            "key": "price",
            "label": "价格区间",
            "type": "range",
            "chart": "bar",
            "options": [{"value": value, "count": count} for value, count in price_ranges.items()],
        },
    ]

    dynamic = [
        {
            "key": key,
            "label": key,
            "type": "enum",
            "chart": "bar",
            "options": [{"value": value, "count": count} for value, count in counter.most_common()],
        }
        for key, counter in dynamic_counter.items()
    ]
    return SessionFacetResponse(category=session["category"], fixed=fixed, dynamic=dynamic)


def get_stats(connection: sqlite3.Connection, user_id: int, session_id: str) -> SessionStatsResponse:
    products = list_products(connection, user_id, session_id)
    if not products:
        return SessionStatsResponse(
            session_id=session_id,
            total_products=0,
            average_price=0,
            chart_groups={"brands": [], "platforms": [], "prices": [], "dynamic": []},
        )

    brand_counter = Counter(product.brand for product in products)
    platform_counter = Counter(product.platform for product in products)
    dynamic_counter = Counter()
    for product in products:
        for facet_key, values in product.dynamic_facets.items():
            for value in values:
                dynamic_counter[f"{facet_key}:{value}"] += 1

    return SessionStatsResponse(
        session_id=session_id,
        total_products=len(products),
        average_price=round(sum(product.price for product in products) / len(products), 2),
        chart_groups={
            "brands": [{"label": key, "value": value} for key, value in brand_counter.most_common()],
            "platforms": [{"label": key, "value": value} for key, value in platform_counter.most_common()],
            "prices": [{"label": product.title[:12], "value": product.price} for product in sorted(products, key=lambda item: item.price)[:8]],
            "dynamic": [{"label": key, "value": value} for key, value in dynamic_counter.most_common(6)],
        },
    )


def get_product_detail(connection: sqlite3.Connection, user_id: int, product_id: str) -> ProductDetailResponse:
    row = connection.execute(
        """
        SELECT p.*
        FROM products p
        JOIN chat_sessions s ON s.id = p.session_id
        WHERE p.id = ? AND s.user_id = ?
        """,
        (product_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在。")
    base = _product_from_row(connection, row)
    return ProductDetailResponse(session_id=row["session_id"], task_id=row["task_id"], **base.model_dump())
