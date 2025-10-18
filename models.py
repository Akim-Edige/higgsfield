# models.py
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from base import Base  # ваш Base = declarative_base()


class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title = Column(Text, nullable=True)

    # связи
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Chat id={self.id} user_id={self.user_id}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # выставляет время на стороне БД
    )

    # связи
    chat = relationship("Chat", back_populates="messages")
    options = relationship(
        "Option",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Option.id",
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} chat_id={self.chat_id}>"


class Option(Base):
    """
    Таблица 'options' (singular модель 'Option', как обычно в SQLAlchemy).
    """
    __tablename__ = "options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt = Column(Text, nullable=True)
    model = Column(Text, nullable=True)
    style = Column(Text, nullable=True)
    # URL храним как текст; валидацию делаем на уровне Pydantic-схемы/роутера
    result_url = Column(Text, nullable=True)

    # связи
    message = relationship("Message", back_populates="options")

    def __repr__(self) -> str:
        return f"<Option id={self.id} message_id={self.message_id}>"
