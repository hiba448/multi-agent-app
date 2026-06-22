import os
import shutil
import json
import re
from typing import Optional, List, Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session as DBSession

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from db.models import (
    engine,
    Session as SessionModel,
    Student,
    Subject,
    Document,
    DocumentChunk
)
from db.vector_store import store_document, store_chunks
from parsing.document_parser import parse_document

load_dotenv()

router = APIRouter()

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL"),
    base_url=os.getenv("OLLAMA_BASE_URL"),
    temperature=0.0
)


DOCUMENT_RELEVANCE_PROMPT = ChatPromptTemplate.from_template("""
You are a strict academic document relevance checker.

A student is working inside this subject:

SUBJECT NAME:
{subject_name}

SUBJECT DESCRIPTION:
{subject_description}

Existing documents/chunks already accepted in this subject:
{existing_subject_context}

The student uploaded a new document. Here is an excerpt:

NEW DOCUMENT EXCERPT:
{new_document_excerpt}

Your task:
Decide whether the new document belongs to the same academic subject/topic.

Rules:
- Accept if the document clearly belongs to the subject.
- Accept if it is a subtopic, chapter, prerequisite, or continuation of the subject.
- Reject if it is about an unrelated academic field.
- If the subject name is broad and the document reasonably fits, accept.
- If there are existing documents, the new document should be coherent with them.
- Do not reject only because the document uses different wording.
- Be strict for obviously unrelated documents.
- If uncertain but the document seems academically close to the subject, accept with medium confidence.
- If the document is empty or impossible to understand, reject.

Return valid JSON only with this exact structure:

{{
  "relevant": true,
  "confidence": 0.0,
  "reason": "short explanation"
}}
""")


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def build_new_document_excerpt(
    chunks: List[Dict],
    max_chunks: int = 8,
    max_chars: int = 5000
) -> str:
    """
    Build a compact excerpt from the newly uploaded document.
    """
    text_parts = []

    for chunk in chunks[:max_chunks]:
        page = chunk.get("page")
        content = chunk.get("content", "")

        if content:
            text_parts.append(f"[Page {page}]\n{content}")

    excerpt = "\n\n".join(text_parts)

    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "\n...[truncated]"

    return excerpt


def get_existing_subject_context(
    db: DBSession,
    subject_id: int,
    max_docs: int = 3,
    max_chunks_per_doc: int = 2,
    max_chars: int = 4000
) -> str:
    """
    Retrieve short excerpts from already accepted documents in the subject.

    This helps the checker decide whether the new document is coherent
    with the subject's existing material.
    """
    documents = db.query(Document).filter(
        Document.subject_id == subject_id
    ).order_by(Document.uploaded_at.desc()).limit(max_docs).all()

    if not documents:
        return "No existing documents yet."

    parts = []

    for document in documents:
        parts.append(f"Document: {document.filename}")

        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).order_by(DocumentChunk.page_number.asc()).limit(max_chunks_per_doc).all()

        for chunk in chunks:
            content = chunk.content or ""
            parts.append(f"[Page {chunk.page_number}]\n{content[:1200]}")

    context = "\n\n".join(parts)

    if len(context) > max_chars:
        context = context[:max_chars] + "\n...[truncated]"

    return context


