from __future__ import annotations

import asyncio
import json
import sqlite3

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from ..database import get_connection
from ..dependencies import get_current_user, get_db
from ..schemas import (
    ChatMessageOut,
    ChatSendRequest,
    ProductOut,
    SessionCreateRequest,
    SessionFacetResponse,
    SessionRenameRequest,
    SessionSummary,
)
from ..services.llm import build_query_plan, chunk_text
from ..services.search import search_products
from ..services.session import (
    add_message,
    create_search_task,
    create_session,
    delete_session,
    get_facets,
    get_session,
    list_messages,
    list_products,
    list_sessions,
    rename_session,
    replace_products,
    touch_session,
    update_search_task_status,
)


router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/sessions", response_model=list[SessionSummary])
def sessions(connection: sqlite3.Connection = Depends(get_db), user: dict = Depends(get_current_user)) -> list[dict]:
    return list_sessions(connection, user["id"])


@router.post("/sessions", response_model=SessionSummary)
def create_chat_session(
    payload: SessionCreateRequest,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    return create_session(connection, user["id"], payload.title)


@router.patch("/sessions/{session_id}", response_model=SessionSummary)
def patch_chat_session(
    session_id: str,
    payload: SessionRenameRequest,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    return rename_session(connection, user["id"], session_id, payload.title)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chat_session(
    session_id: str,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Response:
    delete_session(connection, user["id"], session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def messages(
    session_id: str,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[ChatMessageOut]:
    return list_messages(connection, user["id"], session_id)


@router.get("/sessions/{session_id}/products", response_model=list[ProductOut])
def products(
    session_id: str,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[ProductOut]:
    return list_products(connection, user["id"], session_id)


@router.get("/sessions/{session_id}/facets", response_model=SessionFacetResponse)
def facets(
    session_id: str,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> SessionFacetResponse:
    return get_facets(connection, user["id"], session_id)


@router.post("/sessions/{session_id}/stream")
async def stream_reply(
    session_id: str,
    payload: ChatSendRequest,
    connection: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    session = get_session(connection, user["id"], session_id)
    user_message = payload.message.strip()
    title = session["title"]
    if title == "新的购物会话":
        title = user_message[:18] or title

    async def event_generator():
        stream_connection = get_connection()
        try:
            add_message(stream_connection, session_id, "user", user_message)
            touch_session(stream_connection, session_id, title=title)
            yield _sse("status", {"phase": "received", "label": "已收到问题"})

            history = [
                {"role": message.role, "content": message.content}
                for message in list_messages(stream_connection, user["id"], session_id)
            ]
            yield _sse("status", {"phase": "planning", "label": "正在抽取关键词与预算"})
            query_plan = await build_query_plan(user_message, history)
            task_id = create_search_task(stream_connection, session_id, user_message, query_plan.keywords, query_plan.category)
            touch_session(stream_connection, session_id, category=query_plan.category, title=title)
            yield _sse(
                "plan",
                {
                    "keywords": query_plan.keywords,
                    "category": query_plan.category,
                    "dimensions": query_plan.dimensions,
                    "budget_min": query_plan.budget_min,
                    "budget_max": query_plan.budget_max,
                },
            )

            for chunk in chunk_text(query_plan.reply):
                yield _sse("token", {"content": chunk})
                await asyncio.sleep(0.02)

            yield _sse("status", {"phase": "searching", "label": "正在查询多源结果"})
            products_found, sources = await search_products(query_plan)
            replace_products(stream_connection, session_id, task_id, query_plan.category, products_found)
            assistant_message = add_message(stream_connection, session_id, "assistant", query_plan.reply)
            update_search_task_status(stream_connection, task_id, "done")

            yield _sse("products", {"count": len(products_found), "sources": sources, "category": query_plan.category})
            yield _sse(
                "done",
                {
                    "message_id": assistant_message["id"],
                    "reply": query_plan.reply,
                    "count": len(products_found),
                    "session_id": session_id,
                },
            )
        finally:
            stream_connection.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
