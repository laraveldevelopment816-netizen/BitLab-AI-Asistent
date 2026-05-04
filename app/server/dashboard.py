"""
JSON API za logging dashboard. Pod prefiksom /api/dashboard/.
Bearer auth iz settings.dashboard_api_key.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..agent import run_agent
from ..config import settings
from ..storage.db import get_session_factory
from ..storage.models import Request, ToolCall
from ..storage.repo import (
    get_request_with_tool_calls,
    insert_request,
    insert_tool_call,
)


# Approximate Anthropic API pricing (USD per 1M tokens) — Claude 4.x
COST_PER_M: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":        {"input": 3.00, "output": 15.00},
}


def _cost(model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    rates = COST_PER_M.get(model)
    if not rates or tokens_in is None or tokens_out is None:
        return None
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000


# ── Auth ─────────────────────────────────────────────────────

def require_dashboard_auth(authorization: str | None = Header(default=None)) -> None:
    expected = settings.dashboard_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="Dashboard API ključ nije konfigurisan.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Nedostaje Bearer token.")
    token = authorization[len("Bearer ") :].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Pogrešan token.")


# ── Schemas ──────────────────────────────────────────────────

class ToolCallOut(BaseModel):
    iteration: int
    tool_name: str
    input_json: str
    output_text: str
    latency_ms: int

    model_config = {"from_attributes": True}


class RequestRow(BaseModel):
    id: int
    adapter: str
    channel: str
    model: str
    status: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    iterations: int | None
    cost_usd: float | None
    prompt_preview: str
    created_at: datetime


class RequestDetail(BaseModel):
    id: int
    adapter: str
    channel: str
    model: str
    status: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    iterations: int | None
    cost_usd: float | None
    prompt: str
    response: str | None
    error: str | None
    compare_group_id: str | None
    created_at: datetime
    tool_calls: list[ToolCallOut]


class RequestsPage(BaseModel):
    items: list[RequestRow]
    total: int
    page: int
    page_size: int


class AdapterStats(BaseModel):
    adapter: str
    channel: str
    model: str
    total_requests: int
    ok_requests: int
    error_requests: int
    total_tokens_in: int
    total_tokens_out: int
    avg_latency_ms: float | None
    estimated_cost_usd: float


class StatsResponse(BaseModel):
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    by_adapter: list[AdapterStats]


class CompareRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    channel: str = Field(default="chat", pattern="^(chat|voice|email)$")
    models: list[str] = Field(..., min_length=1, max_length=4)
    history: list[dict[str, Any]] | None = None


class CompareResultItem(BaseModel):
    model_key: str
    model: str
    request_id: int | None
    status: str
    reply: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    cost_usd: float | None
    error: str | None
    tool_calls: list[ToolCallOut] = Field(default_factory=list)

    # `model` polje je shadowed by Pydantic's BaseModel.model_config — disable warning
    model_config = {"protected_namespaces": ()}


class CompareResponse(BaseModel):
    compare_group_id: str
    results: list[CompareResultItem]


# ── Helpers ──────────────────────────────────────────────────

PAGE_SIZE = 50

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_dashboard_auth)],
)


def _to_row(r: Request) -> RequestRow:
    return RequestRow(
        id=r.id, adapter=r.adapter, channel=r.channel, model=r.model,
        status=r.status, tokens_in=r.tokens_in, tokens_out=r.tokens_out,
        latency_ms=r.latency_ms, iterations=r.iterations,
        cost_usd=_cost(r.model, r.tokens_in, r.tokens_out),
        prompt_preview=(r.prompt or "")[:200],
        created_at=r.created_at,
    )


def _to_detail(r: Request) -> RequestDetail:
    return RequestDetail(
        id=r.id, adapter=r.adapter, channel=r.channel, model=r.model,
        status=r.status, tokens_in=r.tokens_in, tokens_out=r.tokens_out,
        latency_ms=r.latency_ms, iterations=r.iterations,
        cost_usd=_cost(r.model, r.tokens_in, r.tokens_out),
        prompt=r.prompt, response=r.response, error=r.error,
        compare_group_id=r.compare_group_id, created_at=r.created_at,
        tool_calls=[
            ToolCallOut.model_validate(tc) for tc in (r.tool_calls or [])
        ],
    )


# ── Endpointi ────────────────────────────────────────────────

@router.get("/requests", response_model=RequestsPage)
async def list_requests(
    adapter: str | None = Query(None),
    channel: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    async with get_session_factory()() as session:
        q = select(Request).order_by(Request.created_at.desc())
        if adapter:
            q = q.where(Request.adapter == adapter)
        if channel:
            q = q.where(Request.channel == channel)
        if status:
            q = q.where(Request.status == status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await session.execute(count_q)).scalar_one()
        rows = (
            await session.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
        ).scalars().all()

    return RequestsPage(
        items=[_to_row(r) for r in rows],
        total=total, page=page, page_size=PAGE_SIZE,
    )


@router.get("/requests/{request_id}", response_model=RequestDetail)
async def get_request(request_id: int):
    async with get_session_factory()() as session:
        r = await get_request_with_tool_calls(session, request_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Request nije pronađen.")
    return _to_detail(r)


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    async with get_session_factory()() as session:
        rows = (await session.execute(select(Request))).scalars().all()

    by_adapter: dict[str, dict] = {}
    for r in rows:
        key = r.adapter
        s = by_adapter.setdefault(key, {
            "channel": r.channel, "model": r.model,
            "total": 0, "ok": 0, "error": 0,
            "tokens_in": 0, "tokens_out": 0, "latencies": [], "cost": 0.0,
        })
        s["total"] += 1
        if r.status == "ok":
            s["ok"] += 1
        else:
            s["error"] += 1
        s["tokens_in"] += r.tokens_in or 0
        s["tokens_out"] += r.tokens_out or 0
        if r.latency_ms is not None:
            s["latencies"].append(r.latency_ms)
        c = _cost(r.model, r.tokens_in, r.tokens_out)
        s["cost"] += c or 0.0

    adapter_stats = [
        AdapterStats(
            adapter=a, channel=s["channel"], model=s["model"],
            total_requests=s["total"], ok_requests=s["ok"], error_requests=s["error"],
            total_tokens_in=s["tokens_in"], total_tokens_out=s["tokens_out"],
            avg_latency_ms=(sum(s["latencies"]) / len(s["latencies"])) if s["latencies"] else None,
            estimated_cost_usd=round(s["cost"], 6),
        )
        for a, s in by_adapter.items()
    ]

    return StatsResponse(
        total_requests=len(rows),
        total_tokens_in=sum(x.total_tokens_in for x in adapter_stats),
        total_tokens_out=sum(x.total_tokens_out for x in adapter_stats),
        total_cost_usd=round(sum(x.estimated_cost_usd for x in adapter_stats), 6),
        by_adapter=adapter_stats,
    )


@router.get("/errors", response_model=RequestsPage)
async def list_errors(
    adapter: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    async with get_session_factory()() as session:
        q = (
            select(Request)
            .where(Request.status == "error")
            .order_by(Request.created_at.desc())
        )
        if adapter:
            q = q.where(Request.adapter == adapter)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await session.execute(count_q)).scalar_one()
        rows = (
            await session.execute(q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
        ).scalars().all()

    return RequestsPage(
        items=[_to_row(r) for r in rows],
        total=total, page=page, page_size=PAGE_SIZE,
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_models(req: CompareRequest):
    """Fan-out istog upita kroz N modela paralelno. Loguje sve sa istim
    compare_group_id. Vraća listu rezultata."""
    registry = settings.model_registry
    invalid = [m for m in req.models if m not in registry]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Nepoznati model(i): {invalid}. Dostupni: {list(registry)}",
        )

    group_id = uuid.uuid4().hex
    base_messages = list(req.history or [])
    base_messages.append({"role": "user", "content": req.message})

    async def _run_one(model_key: str) -> CompareResultItem:
        full_model = registry[model_key]
        try:
            result = await asyncio.to_thread(
                run_agent, base_messages, req.channel, full_model
            )
            trace = result.get("_trace", {})
            request_id = await _persist_trace(
                channel=req.channel, model=full_model, prompt=req.message,
                result=result, compare_group_id=group_id,
            )
            return CompareResultItem(
                model_key=model_key, model=full_model, request_id=request_id,
                status="ok", reply=result["reply"],
                tokens_in=trace.get("tokens_in"), tokens_out=trace.get("tokens_out"),
                latency_ms=trace.get("latency_ms"),
                cost_usd=_cost(full_model, trace.get("tokens_in"), trace.get("tokens_out")),
                error=None,
                tool_calls=[
                    ToolCallOut(
                        iteration=tc["iteration"], tool_name=tc["tool_name"],
                        input_json=tc["input_json"],
                        output_text=tc["output_text"][:4096],
                        latency_ms=tc["latency_ms"],
                    )
                    for tc in trace.get("tool_calls", [])
                ],
            )
        except Exception as exc:
            return CompareResultItem(
                model_key=model_key, model=full_model, request_id=None,
                status="error", reply="", tokens_in=None, tokens_out=None,
                latency_ms=None, cost_usd=None, error=str(exc),
            )

    results = await asyncio.gather(*[_run_one(m) for m in req.models])
    return CompareResponse(compare_group_id=group_id, results=list(results))


# ── Persist helper (poziva se iz main.py i compare endpoint-a) ──

async def _persist_trace(
    *,
    channel: str,
    model: str,
    prompt: str,
    result: dict[str, Any],
    compare_group_id: str | None = None,
    error: str | None = None,
) -> int | None:
    """Best-effort: greške u DB-u ne smiju srušiti chat. Vraća request_id ili None."""
    try:
        trace = result.get("_trace", {}) if result else {}
        adapter = f"{channel}:{_short_model_name(model)}"
        async with get_session_factory()() as session:
            request_row = await insert_request(
                session,
                adapter=adapter, channel=channel, model=model, prompt=prompt,
                response=result.get("reply") if result else None,
                tokens_in=trace.get("tokens_in"),
                tokens_out=trace.get("tokens_out"),
                latency_ms=trace.get("latency_ms"),
                iterations=result.get("iterations") if result else None,
                status="error" if error else "ok",
                error=error,
                compare_group_id=compare_group_id,
            )
            for tc in trace.get("tool_calls", []):
                await insert_tool_call(
                    session, request_id=request_row.id,
                    iteration=tc["iteration"], tool_name=tc["tool_name"],
                    input_json=tc["input_json"], output_text=tc["output_text"],
                    latency_ms=tc["latency_ms"],
                )
            return request_row.id
    except Exception as exc:
        print(f"[TRACE] persist failed: {exc!r}")
        return None


def _short_model_name(model: str) -> str:
    """claude-haiku-4-5-... → haiku, claude-sonnet-4-6 → sonnet."""
    m = model.lower()
    if "haiku" in m:
        return "haiku"
    if "sonnet" in m:
        return "sonnet"
    if "opus" in m:
        return "opus"
    return model[:24]