def extract_json_from_llm(text: str) -> Dict:
    """
    Parse JSON from the LLM response safely.
    """
    clean = text.strip()

    try:
        return json.loads(clean)
    except Exception:
        pass

    match = re.search(r"\{.*\}", clean, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {
        "relevant": False,
        "confidence": 0.0,
        "reason": "Could not parse document relevance response."
    }


def validate_document_relevance(
    subject_name: str,
    subject_description: Optional[str],
    existing_subject_context: str,
    new_document_excerpt: str
) -> Dict:
    """
    Ask the local LLM whether the uploaded document belongs to the subject.
    """
    prompt = DOCUMENT_RELEVANCE_PROMPT.format_messages(
        subject_name=subject_name,
        subject_description=subject_description or "No description provided.",
        existing_subject_context=existing_subject_context,
        new_document_excerpt=new_document_excerpt
    )

    response = llm.invoke(prompt)
    parsed = extract_json_from_llm(response.content)

    relevant = parsed.get("relevant", False)

    if isinstance(relevant, str):
        relevant = relevant.strip().lower() in ["true", "yes", "1"]

    confidence = parsed.get("confidence", 0.0)

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    if confidence < 0:
        confidence = 0.0

    if confidence > 1:
        confidence = 1.0

    reason = parsed.get("reason", "No reason provided.")

    return {
        "relevant": bool(relevant),
        "confidence": confidence,
        "reason": reason
    }


def remove_temp_file(file_path: str):
    """
    Remove temporary uploaded file if it exists.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


# -------------------------------------------------------------------
# Upload endpoint
# -------------------------------------------------------------------
@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    student_id: int = Form(...),
    session_id: int = Form(...),
    subject_id: Optional[int] = Form(None)
):
    """
    Upload and process a lecture document.

    The document is linked to:
    - student
    - subject
    - current discussion/session

    New behavior:
    Before storing the document in the database, the backend checks
    whether the file belongs to the selected subject.
    """

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in [".pdf", ".pptx", ".ppt"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF or PPTX file."
        )

    # ------------------------------------------------------------
    # Validate student, session, and subject
    # ------------------------------------------------------------
    with DBSession(engine) as db:
        student = db.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        current_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.student_id == student_id
        ).first()

        if not current_session:
            raise HTTPException(
                status_code=404,
                detail="Session not found for this student"
            )

        if subject_id is None:
            subject_id = current_session.subject_id

        if subject_id is None:
            raise HTTPException(
                status_code=400,
                detail="Subject is required for uploading a document."
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

        if current_session.subject_id is not None and current_session.subject_id != subject_id:
            raise HTTPException(
                status_code=400,
                detail="This session does not belong to the selected subject."
            )

    # ------------------------------------------------------------
    # Save temporarily to parse it
    # ------------------------------------------------------------
    safe_filename = (
        f"student_{student_id}_subject_{subject_id}_session_{session_id}_{file.filename}"
    )
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks = parse_document(file_path)

        if not chunks:
            remove_temp_file(file_path)
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the uploaded file."
            )

        # ------------------------------------------------------------
        # Subject relevance validation
        # ------------------------------------------------------------
        with DBSession(engine) as db:
            subject = db.query(Subject).filter(
                Subject.id == subject_id,
                Subject.student_id == student_id
            ).first()

            if not subject:
                remove_temp_file(file_path)
                raise HTTPException(
                    status_code=404,
                    detail="Subject not found for this student"
                )

            existing_subject_context = get_existing_subject_context(
                db=db,
                subject_id=subject_id
            )

            new_document_excerpt = build_new_document_excerpt(chunks)

            relevance_result = validate_document_relevance(
                subject_name=subject.name,
                subject_description=subject.description,
                existing_subject_context=existing_subject_context,
                new_document_excerpt=new_document_excerpt
            )

            subject_name_for_error = subject.name

        if not relevance_result["relevant"]:
            remove_temp_file(file_path)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "This document does not appear to match the current subject. "
                        "Please upload it under a more appropriate subject or create a new subject."
                    ),
                    "subject_id": subject_id,
                    "subject_name": subject_name_for_error,
                    "filename": file.filename,
                    "validation": relevance_result
                }
            )

        # ------------------------------------------------------------
        # Store document only after validation passes
        # ------------------------------------------------------------
        document_id = store_document(
            filename=file.filename,
            student_id=student_id,
            subject_id=subject_id
        )

        stored = store_chunks(
            chunks,
            document_id=document_id
        )

        # ------------------------------------------------------------
        # Link document to session
        # ------------------------------------------------------------
        with DBSession(engine) as db:
            current_session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.student_id == student_id,
                SessionModel.subject_id == subject_id
            ).first()

            if not current_session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found after document processing."
                )

            current_session.document_id = document_id
            db.commit()

        return {
            "message": "File uploaded and processed successfully.",
            "document_id": document_id,
            "student_id": student_id,
            "subject_id": subject_id,
            "session_id": session_id,
            "filename": file.filename,
            "chunks_stored": stored,
            "subject_validation": relevance_result
        }

    except HTTPException:
        raise

    except Exception as e:
        remove_temp_file(file_path)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )