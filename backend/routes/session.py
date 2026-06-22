from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.models import (
    engine,
    Student,
    Subject,
    Session as SessionModel,
    Message
)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    student_id: int
    subject_id: int
    title: str | None = None


class CreateSessionResponse(BaseModel):
    student_id: int
    subject_id: int
    session_id: int
    title: str | None = None


@router.post("/", response_model=CreateSessionResponse)
def create_session(request: CreateSessionRequest):
    """
    Create a new discussion/session inside a subject.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == request.student_id
        ).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        subject = session.query(Subject).filter(
            Subject.id == request.subject_id,
            Subject.student_id == request.student_id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found for this student"
            )

        clean_title = request.title.strip() if request.title else None

        new_session = SessionModel(
            student_id=request.student_id,
            subject_id=request.subject_id,
            title=clean_title
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return CreateSessionResponse(
            student_id=request.student_id,
            subject_id=request.subject_id,
            session_id=new_session.id,
            title=new_session.title
        )


@router.get("/{session_id}/history")
def get_history(session_id: int):
    """
    Get message history for a discussion/session.
    """
    with DBSession(engine) as session:
        discussion = session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not discussion:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = session.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.timestamp).all()

        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_label": m.agent_label,
                "timestamp": str(m.timestamp)
            }
            for m in messages
        ]


@router.get("/student/{student_id}")
def get_student_sessions(student_id: int):
    """
    Backward-compatible endpoint:
    Get all sessions for a student across all subjects.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        sessions = session.query(SessionModel).filter(
            SessionModel.student_id == student_id
        ).order_by(SessionModel.created_at.desc()).all()

        result = []

        for s in sessions:
            first_message = session.query(Message).filter(
                Message.session_id == s.id,
                Message.role == "user"
            ).order_by(Message.timestamp).first()

            result.append({
                "session_id": s.id,
                "student_id": s.student_id,
                "subject_id": s.subject_id,
                "document_id": s.document_id,
                "title": s.title,
                "created_at": str(s.created_at),
                "preview": first_message.content[:60] if first_message else "Empty discussion"
            })

        return {
            "student_id": student_id,
            "student_name": student.name,
            "sessions": result
        }


@router.get("/subject/{subject_id}")
def get_subject_sessions(subject_id: int):
    """
    Get all discussions/sessions inside one subject.
    """
    with DBSession(engine) as session:
        subject = session.query(Subject).filter(
            Subject.id == subject_id
        ).first()

        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        sessions = session.query(SessionModel).filter(
            SessionModel.subject_id == subject_id
        ).order_by(SessionModel.created_at.desc()).all()

        result = []

        for s in sessions:
            first_message = session.query(Message).filter(
                Message.session_id == s.id,
                Message.role == "user"
            ).order_by(Message.timestamp).first()

            result.append({
                "session_id": s.id,
                "student_id": s.student_id,
                "subject_id": s.subject_id,
                "document_id": s.document_id,
                "title": s.title,
                "created_at": str(s.created_at),
                "preview": first_message.content[:60] if first_message else "Empty discussion"
            })

        return {
            "subject_id": subject.id,
            "subject_name": subject.name,
            "student_id": subject.student_id,
            "sessions": result
        }


@router.post("/student/{student_id}/subject/{subject_id}/new")
def create_new_subject_session(
    student_id: int,
    subject_id: int,
    title: str | None = None
):
    """
    Create a new discussion for a specific student and subject.
    Useful for frontend buttons.
    """
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        subject = session.query(Subject).filter(
            Subject.id == subject_id,
            Subject.student_id == student_id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=404,
                detail="Subject not found for this student"
            )

        clean_title = title.strip() if title else None

        new_session = SessionModel(
            student_id=student_id,
            subject_id=subject_id,
            title=clean_title
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "session_id": new_session.id,
            "student_id": student_id,
            "subject_id": subject_id,
            "title": new_session.title
        }


@router.get("/{session_id}/document")
def get_session_document(session_id: int):
    """
    Get the document linked to a discussion/session.
    """
    with DBSession(engine) as session:
        s = session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": s.id,
            "student_id": s.student_id,
            "subject_id": s.subject_id,
            "document_id": s.document_id
        }


@router.delete("/{session_id}")
def delete_session(session_id: int):
    """
    Delete a discussion/session and its messages.
    """
    with DBSession(engine) as session:
        s = session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        session.delete(s)
        session.commit()

    return {
        "deleted": session_id
    }