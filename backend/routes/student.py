from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session as DBSession

from db.models import engine, WeakTopic, QuizResult, Document

router = APIRouter()


@router.get("/{student_id}/weak-topics")
def get_weak_topics(student_id: int):
    with DBSession(engine) as session:
        topics = session.query(WeakTopic).filter(
            WeakTopic.student_id == student_id
        ).order_by(WeakTopic.detected_at.desc()).all()

        return [
            {
                "id": t.id,
                "topic": t.topic,
                "detected_at": str(t.detected_at)
            }
            for t in topics
        ]


@router.get("/{student_id}/quiz-results")
def get_quiz_results(student_id: int):
    with DBSession(engine) as session:
        results = session.query(QuizResult).filter(
            QuizResult.student_id == student_id
        ).order_by(QuizResult.timestamp.desc()).all()

        return [
            {
                "id": r.id,
                "question": r.question,
                "student_answer": r.student_answer,
                "is_correct": r.is_correct,
                "score": r.score,
                "timestamp": str(r.timestamp)
            }
            for r in results
        ]


@router.get("/{student_id}/documents")
def get_documents(student_id: int):
    with DBSession(engine) as session:
        documents = session.query(Document).filter(
            Document.student_id == student_id
        ).order_by(Document.uploaded_at.desc()).all()

        return [
            {
                "id": d.id,
                "filename": d.filename,
                "uploaded_at": str(d.uploaded_at)
            }
            for d in documents
        ]