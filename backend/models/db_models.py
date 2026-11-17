"""Database tables.

  reports 1 ──── * findings        one row per lab test in the report
  reports 1 ──── * chat_messages   the conversation about that report
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)        # UUID
    filename: Mapped[str] = mapped_column(String(255))
    ai_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="Finding.position",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_report_id", "report_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)          # order in the report

    parameter: Mapped[str] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64), default="")
    ref_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reported_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    calculated_status: Mapped[str] = mapped_column(String(32))
    status_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    report: Mapped["Report"] = relationship(back_populates="findings")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_report_id", "report_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))           # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped["Report"] = relationship(back_populates="messages")
