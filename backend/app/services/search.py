from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import httpx

from ..config import settings
from .llm import QueryPlan


@dataclass
class SourceRecord:
    source_name: str
    provider: str
    source_url: str
    notes: str


@dataclass
class ProductCandidate:
    id: str
    title: str
    brand: str
    platform: str
    price: float
    image_url: str
    product_url: str
    source_count: int
    matched_keywords: list[str]
    score: float
    category: str
    highlights: list[str]
    dynamic_facets: dict[str, list[str]]
    source_records: list[SourceRecord] = field(default_factory=list)


def _normalize_title(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


def _within_budget(price: float, budget_min: Optional[float], budget_max: Optional[float]) -> bool:
    if budget_min is not None and price < budget_min * 0.75:
        return False
    if budget_max is not None and price > budget_max * 1.15:
        return False
    return True


def _build_candidate(item: dict, provider: str, plan: QueryPlan) -> ProductCandidate:
    matched_keywords = item.get("matched_keywords") or plan.keywords
    source_records = [
        SourceRecord(
            source_name=record["source_name"],
            provider=provider,
            source_url=record["source_url"],
            notes=record["notes"],
        )
        for record in item.get("source_records", [])
    ]
    return ProductCandidate(
        id=str(uuid.uuid4()),
        title=item["title"],
        brand=item["brand"],
        platform=item["platform"],
        price=float(item["price"]),
        image_url=item["image_url"],
        product_url=item["product_url"],
        source_count=max(1, len(source_records)),
        matched_keywords=matched_keywords,
        score=float(item.get("score", 80)),
        category=plan.category,
        highlights=item.get("highlights", []),
        dynamic_facets=item.get("dynamic_facets", {}),
        source_records=source_records,
    )


class MCPProvider:
    def __init__(self, name: str, base_url: str, token: str) -> None:
        self.name = name
        self.base_url = base_url
        self.token = token

    async def search(self, plan: QueryPlan) -> list[ProductCandidate]:
        if not self.base_url:
            return []

        payload = {
            "query": " ".join(plan.keywords),
            "category": plan.category,
            "keywords": plan.keywords,
            "budget_min": plan.budget_min,
            "budget_max": plan.budget_max,
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"{self.base_url}/search", headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            return []

        items = body.get("items", [])
        normalized: list[ProductCandidate] = []
        for item in items:
            required = {"title", "brand", "platform", "price", "image_url", "product_url"}
            if not required.issubset(item):
                continue
            if not _within_budget(float(item["price"]), plan.budget_min, plan.budget_max):
                continue
            normalized.append(_build_candidate(item, self.name, plan))
        return normalized


class MockProvider:
    MOCK_DATA = {
        "skincare": [
            {
                "title": "理肤泉大哥大轻盈防晒乳 SPF50+",
                "brand": "理肤泉",
                "platform": "淘宝",
                "price": 189,
                "image_url": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/skincare-1",
                "score": 92,
                "highlights": ["成膜快", "油皮友好", "通勤场景稳定"],
                "dynamic_facets": {"功效": ["防晒", "控油"], "肤质": ["油皮", "混油"], "成分": ["麦色滤"], "使用场景": ["通勤", "春夏"]},
                "source_records": [
                    {"source_name": "小红书防晒合集", "source_url": "https://shopmate.example/xhs/skincare-1", "notes": "高频提到轻薄不搓泥"},
                    {"source_name": "淘宝旗舰店", "source_url": "https://shopmate.example/tb/skincare-1", "notes": "店铺销量稳定"},
                ],
            },
            {
                "title": "珀莱雅双抗精华 轻油版",
                "brand": "珀莱雅",
                "platform": "京东",
                "price": 279,
                "image_url": "https://images.unsplash.com/photo-1612817288484-6f916006741a?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/skincare-2",
                "score": 88,
                "highlights": ["抗氧修护", "学生党可等活动价", "口碑热度高"],
                "dynamic_facets": {"功效": ["抗氧化", "提亮"], "肤质": ["混油", "中性"], "成分": ["麦角硫因"], "使用场景": ["熬夜修护"]},
                "source_records": [
                    {"source_name": "小红书精华盘点", "source_url": "https://shopmate.example/xhs/skincare-2", "notes": "提亮反馈集中"},
                    {"source_name": "京东自营", "source_url": "https://shopmate.example/jd/skincare-2", "notes": "满减后价格友好"},
                ],
            },
            {
                "title": "薇诺娜舒敏保湿特护霜",
                "brand": "薇诺娜",
                "platform": "拼多多",
                "price": 168,
                "image_url": "https://images.unsplash.com/photo-1570194065650-d99fb4bedf0f?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/skincare-3",
                "score": 84,
                "highlights": ["敏感肌常见推荐", "保湿修护稳定", "大促价格友好"],
                "dynamic_facets": {"功效": ["修护", "保湿"], "肤质": ["敏感肌", "干敏"], "成分": ["青刺果"], "使用场景": ["换季"]},
                "source_records": [
                    {"source_name": "小红书敏感肌笔记", "source_url": "https://shopmate.example/xhs/skincare-3", "notes": "换季维稳讨论多"},
                    {"source_name": "拼多多品牌店", "source_url": "https://shopmate.example/pdd/skincare-3", "notes": "价格带偏低"},
                ],
            },
        ],
        "shoes": [
            {
                "title": "Nike Pegasus 41 缓震跑鞋",
                "brand": "Nike",
                "platform": "淘宝",
                "price": 529,
                "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/shoes-1",
                "score": 91,
                "highlights": ["通勤跑两用", "缓震稳定", "大众脚感接受度高"],
                "dynamic_facets": {"鞋型": ["跑鞋"], "适用场景": ["通勤", "慢跑"], "缓震": ["中高"], "材质": ["工程网布"]},
                "source_records": [
                    {"source_name": "小红书跑鞋测评", "source_url": "https://shopmate.example/xhs/shoes-1", "notes": "入门跑者提及频繁"},
                    {"source_name": "淘宝运动店", "source_url": "https://shopmate.example/tb/shoes-1", "notes": "配色较全"},
                ],
            },
            {
                "title": "Adidas Adizero Boston 12",
                "brand": "Adidas",
                "platform": "京东",
                "price": 699,
                "image_url": "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/shoes-2",
                "score": 87,
                "highlights": ["速度训练向", "支撑和推进感平衡", "活动价波动大"],
                "dynamic_facets": {"鞋型": ["跑鞋"], "适用场景": ["速度训练"], "缓震": ["中"], "材质": ["轻量复合材料"]},
                "source_records": [
                    {"source_name": "小红书训练鞋总结", "source_url": "https://shopmate.example/xhs/shoes-2", "notes": "适合进阶跑者"},
                    {"source_name": "京东旗舰店", "source_url": "https://shopmate.example/jd/shoes-2", "notes": "活动时性价比较高"},
                ],
            },
            {
                "title": "安踏 PG7 通勤休闲板鞋",
                "brand": "安踏",
                "platform": "拼多多",
                "price": 259,
                "image_url": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/shoes-3",
                "score": 82,
                "highlights": ["预算友好", "日常通勤穿搭好搭配", "鞋底偏耐磨"],
                "dynamic_facets": {"鞋型": ["板鞋"], "适用场景": ["通勤", "休闲"], "缓震": ["中低"], "材质": ["合成革"]},
                "source_records": [
                    {"source_name": "小红书通勤鞋穿搭", "source_url": "https://shopmate.example/xhs/shoes-3", "notes": "搭配讨论较多"},
                    {"source_name": "拼多多百亿补贴", "source_url": "https://shopmate.example/pdd/shoes-3", "notes": "价格优势明显"},
                ],
            },
        ],
        "electronics": [
            {
                "title": "Redmi Pad Pro 12.1 英寸平板",
                "brand": "Redmi",
                "platform": "淘宝",
                "price": 1599,
                "image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/electronics-1",
                "score": 89,
                "highlights": ["学生党大屏", "续航稳", "影音表现均衡"],
                "dynamic_facets": {"核心参数": ["12.1英寸", "2.5K"], "续航": ["长续航"], "屏幕": ["LCD高刷"], "适用人群": ["学生党", "影音"]},
                "source_records": [
                    {"source_name": "小红书平板选购", "source_url": "https://shopmate.example/xhs/electronics-1", "notes": "高频出现在学生党推荐里"},
                    {"source_name": "淘宝官方店", "source_url": "https://shopmate.example/tb/electronics-1", "notes": "配件套餐较多"},
                ],
            },
            {
                "title": "华为 FreeBuds 6i 主动降噪耳机",
                "brand": "华为",
                "platform": "京东",
                "price": 449,
                "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/electronics-2",
                "score": 86,
                "highlights": ["通勤降噪够用", "佩戴舒适", "价格带友好"],
                "dynamic_facets": {"核心参数": ["主动降噪"], "续航": ["7小时单次"], "屏幕": ["无"], "适用人群": ["通勤", "学生党"]},
                "source_records": [
                    {"source_name": "小红书耳机测评", "source_url": "https://shopmate.example/xhs/electronics-2", "notes": "通勤场景反馈集中"},
                    {"source_name": "京东自营", "source_url": "https://shopmate.example/jd/electronics-2", "notes": "售后体验稳定"},
                ],
            },
            {
                "title": "联想 小新 Pro 14 轻薄本",
                "brand": "联想",
                "platform": "拼多多",
                "price": 5299,
                "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/electronics-3",
                "score": 90,
                "highlights": ["学习办公均衡", "屏幕素质好", "活动期性价比突出"],
                "dynamic_facets": {"核心参数": ["R7处理器", "32G"], "续航": ["办公一整天"], "屏幕": ["2.8K OLED"], "适用人群": ["学生党", "办公"]},
                "source_records": [
                    {"source_name": "小红书轻薄本对比", "source_url": "https://shopmate.example/xhs/electronics-3", "notes": "学习办公场景高频出现"},
                    {"source_name": "拼多多品牌补贴", "source_url": "https://shopmate.example/pdd/electronics-3", "notes": "价格波动需留意"},
                ],
            },
        ],
        "general": [
            {
                "title": "网易严选 极简双肩包",
                "brand": "网易严选",
                "platform": "淘宝",
                "price": 199,
                "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80",
                "product_url": "https://shopmate.example/products/general-1",
                "score": 80,
                "highlights": ["通勤友好", "收纳分层清晰", "风格百搭"],
                "dynamic_facets": {"核心卖点": ["收纳", "轻量"], "使用场景": ["通勤", "短途"], "适用人群": ["学生党", "上班族"]},
                "source_records": [
                    {"source_name": "小红书通勤好物", "source_url": "https://shopmate.example/xhs/general-1", "notes": "多次出现在通勤清单"},
                    {"source_name": "淘宝店铺", "source_url": "https://shopmate.example/tb/general-1", "notes": "评价集中在容量和颜值"},
                ],
            }
        ],
    }

    async def search(self, plan: QueryPlan) -> list[ProductCandidate]:
        items = self.MOCK_DATA.get(plan.category, self.MOCK_DATA["general"])
        results = []
        for item in items:
            if _within_budget(float(item["price"]), plan.budget_min, plan.budget_max):
                results.append(_build_candidate(item, "mock", plan))
        if results:
            return results
        return [_build_candidate(item, "mock", plan) for item in items[:3]]


def merge_products(candidates: list[ProductCandidate]) -> list[ProductCandidate]:
    grouped: dict[str, ProductCandidate] = {}
    for candidate in candidates:
        key = f"{candidate.brand.lower()}::{_normalize_title(candidate.title)}"
        if key not in grouped:
            grouped[key] = candidate
            continue
        current = grouped[key]
        current.score = max(current.score, candidate.score)
        current.source_records.extend(candidate.source_records)
        current.source_count = len(current.source_records)
        current.matched_keywords = sorted(set(current.matched_keywords + candidate.matched_keywords))
        current.highlights = list(dict.fromkeys(current.highlights + candidate.highlights))
        merged_facets = defaultdict(list, current.dynamic_facets)
        for facet_key, values in candidate.dynamic_facets.items():
            merged_facets[facet_key] = list(dict.fromkeys(merged_facets[facet_key] + values))
        current.dynamic_facets = dict(merged_facets)
    return sorted(grouped.values(), key=lambda item: (-item.score, item.price))


async def search_products(plan: QueryPlan) -> tuple[list[ProductCandidate], list[dict]]:
    providers = [
        MCPProvider("xiaohongshu-mcp", settings.xiaohongshu_mcp_url, settings.xiaohongshu_mcp_token),
        MCPProvider("taobaoke-mcp", settings.taobaoke_mcp_url, settings.taobaoke_mcp_token),
    ]
    candidates: list[ProductCandidate] = []
    used_sources: list[dict] = []

    for provider in providers:
        items = await provider.search(plan)
        used_sources.append({"name": provider.name, "mode": "real" if provider.base_url else "disabled", "count": len(items)})
        candidates.extend(items)

    if not candidates:
        mock_items = await MockProvider().search(plan)
        used_sources.append({"name": "mock-provider", "mode": "mock", "count": len(mock_items)})
        candidates.extend(mock_items)

    return merge_products(candidates), used_sources
