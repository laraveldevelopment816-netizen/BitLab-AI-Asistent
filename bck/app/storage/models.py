"""
SQLAlchemy modeli za logging dashboard.

Adapter polje koristimo kao "<channel>:<model>" (npr. "chat:haiku") da bi se
isti backend skladišta dijelio između chat / voice / email / compare kanala
i različitih modela.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # "<channel>:<model>" — npr. "chat:haiku", "voice:sonnet", "email:sonnet",
    # "compare:haiku" (za fan-out u Compare panel-u)
    adapter: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)  # chat / voice / email / compare
    model: Mapped[str] = mapped_column(String(128))
    # low / medium / high — Anthropic thinking budget mapping ili PWR reasoning_effort.
    # Nullable za istorijske redove prije mdef kartice.
    effort: Mapped[str | None] = mapped_column(String(8), nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iterations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ok", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Compare grupiše više requesta (jedan upit, N modela) zajedničkim ID-om
    compare_group_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    # Session grupiše sve poruke jednog razgovora (chat tab/voice modal/email
    # thread). UUID generisan klijent-side u widget.js, prosljeđen kroz /api/chat.
    # Nullable za legacy podatke prije ovog feature-a.
    session_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ToolCall.iteration",
    )


class ToolCall(Base):
    """Fine-grained log po koraku agent loop-a — naš diferencijator."""
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    iteration: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(64))
    input_json: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text)  # truncated na 4KB pri snimanju
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    request: Mapped[Request] = relationship(back_populates="tool_calls")


# Indeksi za uobičajene filter pattern-e u dashboardu
Index("ix_requests_created_at_desc", Request.created_at.desc())
