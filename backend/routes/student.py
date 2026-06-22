from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional

from db.models import (
    engine,
    Student,
    Subject,
    WeakTopic,
    QuizResult,
    Document,
    TopicProgress
)

from backend.agents.tutor import analyze_full_quiz_attempt

router = APIRouter()


# -------------------------------------------------------------------
# Request models
# -------------------------------------------------------------------
class SaveQuizResultRequest(BaseModel):
    question: str
    student_answer: str
    is_correct: bool
    score: float


class QuizAnswerItem(BaseModel):
    question: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None


class AnalyzeQuizAttemptRequest(BaseModel):
    discussion_title: Optional[str] = None
    quiz_focus: Optional[str] = "general lecture content"
    attempt_type: Optional[str] = "general_quiz"

    correct_count: int
    total_questions: int

    answers: List[QuizAnswerItem]


# -------------------------------------------------------------------
# Validation helpers
# -------------------------------------------------------------------
def validate_student_and_subject(
    db: DBSession,
    student_id: int,
    subject_id: int
):
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.student_id == student_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found for this student"
        )

    return student, subject


# -------------------------------------------------------------------
# Weak topics endpoints
# -------------------------------------------------------------------
@router.get("/{student_id}/weak-topics")
def get_weak_topics(student_id: int):
    """
    Backward-compatible endpoint:
    Get all weak topics for a student across all subjects.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        topics = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id
        ).order_by(WeakTopic.detected_at.desc()).all()

        return [
            {
                "id": t.id,
                "student_id": t.student_id,
                "subject_id": t.subject_id,
                "topic": t.topic,
                "evidence": t.evidence,
                "recommendation": t.recommendation,
                "mastery_status": t.mastery_status,
                "detected_at": str(t.detected_at),
                "updated_at": str(t.updated_at) if t.updated_at else None
            }
            for t in topics
        ]


@router.get("/{student_id}/subject/{subject_id}/weak-topics")
def get_subject_weak_topics(student_id: int, subject_id: int):
    """
    Get weak topics for one student inside one subject.
    These topics are now produced by global quiz analysis.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        topics = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id,
            WeakTopic.subject_id == subject_id
        ).order_by(WeakTopic.detected_at.desc()).all()

        return [
            {
                "id": t.id,
                "student_id": t.student_id,
                "subject_id": t.subject_id,
                "topic": t.topic,
                "evidence": t.evidence,
                "recommendation": t.recommendation,
                "mastery_status": t.mastery_status,
                "detected_at": str(t.detected_at),
                "updated_at": str(t.updated_at) if t.updated_at else None
            }
            for t in topics
        ]


# -------------------------------------------------------------------
# Quiz result endpoints
# -------------------------------------------------------------------
@router.get("/{student_id}/quiz-results")
def get_quiz_results(student_id: int):
    """
    Backward-compatible endpoint:
    Get all quiz results for a student across all subjects.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        results = session.query(QuizResult).filter(
            QuizResult.student_id == student_id
        ).order_by(QuizResult.timestamp.desc()).all()

        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "subject_id": r.subject_id,
                "question": r.question,
                "student_answer": r.student_answer,
                "is_correct": r.is_correct,
                "score": r.score,
                "analysis_report": r.analysis_report,
                "timestamp": str(r.timestamp)
            }
            for r in results
        ]


@router.get("/{student_id}/subject/{subject_id}/quiz-results")
def get_subject_quiz_results(student_id: int, subject_id: int):
    """
    Get quiz results for one student inside one subject.

    In the new version, each completed quiz should normally create one
    final quiz result, with an optional analysis report.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        results = session.query(QuizResult).filter(
            QuizResult.student_id == student_id,
            QuizResult.subject_id == subject_id
        ).order_by(QuizResult.timestamp.desc()).all()

        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "subject_id": r.subject_id,
                "question": r.question,
                "student_answer": r.student_answer,
                "is_correct": r.is_correct,
                "score": r.score,
                "analysis_report": r.analysis_report,
                "timestamp": str(r.timestamp)
            }
            for r in results
        ]


