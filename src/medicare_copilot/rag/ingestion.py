from pathlib import Path
from uuid import uuid4
from typing import Any

import pymupdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sqlalchemy.orm import Session
import cohere
from src.medicare_copilot.backend.models import RAGChunk
from src.medicare_copilot.rag.embeddings import embed_documents


EMBEDDING_DIMENSION = 1024
EMBEDDING_BATCH_SIZE = 32

# co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

# response = co.embed(
#     model="embed-v4.0", texts=texts, input_type="classification", output_dimension=1024
# )


# embeddings = CohereEmbeddings(
#     model="embed-v4.0",
#     cohere_api_key=settings.COHERE_API_KEY,
#     output_dimension=EMBEDDING_DIMENSION,
# )

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""],
    add_start_index=True,
)


def extract_pdf_pages(pdf_path: Path) -> list[Document]:
    """Extract text from a PDF while preserving page numbers."""
    documents = []

    with pymupdf.open(str(pdf_path)) as pdf:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        for page_index, page in enumerate(pdf):
            text = page.get_text("text").strip()

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "document_name": pdf_path.name,
                        "page_number": page_index + 1,
                    },
                )
            )

    if not documents:
        raise ValueError(
            "No extractable text found. The PDF may be scanned and require OCR."
        )

    return documents


def create_chunks(
    pdf_path: Path,
) -> list[Document]:
    """Split extracted page text into overlapping chunks."""
    pages = extract_pdf_pages(pdf_path)
    chunks = splitter.split_documents(pages)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index

    return chunks


def embed_in_batches(
    chunks: list[Document],
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """Generate embeddings in batches to limit memory usage."""
    vectors = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [chunk.page_content for chunk in batch]

        batch_vectors = embed_documents(texts)

        if len(batch_vectors) != len(batch):
            raise RuntimeError("Embedding count does not match chunk count.")

        for vector in batch_vectors:
            if len(vector) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Expected {EMBEDDING_DIMENSION} embedding dimensions; "
                    f"received {len(vector)}."
                )

        vectors.extend(batch_vectors)

    return vectors


def ingest_pdf(
    pdf_path: Path,
    db: Session,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """
    Extract, chunk, embed and persist a PDF.

    The database transaction covers the chunk insertions.
    ``original_filename`` should be the user-supplied file name; if omitted
    the basename of ``pdf_path`` is used (which may be a temp-file name).
    """
    pdf_path = Path(pdf_path)
    display_name = original_filename or pdf_path.name

    chunks = create_chunks(pdf_path)
    vectors = embed_in_batches(chunks)

    document_id = uuid4()
    records = []

    for chunk, vector in zip(chunks, vectors):
        page_number = chunk.metadata["page_number"]

        records.append(
            RAGChunk(
                document_id=document_id,
                document_name=display_name,
                chunk_index=chunk.metadata["chunk_index"],
                content=chunk.page_content,
                start_page=page_number,
                end_page=page_number,
                embedding=vector,
                chunk_metadata={
                    "page_number": page_number,
                    "start_index": chunk.metadata.get("start_index"),
                },
            )
        )

    try:
        db.add_all(records)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "document_id": str(document_id),
        "document_name": display_name,
        "pages_extracted": len({chunk.metadata["page_number"] for chunk in chunks}),
        "chunks_created": len(records),
    }
