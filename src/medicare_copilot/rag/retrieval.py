from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.medicare_copilot.backend.models import RAGChunk
from src.medicare_copilot.rag.embeddings import embed_query


def sparse_search(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """PostgreSQL lexical search using ts_rank_cd."""
    query_ts = func.plainto_tsquery("english", query)

    statement = (
        select(
            RAGChunk,
            func.ts_rank_cd(
                RAGChunk.search_vector,
                query_ts,
            ).label("score"),
        )
        .where(RAGChunk.search_vector.op("@@")(query_ts))
        .order_by(
            func.ts_rank_cd(
                RAGChunk.search_vector,
                query_ts,
            ).desc()
        )
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        {
            "id": str(chunk.id),
            "content": chunk.content,
            "document_id": str(chunk.document_id),
            "document_name": chunk.document_name,
            "start_page": chunk.start_page,
            "end_page": chunk.end_page,
            "score": float(score),
            "retrieval_type": "sparse",
        }
        for chunk, score in rows
    ]


def dense_search(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Dense vector similarity search using cosine distance."""
    query_vector = embed_query(query)

    distance = RAGChunk.embedding.cosine_distance(query_vector)

    statement = (
        select(RAGChunk, distance.label("distance"))
        .order_by(distance.asc())
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        {
            "id": str(chunk.id),
            "content": chunk.content,
            "document_id": str(chunk.document_id),
            "document_name": chunk.document_name,
            "start_page": chunk.start_page,
            "end_page": chunk.end_page,
            "score": float(1 - distance_value),
            "retrieval_type": "dense",
        }
        for chunk, distance_value in rows
    ]


def hybrid_search(
    db: Session,
    query: str,
    limit: int = 5,
    candidate_limit: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    Combine sparse and dense retrieval using reciprocal rank fusion.
    """
    sparse_results = sparse_search(
        db,
        query,
        limit=candidate_limit,
    )
    dense_results = dense_search(
        db,
        query,
        limit=candidate_limit,
    )

    combined = {}

    for results in (sparse_results, dense_results):
        for rank, result in enumerate(results, start=1):
            chunk_id = result["id"]

            if chunk_id not in combined:
                combined[chunk_id] = {
                    **result,
                    "rrf_score": 0.0,
                    "retrieval_types": [],
                }

            combined[chunk_id]["rrf_score"] += 1.0 / (rrf_k + rank)

            combined[chunk_id]["retrieval_types"].append(result["retrieval_type"])

    ranked_results = sorted(
        combined.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return ranked_results[:limit]
