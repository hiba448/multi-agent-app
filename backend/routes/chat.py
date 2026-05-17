from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from sqlalchemy.orm import Session as DBSession

from db.models import engine, Message
from backend.agents.orchestrator import run_orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    request: str
    document_id: int
    student_id: int
    session_id: int
    extra: Optional[Dict] = None


@router.post("/")
async def chat(body: ChatRequest):
    try:
        # save user message
        with DBSession(engine) as session:
            session.add(Message(
                session_id=body.session_id,
                role="user",
                content=body.request,
                agent_label=None
            ))
            session.commit()

        # run orchestrator
        result = run_orchestrator(
            request=body.request,
            document_id=body.document_id,
            student_id=body.student_id,
            extra=body.extra
        )

        # build response content for message history
        agent_label = result.get("agent", "orchestrator")
        content = build_content_string(result)

        # save agent response
        with DBSession(engine) as session:
            session.add(Message(
                session_id=body.session_id,
                role="agent",
                content=content,
                agent_label=agent_label
            ))
            session.commit()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_content_string(result: Dict) -> str:
    """Convert agent result to a plain string for message history storage."""
    intent = result.get("intent", "")

    if intent == "SUMMARIZE":
        return result.get("summary", "")
    elif intent == "QUESTION":
        return result.get("answer", "")
    elif intent == "QUIZ":
        questions = result.get("questions", [])
        return str(len(questions)) + " questions generated."
    elif intent == "EVALUATE":
        return result.get("feedback", "")
    elif intent == "EXPLAIN":
        return result.get("explanation", "")

    return str(result)