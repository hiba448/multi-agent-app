import os
import shutil
import json
import re
import unicodedata
from typing import Optional, List, Dict, Set

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
You are an academic document relevance checker.

A student is working inside this subject:

SUBJECT NAME:
{subject_name}

SUBJECT DESCRIPTION:
{subject_description}

Existing accepted material in this subject:
{existing_subject_context}

The student uploaded a new document. Here is an excerpt:

NEW DOCUMENT EXCERPT:
{new_document_excerpt}

Your task:
Decide whether the uploaded document should be accepted into this subject.

Important principle:
The document must be academically relevant to the subject itself. The language
used in the document is not enough to make it relevant.

For example:
- A time series document written in French is NOT relevant to a French language
  or French literature subject.
- A machine learning document written in French is NOT relevant to a French
  subject unless it is mainly about French language processing, French linguistics,
  French literature, grammar, writing, or text analysis.
- A technical document should be accepted only in a subject where the technical
  topic is academically expected.

Balanced rules:
- Accept if the uploaded document clearly matches the subject name or its main academic topic.
- Accept if it discusses a direct chapter, subtopic, prerequisite, application,
  method, or continuation of the subject.
- Accept if it uses different wording but clearly belongs to the same course area.
- Reject if the document mainly belongs to another academic field.
- Reject if the only connection is language, weak analogy, broad interpretation,
  or indirect interdisciplinary relation.
- Reject if the document could be discussed from the subject perspective, but the
  document itself is not mainly about that subject.
- If existing documents are available, use them as additional context, but do not
  reject a valid new chapter only because it introduces a new topic inside the
  same subject.
- If the document is empty or impossible to understand, reject.

Subject-specific examples:
- Subject "Time Series": accept documents about forecasting, ARIMA, stationarity,
  autocorrelation, trend, seasonality, temporal data, stochastic processes, or
  time-dependent observations.
- Subject "French": accept documents about French grammar, vocabulary, writing,
  literature, poetry, novels, text analysis, rhetoric, linguistics, or French
  language learning.
- Subject "French": reject documents about time series, machine learning,
  databases, operating systems, mathematics, statistics, or engineering when the
  main content is technical rather than language/literature.
- Subject "Machine Learning": accept documents about regression, classification,
  neural networks, clustering, model evaluation, training, features, or datasets.
- Subject "Philosophy": accept documents mainly about ethics, logic, metaphysics,
  epistemology, philosophy of mind, political philosophy, philosophy of science,
  or philosophy of technology.
- Subject "Philosophy": reject technical machine learning documents unless the
  main focus is philosophical analysis, ethics, consciousness, knowledge, or
  social implications.

Confidence rules:
- Use confidence above 0.80 only when the document clearly belongs to the subject.
- Use confidence between 0.65 and 0.80 when the document is probably relevant.
- Use confidence below 0.65 when the relation is weak, indirect, or unclear.
- Mark relevant=true only when the document is clearly or probably relevant.
- Mark relevant=false when the document mainly belongs to another field.

Return valid JSON only with this exact structure:

