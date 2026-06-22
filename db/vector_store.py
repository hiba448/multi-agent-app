import os
import httpx
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select
from dotenv import load_dotenv

from db.models import engine, DocumentChunk, Document

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL")


def get_embedding(text: str):
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={
            "model": OLLAMA_EMBED_MODEL or "nomic-embed-text",
            "input": text
        },
        timeout=30.0
    )

    response.raise_for_status()
    data = response.json()

    return data["embeddings"][0]


def store_chunks(
    chunks: List[Dict],
    document_id: int
) -> int:
    """
    Generate embeddings for each chunk and store them
    in the document_chunks table.

    Returns the number of chunks stored.
    """
    with Session(engine) as session:
        stored = 0

        for chunk in chunks:
            embedding = get_embedding(chunk["content"])

            db_chunk = DocumentChunk(
                document_id=document_id,
                content=chunk["content"],
                embedding=embedding,
                page_number=chunk["page"]
            )

            session.add(db_chunk)
            stored += 1

        session.commit()
        return stored


def retrieve_similar_chunks(
    query: str,
    document_id: int,
    top_k: int = 5
) -> List[Dict]:
    """
    Retrieve the top_k most semantically similar chunks
    to the query from a specific document.

    Uses cosine distance via pgvector.
    """
    query_embedding = get_embedding(query)

    with Session(engine) as session:
        results = session.execute(
            select(
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            .where(DocumentChunk.document_id == document_id)
            .order_by("distance")
            .limit(top_k)
        ).fetchall()

    return [
        {
            "content": row.content,
            "page": row.page_number,
            "distance": round(row.distance, 4)
        }
        for row in results
    ]


def store_document(
    filename: str,
    student_id: int,
    subject_id: Optional[int] = None
) -> int:
    """
    Create a document record in the database.

    The document belongs to:
    - a student
    - optionally a subject

    Returns the new document id.
    """
    with Session(engine) as session:
        document = Document(
            filename=filename,
            student_id=student_id,
            subject_id=subject_id
        )

        session.add(document)
        session.commit()
        session.refresh(document)

        return document.id