from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, Boolean, DateTime, ForeignKey, Float,
    UniqueConstraint
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

    # Personal information
    name = Column(String(100), nullable=False)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), nullable=True, unique=True, index=True)
    username = Column(String(100), nullable=True, unique=True, index=True)

    # Simple school-project auth field.
    # We keep the column name password_hash because it already exists in the DB.
    password_hash = Column(String(255), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    subjects = relationship(
        "Subject",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    sessions = relationship(
        "Session",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    weak_topics = relationship(
        "WeakTopic",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    quiz_results = relationship(
        "QuizResult",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    topic_progress = relationship(
        "TopicProgress",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    documents = relationship(
        "Document",
        back_populates="student",
        cascade="all, delete-orphan"
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="subjects")

    sessions = relationship(
        "Session",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    documents = relationship(
        "Document",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    weak_topics = relationship(
        "WeakTopic",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    quiz_results = relationship(
        "QuizResult",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    topic_progress = relationship(
        "TopicProgress",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "name",
            name="uq_subject_student_name"
        ),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="sessions")
    subject = relationship("Subject", back_populates="sessions")
    document = relationship("Document", back_populates="sessions")

    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    role = Column(String(20), nullable=False)        # "user" or "agent"
    content = Column(Text, nullable=False)
    agent_label = Column(String(50), nullable=True)  # "scribe", "research", "tutor"

    timestamp = Column(DateTime, server_default=func.now())

    session = relationship("Session", back_populates="messages")


class WeakTopic(Base):
    __tablename__ = "weak_topics"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    topic = Column(String(200), nullable=False)

    # Optional metadata produced by the global quiz analysis agent.
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    mastery_status = Column(String(50), nullable=True)  # needs_practice / improving / mastered

    detected_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student = relationship("Student", back_populates="weak_topics")
    subject = relationship("Subject", back_populates="weak_topics")

    progress_records = relationship(
        "TopicProgress",
        back_populates="weak_topic",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "topic",
            name="uq_weak_topic_student_subject_topic"
        ),
    )


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    question = Column(Text, nullable=False)
    student_answer = Column(Text, nullable=False)

    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, nullable=True)

    # Optional final report generated after the whole quiz.
    analysis_report = Column(Text, nullable=True)

    timestamp = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="quiz_results")
    subject = relationship("Subject", back_populates="quiz_results")

    topic_progress_records = relationship(
        "TopicProgress",
        back_populates="quiz_result"
    )


class TopicProgress(Base):
    __tablename__ = "topic_progress"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    weak_topic_id = Column(Integer, ForeignKey("weak_topics.id"), nullable=True)
    quiz_result_id = Column(Integer, ForeignKey("quiz_results.id"), nullable=True)

    topic = Column(String(200), nullable=False)

    score = Column(Float, nullable=False)
    correct_answers = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)

    attempt_type = Column(String(50), nullable=True)
    # examples:
    # "general_quiz"
    # "weak_topic_quiz"
    # "revision_quiz"

    analysis = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="topic_progress")
    subject = relationship("Subject", back_populates="topic_progress")
    weak_topic = relationship("WeakTopic", back_populates="progress_records")
    quiz_result = relationship("QuizResult", back_populates="topic_progress_records")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="documents")
    subject = relationship("Subject", back_populates="documents")

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    sessions = relationship("Session", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    page_number = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="chunks")