@router.post("/{student_id}/subject/{subject_id}/quiz-results")
def save_subject_quiz_result(
    student_id: int,
    subject_id: int,
    request: SaveQuizResultRequest
):
    """
    Backward-compatible endpoint:
    Save one final quiz result for a subject.

    The preferred new endpoint is:
    POST /student/{student_id}/subject/{subject_id}/quiz-attempt/analyze

    But we keep this endpoint so older frontend code does not break.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        score = request.score

        if score < 0:
            score = 0.0

        if score > 1:
            score = 1.0

        result = QuizResult(
            student_id=student_id,
            subject_id=subject_id,
            question=request.question,
            student_answer=request.student_answer,
            is_correct=request.is_correct,
            score=score
        )

        session.add(result)
        session.commit()
        session.refresh(result)

        return {
            "id": result.id,
            "student_id": result.student_id,
            "subject_id": result.subject_id,
            "question": result.question,
            "student_answer": result.student_answer,
            "is_correct": result.is_correct,
            "score": result.score,
            "analysis_report": result.analysis_report,
            "timestamp": str(result.timestamp)
        }


@router.post("/{student_id}/subject/{subject_id}/quiz-attempt/analyze")
def analyze_subject_quiz_attempt(
    student_id: int,
    subject_id: int,
    request: AnalyzeQuizAttemptRequest
):
    """
    Analyze the FULL quiz attempt.

    This is the new weak-topic logic:
    - the student finishes all questions
    - the whole quiz attempt is analyzed globally
    - weak topics are inferred from overall patterns
    - topic progress is saved
    - one final quiz result is saved
    """
    with DBSession(engine) as session:
        student, subject = validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

    if request.total_questions <= 0:
        raise HTTPException(
            status_code=400,
            detail="total_questions must be greater than 0"
        )

    if request.correct_count < 0:
        raise HTTPException(
            status_code=400,
            detail="correct_count cannot be negative"
        )

    if request.correct_count > request.total_questions:
        raise HTTPException(
            status_code=400,
            detail="correct_count cannot be greater than total_questions"
        )

    answers_payload = [
        {
            "question": answer.question,
            "student_answer": answer.student_answer,
            "correct_answer": answer.correct_answer,
            "is_correct": answer.is_correct,
            "explanation": answer.explanation
        }
        for answer in request.answers
    ]

    result = analyze_full_quiz_attempt(
        student_id=student_id,
        subject_id=subject_id,
        subject_name=subject.name,
        discussion_title=request.discussion_title or "current discussion",
        quiz_focus=request.quiz_focus or "general lecture content",
        quiz_answers=answers_payload,
        correct_count=request.correct_count,
        total_questions=request.total_questions,
        attempt_type=request.attempt_type or "general_quiz"
    )

    return result


# -------------------------------------------------------------------
# Topic progress endpoints
# -------------------------------------------------------------------
@router.get("/{student_id}/subject/{subject_id}/topic-progress")
def get_subject_topic_progress(student_id: int, subject_id: int):
    """
    Get all topic-progress records for a student inside a subject.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        records = session.query(TopicProgress).filter(
            TopicProgress.student_id == student_id,
            TopicProgress.subject_id == subject_id
        ).order_by(TopicProgress.created_at.desc()).all()

        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "subject_id": r.subject_id,
                "weak_topic_id": r.weak_topic_id,
                "quiz_result_id": r.quiz_result_id,
                "topic": r.topic,
                "score": r.score,
                "correct_answers": r.correct_answers,
                "total_questions": r.total_questions,
                "attempt_type": r.attempt_type,
                "analysis": r.analysis,
                "recommendation": r.recommendation,
                "created_at": str(r.created_at)
            }
            for r in records
        ]


@router.get("/{student_id}/subject/{subject_id}/topic-progress/{topic}")
def get_one_topic_progress(student_id: int, subject_id: int, topic: str):
    """
    Get progress history for one specific topic.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        records = session.query(TopicProgress).filter(
            TopicProgress.student_id == student_id,
            TopicProgress.subject_id == subject_id,
            TopicProgress.topic.ilike(topic)
        ).order_by(TopicProgress.created_at.desc()).all()

        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "subject_id": r.subject_id,
                "weak_topic_id": r.weak_topic_id,
                "quiz_result_id": r.quiz_result_id,
                "topic": r.topic,
                "score": r.score,
                "correct_answers": r.correct_answers,
                "total_questions": r.total_questions,
                "attempt_type": r.attempt_type,
                "analysis": r.analysis,
                "recommendation": r.recommendation,
                "created_at": str(r.created_at)
            }
            for r in records
        ]


# -------------------------------------------------------------------
# Document endpoints
# -------------------------------------------------------------------
@router.get("/{student_id}/documents")
def get_documents(student_id: int):
    """
    Backward-compatible endpoint:
    Get all documents uploaded by a student across all subjects.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        documents = session.query(Document).filter(
            Document.student_id == student_id
        ).order_by(Document.uploaded_at.desc()).all()

        return [
            {
                "id": d.id,
                "student_id": d.student_id,
                "subject_id": d.subject_id,
                "filename": d.filename,
                "uploaded_at": str(d.uploaded_at)
            }
            for d in documents
        ]


@router.get("/{student_id}/subject/{subject_id}/documents")
def get_subject_documents(student_id: int, subject_id: int):
    """
    Get all uploaded documents for one student inside one subject.
    """
    with DBSession(engine) as session:
        validate_student_and_subject(
            db=session,
            student_id=student_id,
            subject_id=subject_id
        )

        documents = session.query(Document).filter(
            Document.student_id == student_id,
            Document.subject_id == subject_id
        ).order_by(Document.uploaded_at.desc()).all()

        return [
            {
                "id": d.id,
                "student_id": d.student_id,
                "subject_id": d.subject_id,
                "filename": d.filename,
                "uploaded_at": str(d.uploaded_at)
            }
            for d in documents
        ]