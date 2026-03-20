from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings:
    app_name = "ShopMate API"
    cors_origins = [
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    ]
    db_path = Path(os.getenv("SHOPMATE_DB_PATH", DATA_DIR / "shopmate.db"))
    llm_base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    xiaohongshu_mcp_url = os.getenv("XHS_MCP_URL", "").rstrip("/")
    xiaohongshu_mcp_token = os.getenv("XHS_MCP_TOKEN", "")
    taobaoke_mcp_url = os.getenv("TBK_MCP_URL", "").rstrip("/")
    taobaoke_mcp_token = os.getenv("TBK_MCP_TOKEN", "")
    token_ttl_days = int(os.getenv("TOKEN_TTL_DAYS", "14"))


settings = Settings()
