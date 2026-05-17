import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session as DBSession

from db.models import engine
from db.vector_store import store_document, store_chunks
from parsing.document_parser import parse_document

router = APIRouter()

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    student_id: int = Form(...)
):
    # validate file type
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in [".pdf", ".pptx", ".ppt"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF or PPTX file."
        )

    # save file to disk
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # parse into chunks
        chunks = parse_document(file_path)

        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the uploaded file."
            )

        # store document record
        document_id = store_document(
            filename=file.filename,
            student_id=student_id
        )

        # embed and store chunks
        stored = store_chunks(chunks, document_id=document_id)

        return {
            "message": "File uploaded and processed successfully.",
            "document_id": document_id,
            "filename": file.filename,
            "chunks_stored": stored
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))