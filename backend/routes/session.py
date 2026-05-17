from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from db.models import engine, Student, Session as SessionModel, Message

router = APIRouter()


class CreateSessionRequest(BaseModel):
    student_name: str


class CreateSessionResponse(BaseModel):
    student_id: int
    session_id: int
    student_name: str


@router.post("/", response_model=CreateSessionResponse)
def create_session(request: CreateSessionRequest):
    with DBSession(engine) as session:
        # create student if not exists
        student = session.query(Student).filter(
            Student.name == request.student_name
        ).first()

        if not student:
            student = Student(name=request.student_name)
            session.add(student)
            session.flush()

        new_session = SessionModel(student_id=student.id)
        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        session.refresh(student)

        return CreateSessionResponse(
            student_id=student.id,
            session_id=new_session.id,
            student_name=student.name
        )


@router.get("/{session_id}/history")
def get_history(session_id: int):
    with DBSession(engine) as session:
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