{{
  "relevant": false,
  "confidence": 0.0,
  "reason": "short explanation"
}}
""")


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def build_new_document_excerpt(
    chunks: List[Dict],
    max_chunks: int = 12,
    max_chars: int = 8000
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


def normalize_text_for_match(text: str) -> str:
    """
    Normalize text for reliable keyword matching.
    Handles accents, punctuation, and case.
    """
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def keyword_in_text(keyword: str, normalized_text: str) -> bool:
    """
    Check whether a normalized keyword or phrase appears in normalized text.
    Word padding avoids many accidental substring matches.
    """
    normalized_keyword = normalize_text_for_match(keyword)

    if not normalized_keyword:
        return False

    return f" {normalized_keyword} " in f" {normalized_text} "


ACADEMIC_FIELD_KEYWORDS = {
    "time_series": {
        "time series", "serie temporelle", "series temporelles",
        "forecasting", "prevision", "previsions", "prediction",
        "arima", "sarima", "arma", "stationarity", "stationnarite",
        "autocorrelation", "seasonality", "saisonnalite",
        "trend", "tendance", "temporal", "temporel", "chronologique",
        "stochastic process", "processus stochastique", "lag", "retard",
        "moving average", "moyenne mobile"
    },
    "machine_learning": {
        "machine learning", "apprentissage automatique",
        "supervised learning", "unsupervised learning",
        "classification", "regression", "neural network", "reseau de neurones",
        "clustering", "model training", "training set", "dataset",
        "features", "gradient descent", "descente de gradient",
        "loss function", "fonction de cout", "overfitting", "underfitting"
    },
    "statistics_math": {
        "statistics", "statistique", "probability", "probabilite",
        "variance", "mean", "moyenne", "standard deviation", "ecart type",
        "hypothesis test", "test d hypothese", "distribution",
        "random variable", "variable aleatoire", "correlation"
    },
    "databases": {
        "database", "base de donnees", "sql", "relational model",
        "modele relationnel", "normalization", "normalisation",
        "transaction", "index", "query", "requete", "schema", "table"
    },
    "operating_systems": {
        "operating system", "systeme d exploitation", "process",
        "processus", "thread", "memory management", "gestion memoire",
        "scheduling", "ordonnancement", "file system", "systeme de fichiers",
        "deadlock", "interblocage"
    },
    "french_language_literature": {
        "french grammar", "grammaire francaise", "conjugaison",
        "orthographe", "vocabulaire", "syntax", "syntaxe",
        "litterature francaise", "literature francaise", "poesie",
        "poeme", "roman", "theatre", "rhetorique", "analyse de texte",
        "commentaire compose", "dissertation", "expression ecrite",
        "langue francaise", "linguistique francaise", "texte litteraire",
        "auteur", "narrateur", "figure de style", "metaphore"
    },
    "philosophy": {
        "philosophy", "philosophie", "ethics", "ethique",
        "logic", "logique", "metaphysics", "metaphysique",
        "epistemology", "epistemologie", "knowledge", "connaissance",
        "consciousness", "conscience", "mind", "esprit",
        "political philosophy", "philosophie politique",
        "philosophy of science", "philosophie des sciences",
        "ontology", "ontologie"
    }
}


SUBJECT_CATEGORY_ALIASES = {
    "time_series": {
        "time series", "series temporelles", "serie temporelle",
        "temporal data", "analyse des series temporelles"
    },
    "machine_learning": {
        "machine learning", "apprentissage automatique",
        "artificial intelligence", "intelligence artificielle"
    },
    "statistics_math": {
        "statistics", "statistique", "probability", "probabilite",
        "math", "mathematics", "mathematiques"
    },
    "databases": {
        "database", "databases", "base de donnees", "bases de donnees", "sql"
    },
    "operating_systems": {
        "operating systems", "operating system", "systeme d exploitation",
        "systemes d exploitation"
    },
    "french_language_literature": {
        "french", "francais", "langue francaise", "french language",
        "french literature", "litterature francaise", "literature francaise"
    },
    "philosophy": {
        "philosophy", "philosophie"
    }
}


def detect_subject_categories(
    subject_name: str,
    subject_description: Optional[str]
) -> Set[str]:
    """
    Detect the intended academic category of the subject.
    """
    text = normalize_text_for_match(
        f"{subject_name or ''} {subject_description or ''}"
    )

    categories = set()

    for category, aliases in SUBJECT_CATEGORY_ALIASES.items():
        for alias in aliases:
            if keyword_in_text(alias, text):
                categories.add(category)
                break

    return categories


def detect_document_categories(document_excerpt: str) -> Set[str]:
    """
    Detect academic categories strongly present in the uploaded document.
    """
    text = normalize_text_for_match(document_excerpt)

    categories = set()

    for category, keywords in ACADEMIC_FIELD_KEYWORDS.items():
        hits = 0

        for keyword in keywords:
            if keyword_in_text(keyword, text):
                hits += 1

        if hits >= 2:
            categories.add(category)

    return categories


def has_direct_subject_match(subject_name: str, document_excerpt: str) -> bool:
    """
    Detect obvious direct subject matches such as:
    subject = "Time Series"
    document contains "time series" or "series temporelles".

    This is intentionally not used for language subjects such as French,
    because a document written in French is not automatically relevant to
    a French language/literature subject.
    """
    subject = normalize_text_for_match(subject_name)
    excerpt = normalize_text_for_match(document_excerpt)

    if not subject or not excerpt:
        return False

    language_subjects = {
        "french", "francais", "english", "anglais", "arabic", "arabe",
        "spanish", "espagnol", "german", "allemand"
    }

    if subject in language_subjects:
        return False

    if keyword_in_text(subject, excerpt):
        return True

    stopwords = {
        "the", "a", "an", "of", "and", "or", "to", "for", "in", "on",
        "course", "subject", "introduction", "intro", "chapter", "module"
    }

    subject_terms = [
        term for term in subject.split()
        if term not in stopwords and len(term) > 2
    ]

    if len(subject_terms) >= 2:
        matched_terms = [
            term for term in subject_terms
            if keyword_in_text(term, excerpt)
        ]
        return len(matched_terms) >= 2

    return False


def deterministic_relevance_gate(
    subject_name: str,
    subject_description: Optional[str],
    document_excerpt: str
) -> Dict:
    """
    Apply deterministic academic safeguards before trusting the LLM.

    This prevents cases such as:
    - Subject: French
    - Document: Time series document written in French
    from being incorrectly accepted.
    """
    subject_categories = detect_subject_categories(
        subject_name=subject_name,
        subject_description=subject_description
    )

    document_categories = detect_document_categories(document_excerpt)

    direct_match = has_direct_subject_match(
        subject_name=subject_name,
        document_excerpt=document_excerpt
    )

    # Obvious mismatch:
    # known subject category + known document category + no overlap.
    if subject_categories and document_categories:
        overlap = subject_categories.intersection(document_categories)

        if not overlap and not direct_match:
            return {
                "decision": "reject",
                "confidence": 0.05,
                "reason": (
                    "The uploaded document mainly belongs to a different academic "
                    "field from the selected subject. The language of the document "
                    "does not make it relevant to the subject."
                ),
                "subject_categories": list(subject_categories),
                "document_categories": list(document_categories),
                "direct_match": direct_match
            }

        if overlap:
            return {
                "decision": "accept",
                "confidence": 0.88,
                "reason": (
                    "The uploaded document matches the academic field of the "
                    "selected subject."
                ),
                "subject_categories": list(subject_categories),
                "document_categories": list(document_categories),
                "direct_match": direct_match
            }

    # Direct non-language subject match.
    if direct_match:
        return {
            "decision": "accept",
            "confidence": 0.9,
            "reason": (
                "The uploaded document directly matches the selected subject or "
                "one of its main academic topics."
            ),
            "subject_categories": list(subject_categories),
            "document_categories": list(document_categories),
            "direct_match": direct_match
        }

    return {
        "decision": "llm",
        "confidence": None,
        "reason": "",
        "subject_categories": list(subject_categories),
        "document_categories": list(document_categories),
        "direct_match": direct_match
    }


def validate_document_relevance(
    subject_name: str,
    subject_description: Optional[str],
    existing_subject_context: str,
    new_document_excerpt: str
) -> Dict:
    """
    Decide whether the uploaded document belongs to the selected subject.

    The validation combines deterministic academic-field checks with the LLM.
    Deterministic checks protect against obvious mismatches.
    The LLM handles softer academic judgement cases.
    """
    gate = deterministic_relevance_gate(
        subject_name=subject_name,
        subject_description=subject_description,
        document_excerpt=new_document_excerpt
    )

    if gate["decision"] == "reject":
        return {
            "relevant": False,
            "confidence": gate["confidence"],
            "reason": gate["reason"]
        }

    if gate["decision"] == "accept":
        return {
            "relevant": True,
            "confidence": gate["confidence"],
            "reason": gate["reason"]
        }

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

    if confidence < 0.65:
        relevant = False
        reason = (
            "The document was not accepted because its academic relation to the "
            "selected subject is not strong enough. " + str(reason)
        )

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

        if (
            current_session.subject_id is not None
            and current_session.subject_id != subject_id
        ):
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