from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, Boolean, DateTime, ForeignKey, Float
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL"))


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    sessions = relationship("Session", back_populates="student")
    weak_topics = relationship("WeakTopic", back_populates="student")
    quiz_results = relationship("QuizResult", back_populates="student")
    documents = relationship("Document", back_populates="student")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)       # "user" or "agent"
    content = Column(Text, nullable=False)
    agent_label = Column(String(50), nullable=True) # "scribe", "research", "tutor"
    timestamp = Column(DateTime, server_default=func.now())

    session = relationship("Session", back_populates="messages")


class WeakTopic(Base):
    __tablename__ = "weak_topics"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic = Column(String(200), nullable=False)
    detected_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="weak_topics")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question = Column(Text, nullable=False)
    student_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="quiz_results")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))  # Gemma 3 embedding dimension
    page_number = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="chunks")