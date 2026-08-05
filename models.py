"""
database/models.py
==================
SQLAlchemy ORM models representing the complete schema for MindCare AI.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User profile and authentication credentials."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    occupation = Column(String(100), nullable=True)
    goals = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")

    # Relationships
    mood_entries = relationship("MoodEntry", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    habit_logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    sleep_logs = relationship("SleepLog", back_populates="user", cascade="all, delete-orphan")
    meditation_logs = relationship("MeditationLog", back_populates="user", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    stress_assessments = relationship("StressAssessment", back_populates="user", cascade="all, delete-orphan")


class MoodEntry(Base):
    """Daily mood and metric ratings with emotion detection analytics."""
    __tablename__ = "mood_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, default=date.today, nullable=False, index=True)
    mood_score = Column(Integer, nullable=False)      # 1 to 10
    stress_level = Column(Integer, nullable=False)    # 1 to 10
    energy_level = Column(Integer, nullable=False)    # 1 to 10
    anxiety_level = Column(Integer, nullable=False)   # 1 to 10
    sleep_quality = Column(Integer, nullable=False)   # 1 to 10
    notes = Column(Text, nullable=True)
    detected_emotion = Column(String(50), nullable=True)

    user = relationship("User", back_populates="mood_entries")


class JournalEntry(Base):
    """Daily reflections, gratitude tracking, and personal journals."""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    entry_type = Column(String(50), default="Standard")  # Standard, Gratitude Log, Reflection
    gratitude_items = Column(Text, nullable=True)        # JSON string or comma-separated items
    tags = Column(String(255), nullable=True)            # Comma-separated tags

    user = relationship("User", back_populates="journal_entries")


class HabitLog(Base):
    """Daily habit completion tracking."""
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, default=date.today, nullable=False, index=True)
    habit_name = Column(String(100), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="habit_logs")


class SleepLog(Base):
    """Sleep duration and quality records."""
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, default=date.today, nullable=False, index=True)
    hours = Column(Float, nullable=False)
    quality = Column(Integer, nullable=False)  # 1 to 10
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="sleep_logs")


class MeditationLog(Base):
    """Guided breathing and meditation exercise history."""
    __tablename__ = "meditation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_type = Column(String(50), nullable=False)  # Box Breathing, Deep Relaxation, Mindfulness
    duration_mins = Column(Integer, nullable=False)

    user = relationship("User", back_populates="meditation_logs")


class ChatHistory(Base):
    """Conversational logs between user and MindCare AI companion."""
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # 'user' or 'ai'
    message = Column(Text, nullable=False)
    emotion = Column(String(50), nullable=True)

    user = relationship("User", back_populates="chat_histories")


class StressAssessment(Base):
    """Results from self-assessment mental health quizzes."""
    __tablename__ = "stress_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    score = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)

    user = relationship("User", back_populates="stress_assessments")