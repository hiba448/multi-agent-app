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
    
@router.get("/student/{student_id}")
def get_student_sessions(student_id: int):
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
            # get first message as preview
            first_message = session.query(Message).filter(
                Message.session_id == s.id,
                Message.role == "user"
            ).order_by(Message.timestamp).first()

            result.append({
                "session_id": s.id,
                "created_at": str(s.created_at),
                "preview": first_message.content[:60] if first_message else "Empty session"
            })

        return {
            "student_id": student_id,
            "student_name": student.name,
            "sessions": result
        }


@router.post("/student/{student_id}/new")
def create_new_session(student_id: int):
    with DBSession(engine) as session:
        student = session.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        new_session = SessionModel(student_id=student_id)
        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "session_id": new_session.id,
            "student_id": student_id
        }
    
@router.get("/{session_id}/document")
def get_session_document(session_id: int):
    with DBSession(engine) as session:
        s = session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()

        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"document_id": s.document_id}
    
@router.delete("/{session_id}")
def delete_session(session_id: int):
    with DBSession(engine) as session:
        s = session.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        session.delete(s)
        session.commit()
    return {"deleted": session_id}