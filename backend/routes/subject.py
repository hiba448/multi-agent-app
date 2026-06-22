from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.models import (
    engine,
    Student,
    Subject,
    Session as SessionModel,
    Message,
    Document,
    DocumentChunk,
    WeakTopic,
    QuizResult,
    TopicProgress
)

router = APIRouter()


# -------------------------------------------------------------------
# Request models
# -------------------------------------------------------------------
class CreateSubjectRequest(BaseModel):
    student_id: int
    name: str
    description: Optional[str] = None


class UpdateSubjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def subject_to_dict(subject: Subject):
    return {
        "id": subject.id,
        "student_id": subject.student_id,
        "name": subject.name,
        "description": subject.description,
        "created_at": str(subject.created_at)
    }


# -------------------------------------------------------------------
# Get all subjects for student
# -------------------------------------------------------------------
@router.get("/student/{student_id}")
def get_student_subjects(student_id: int):
    """
    Get all subjects for a specific student.
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

        subjects = session.query(Subject).filter(
            Subject.student_id == student_id
        ).order_by(Subject.created_at.desc()).all()

        return [
            subject_to_dict(subject)
            for subject in subjects
        ]


# -------------------------------------------------------------------
# Create subject
# -------------------------------------------------------------------
@router.post("/")
def create_subject(request: CreateSubjectRequest):
    """
    Create a new subject for a student.
    Subject names must be unique per student.
    """
    clean_name = request.name.strip()

    if not clean_name:
        raise HTTPException(
            status_code=400,
            detail="Subject name cannot be empty."
        )

    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == request.student_id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        existing_subject = session.query(Subject).filter(
            Subject.student_id == request.student_id,
            Subject.name == clean_name
        ).first()

        if existing_subject:
            raise HTTPException(
                status_code=400,
                detail="A subject with this name already exists."
            )

        subject = Subject(
            student_id=request.student_id,
            name=clean_name,
            description=request.description
        )

        session.add(subject)
        session.commit()
        session.refresh(subject)

        return subject_to_dict(subject)


# -------------------------------------------------------------------
# Get one subject
# -------------------------------------------------------------------
@router.get("/{subject_id}")
def get_subject(subject_id: int):
    """
    Get one subject by id.
    """
    with DBSession(engine) as session:
        subject = session.query(Subject).filter(
            Subject.id == subject_id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )

        return subject_to_dict(subject)


# -------------------------------------------------------------------
# Update subject
# -------------------------------------------------------------------
@router.put("/{subject_id}")
def update_subject(subject_id: int, request: UpdateSubjectRequest):
    """
    Update subject name or description.
    """
    with DBSession(engine) as session:
        subject = session.query(Subject).filter(
            Subject.id == subject_id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )

        if request.name is not None:
            clean_name = request.name.strip()

            if not clean_name:
                raise HTTPException(
                    status_code=400,
                    detail="Subject name cannot be empty."
                )

            existing_subject = session.query(Subject).filter(
                Subject.student_id == subject.student_id,
                Subject.name == clean_name,
                Subject.id != subject_id
            ).first()

            if existing_subject:
                raise HTTPException(
                    status_code=400,
                    detail="A subject with this name already exists."
                )

            subject.name = clean_name

        if request.description is not None:
            subject.description = request.description

        session.commit()
        session.refresh(subject)

        return subject_to_dict(subject)


# -------------------------------------------------------------------
# Delete subject safely
# -------------------------------------------------------------------
@router.delete("/{subject_id}")
def delete_subject(subject_id: int):
    """
    Delete a subject and all related data safely.

    Deletion order matters because of foreign key constraints:

    1. messages depend on sessions
    2. sessions belong to subject and may reference documents
    3. topic_progress may reference weak_topics and quiz_results
    4. document_chunks depend on documents
    5. documents belong to subject
    6. weak_topics and quiz_results belong to subject
    7. subject is deleted last
    """

    with DBSession(engine) as session:
        subject = session.query(Subject).filter(
            Subject.id == subject_id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )

        try:
            # -----------------------------------------------------
            # 1. Get all sessions/discussions for this subject
            # -----------------------------------------------------
            subject_sessions = session.query(SessionModel).filter(
                SessionModel.subject_id == subject_id
            ).all()

            session_ids = [
                s.id for s in subject_sessions
            ]

            # -----------------------------------------------------
            # 2. Get all documents for this subject
            # -----------------------------------------------------
            subject_documents = session.query(Document).filter(
                Document.subject_id == subject_id
            ).all()

            document_ids = [
                d.id for d in subject_documents
            ]

            # -----------------------------------------------------
            # 3. Delete messages first
            # messages reference sessions, so they must be removed
            # before deleting sessions.
            # -----------------------------------------------------
            if session_ids:
                session.query(Message).filter(
                    Message.session_id.in_(session_ids)
                ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 4. Delete sessions/discussions
            # -----------------------------------------------------
            if session_ids:
                session.query(SessionModel).filter(
                    SessionModel.id.in_(session_ids)
                ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 5. Delete topic progress before weak topics and quiz results
            # because topic_progress can reference both.
            # -----------------------------------------------------
            session.query(TopicProgress).filter(
                TopicProgress.subject_id == subject_id
            ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 6. Delete weak topics
            # -----------------------------------------------------
            session.query(WeakTopic).filter(
                WeakTopic.subject_id == subject_id
            ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 7. Delete quiz results
            # -----------------------------------------------------
            session.query(QuizResult).filter(
                QuizResult.subject_id == subject_id
            ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 8. Delete document chunks before documents
            # -----------------------------------------------------
            if document_ids:
                session.query(DocumentChunk).filter(
                    DocumentChunk.document_id.in_(document_ids)
                ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 9. Delete documents
            # -----------------------------------------------------
            if document_ids:
                session.query(Document).filter(
                    Document.id.in_(document_ids)
                ).delete(synchronize_session=False)

            # -----------------------------------------------------
            # 10. Delete subject itself
            # -----------------------------------------------------
            session.delete(subject)
            session.commit()

            return {
                "deleted": subject_id,
                "sessions_deleted": len(session_ids),
                "documents_deleted": len(document_ids)
            }

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Could not delete subject: {str(e)}"
            )