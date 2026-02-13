from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship
from .db import Base

class Entry(Base):
    __tablename__ = "entries"

    id = Column(BigInteger, primary_key=True)
    kind = Column(Text, nullable=False)
    headword = Column(Text, nullable=False)
    meaning_en = Column(Text, nullable=False)
    meaning_es = Column(Text, nullable=False)
    notes = Column(Text)
    level = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    examples = relationship("Example", back_populates="entry", cascade="all, delete")

class Example(Base):
    __tablename__ = "examples"

    id = Column(BigInteger, primary_key=True)
    entry_id = Column(BigInteger, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    text_en = Column(Text, nullable=False)
    text_es = Column(Text)
    rank = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    entry = relationship("Entry", back_populates="examples")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    is_suggested = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class TopicEntry(Base):
    __tablename__ = "topic_entries"

    topic_id = Column(BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    entry_id = Column(BigInteger, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
