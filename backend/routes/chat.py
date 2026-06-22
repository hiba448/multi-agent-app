from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from sqlalchemy.orm import Session as DBSession

from db.models import engine, Message, Session as SessionModel, Subject, Document
from backend.agents.orchestrator import run_orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    request: str
    document_id: int
    student_id: int
    session_id: int
    subject_id: int
    extra: Optional[Dict] = None


@router.post("/")
async def chat(body: ChatRequest):
    try:
        with DBSession(engine) as db:
            current_session = db.query(SessionModel).filter(
                SessionModel.id == body.session_id,
                SessionModel.student_id == body.student_id,
                SessionModel.subject_id == body.subject_id
            ).first()

            if not current_session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found for this student and subject."
                )

            subject = db.query(Subject).filter(
                Subject.id == body.subject_id,
                Subject.student_id == body.student_id
            ).first()

            if not subject:
                raise HTTPException(
                    status_code=404,
                    detail="Subject not found for this student."
                )

            document = db.query(Document).filter(
                Document.id == body.document_id,
                Document.student_id == body.student_id,
                Document.subject_id == body.subject_id
            ).first()

            if not document:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found for this student and subject."
                )

            if current_session.document_id != body.document_id:
                raise HTTPException(
                    status_code=400,
                    detail="This document is not linked to the selected session."
                )

            db.add(Message(
                session_id=body.session_id,
                role="user",
                content=body.request,
                agent_label=None
            ))
            db.commit()

        result = run_orchestrator(
            request=body.request,
            document_id=body.document_id,
            student_id=body.student_id,
            subject_id=body.subject_id,
            extra=body.extra
        )

        agent_label = result.get("agent", "orchestrator")
        content = build_content_string(result)

        with DBSession(engine) as db:
            db.add(Message(
                session_id=body.session_id,
                role="agent",
                content=content,
                agent_label=agent_label
            ))
            db.commit()

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_content_string(result: Dict) -> str:
    """
    Convert agent result to a plain string for message history storage.
    """
    intent = result.get("intent", "")

    if intent == "SUMMARIZE":
        return result.get("summary", "")

    if intent == "QUESTION":
        return result.get("answer", "")

    if intent == "QUIZ":
        questions = result.get("questions", [])
        return str(len(questions)) + " questions generated."

    if intent == "EVALUATE":
        return result.get("feedback", "")

    if intent == "EXPLAIN":
        return result.get("explanation", "")

    return str(result)