from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import httpx

from ..config import settings


STOPWORDS = {
    "推荐",
    "一下",
    "帮我",
    "适合",
    "想要",
    "看看",
    "预算",
    "左右",
    "以内",
    "或者",
    "比较",
    "一个",
    "一些",
}


DIMENSIONS_BY_CATEGORY = {
    "skincare": ["功效", "肤质", "成分", "使用场景"],
    "shoes": ["鞋型", "适用场景", "缓震", "材质"],
    "electronics": ["核心参数", "续航", "屏幕", "适用人群"],
    "general": ["核心卖点", "使用场景", "适用人群"],
}


@dataclass
class QueryPlan:
    reply: str
    keywords: list[str]
    category: str
    budget_min: Optional[float]
    budget_max: Optional[float]
    dimensions: list[str]


def infer_category(message: str) -> str:
    lowered = message.lower()
    category_keywords = {
        "skincare": ["防晒", "护肤", "精华", "面霜", "敏感肌", "油皮", "爽肤水", "乳液"],
        "shoes": ["鞋", "跑鞋", "板鞋", "篮球鞋", "通勤", "缓震", "球鞋", "靴"],
        "electronics": ["数码", "手机", "耳机", "平板", "电脑", "相机", "键盘", "显示器"],
    }
    for category, keys in category_keywords.items():
        if any(key in message or key in lowered for key in keys):
            return category
    return "general"


def extract_budget(message: str) -> Tuple[Optional[float], Optional[float]]:
    range_match = re.search(r"(\d{2,5})\s*[-~到至]\s*(\d{2,5})", message)
    if range_match:
        low, high = sorted([float(range_match.group(1)), float(range_match.group(2))])
        return low, high

    around_match = re.search(r"(?:预算)?\s*(\d{2,5})\s*左右", message)
    if around_match:
        center = float(around_match.group(1))
        return center * 0.8, center * 1.2

    max_match = re.search(r"(\d{2,5})\s*(?:以内|以下)", message)
    if max_match:
        return None, float(max_match.group(1))

    min_match = re.search(r"(\d{2,5})\s*(?:以上)", message)
    if min_match:
        return float(min_match.group(1)), None

    return None, None


def extract_keywords(message: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", message)
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if token in STOPWORDS or token.isdigit():
            continue
        if token not in seen:
            seen.add(token)
            keywords.append(token)
        if len(keywords) >= 6:
            break
    return keywords or ["高性价比", "热度高"]


def build_mock_reply(
    message: str,
    category: str,
    keywords: list[str],
    budget_min: Optional[float],
    budget_max: Optional[float],
) -> str:
    category_hint = {
        "skincare": "护肤场景",
        "shoes": "鞋类场景",
        "electronics": "数码场景",
        "general": "综合购物场景",
    }[category]
    budget_text = "价格带不限"
    if budget_min and budget_max:
        budget_text = f"预算大致在 {int(budget_min)} 到 {int(budget_max)} 元"
    elif budget_max:
        budget_text = f"预算控制在 {int(budget_max)} 元以内"
    elif budget_min:
        budget_text = f"预算在 {int(budget_min)} 元以上"

    joined_keywords = "、".join(keywords[:4])
    return (
        f"我会把你的需求归类为{category_hint}，先从种草内容里提炼“{joined_keywords}”相关线索，"
        f"再联动商品平台结果做聚合对比。当前按 {budget_text} 进行筛选，固定维度重点看品牌、平台、价格，"
        f"同时根据本轮对话动态生成更细的二级维度，方便后续继续筛选。"
    )


def chunk_text(text: str, chunk_size: int = 18) -> Iterable[str]:
    start = 0
    while start < len(text):
        yield text[start : start + chunk_size]
        start += chunk_size


def _extract_json_object(raw_content: str) -> Optional[dict]:
    first = raw_content.find("{")
    last = raw_content.rfind("}")
    if first == -1 or last == -1:
        return None
    try:
        return json.loads(raw_content[first : last + 1])
    except json.JSONDecodeError:
        return None


async def _query_openai_compatible(message: str, history: list[dict]) -> Optional[dict]:
    if not settings.llm_base_url or not settings.llm_api_key:
        return None

    payload = {
        "model": settings.llm_model,
        "temperature": 0.4,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是购物助手的数据规划器。"
                    "请只返回 JSON，结构为 {reply, keywords, category, budget_min, budget_max, dimensions}。"
                    "category 只能是 skincare、shoes、electronics、general。"
                ),
            },
            *history[-6:],
            {"role": "user", "content": message},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(f"{settings.llm_base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _extract_json_object(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


async def build_query_plan(message: str, history: list[dict]) -> QueryPlan:
    generated = await _query_openai_compatible(message, history)
    if generated:
        category = generated.get("category") or infer_category(message)
        keywords = [str(item).strip() for item in generated.get("keywords", []) if str(item).strip()]
        budget_min = generated.get("budget_min")
        budget_max = generated.get("budget_max")
        dimensions = [str(item).strip() for item in generated.get("dimensions", []) if str(item).strip()]
        reply = str(generated.get("reply", "")).strip() or build_mock_reply(
            message,
            category,
            keywords or extract_keywords(message),
            budget_min,
            budget_max,
        )
        return QueryPlan(
            reply=reply,
            keywords=keywords or extract_keywords(message),
            category=category,
            budget_min=budget_min,
            budget_max=budget_max,
            dimensions=dimensions or DIMENSIONS_BY_CATEGORY.get(category, DIMENSIONS_BY_CATEGORY["general"]),
        )

    category = infer_category(message)
    budget_min, budget_max = extract_budget(message)
    keywords = extract_keywords(message)
    return QueryPlan(
        reply=build_mock_reply(message, category, keywords, budget_min, budget_max),
        keywords=keywords,
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
        dimensions=DIMENSIONS_BY_CATEGORY.get(category, DIMENSIONS_BY_CATEGORY["general"]),
    )
