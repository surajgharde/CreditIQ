from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class TelegramLink(Base):
    """
    Binds a Telegram chat to exactly one company.

    The bot answers a linked chat only about that company's analyses, so a
    borrower contact can never see another borrower's file. A chat with no link
    is served nothing.
    """
    __tablename__ = "telegram_links"

    id = Column(Integer, primary_key=True, index=True)
    # Telegram chat IDs are 64-bit and negative for groups.
    chat_id = Column(Integer, unique=True, index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    # Free-text note for the operator, e.g. the contact's name.
    label = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
