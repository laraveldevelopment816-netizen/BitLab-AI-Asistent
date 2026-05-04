"""
Async CRUD helperi za Request + ToolCall.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Request, ToolCall


_OUTPUT_TRUNC = 4 * 1024  # 4KB max po tool call output-u


async def insert_request(
    session: AsyncSession,
    *,
    adapter: str,
    channel: str,
    model: str,
    prompt: str,
    response: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    latency_ms: int | None = None,
    iterations: int | None = None,
    status: str = "ok",
    error: str | None = None,
    compare_group_id: str | None = None,
) -> Request:
    row = Request(
        adapter=adapter,
        channel=channel,
        model=model,
        prompt=prompt,
        response=response,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        iterations=iterations,
        status=status,
        error=error,
        compare_group_id=compare_group_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def insert_tool_call(
    session: AsyncSession,
    *,
    request_id: int,
    iteration: int,
    tool_name: str,
    input_json: str,
    output_text: str,
    latency_ms: int,
) -> ToolCall:
    row = ToolCall(
        request_id=request_id,
        iteration=iteration,
        tool_name=tool_name,
        input_json=input_json,
        output_text=output_text[:_OUTPUT_TRUNC],
        latency_ms=latency_ms,
    )
    session.add(row)
    await session.commit()
    return row


async def get_request_with_tool_calls(
    session: AsyncSession, request_id: int
) -> Request | None:
    q = (
        select(Request)
        .where(Request.id == request_id)
        .options(selectinload(Request.tool_calls))
    )
    result = await session.execute(q)
    return result.scalar_one_or_none()
