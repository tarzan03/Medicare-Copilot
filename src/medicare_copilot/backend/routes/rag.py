import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from src.medicare_copilot.rag.ingestion import ingest
from src.medicare_copilot.rag.retrieval import (
    dense_search,
    sparse_search,
    hybrid_search,
)
from medicare_copilot.utils.db import get_db


rag_router = APIRouter(prefix="/rag", tags=["RAG"])

MAX_PDF_BYTES = 25 * 1024 * 1024


@rag_router.post("/documents")
def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a PDF, chunk it, embed it, and persist the chunks."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    content = file.file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 25 MB upload limit.",
        )

    # Validate the file signature and PDF readability.
    import pymupdf

    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if pdf.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Encrypted PDFs are not supported.",
                )
            if pdf.page_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The PDF contains no pages.",
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a readable PDF.",
        ) from exc

    # Use a temporary file because the ingestion service accepts a path.
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=True,
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()

            result = ingest_pdf(
                Path(temp_file.name),
                db,
            )

        return {
            "status": "success",
            **result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF ingestion failed.",
        ) from exc


@rag_router.get("/search")
def search_documents(
    query: str = Query(..., min_length=1),
    mode: str = Query(default="hybrid"),
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Search indexed document chunks using sparse, dense or hybrid retrieval."""
    if mode == "sparse":
        results = sparse_search(db, query, limit=limit)
    elif mode == "dense":
        results = dense_search(db, query, limit=limit)
    elif mode == "hybrid":
        results = hybrid_search(db, query, limit=limit)
    else:
        raise HTTPException(
            status_code=400,
            detail="mode must be sparse, dense, or hybrid.",
        )

    return {
        "query": query,
        "mode": mode,
        "count": len(results),
        "results": results,
    }
