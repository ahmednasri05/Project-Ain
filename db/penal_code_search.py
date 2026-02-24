"""
Semantic search over the penal_code_embeddings table in Supabase.

The vector search is handled by the `match_penal_code` Postgres function
(defined in migrations/10_create_penal_code_embeddings.sql) and called via
supabase.rpc() so that pgvector's <=> operator is available server-side.

Public API
----------
search_penal_code(query, limit, threshold, chapter_filter, book_filter)
    Semantic vector search — returns articles ranked by cosine similarity.

get_article_by_number(article_number, chapter_title)
    Direct lookup by article number, with an optional chapter filter.

find_similar_articles(article_id, limit)
    Find articles whose embeddings are closest to a given article.
"""

import sys
from pathlib import Path
from typing import Optional

# Project-Ain/ is the package root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.client import get_supabase_client  # noqa: E402
from ai.embedding import embed_texts        # noqa: E402

TABLE = "penal_code_embeddings"


# ── Core helpers ──────────────────────────────────────────────────────────────

def _embed_query(query: str) -> list[float]:
    """Embed a single Arabic query string."""
    return embed_texts([query])[0]


def _vector_to_pg(embedding: list[float]) -> str:
    """
    Serialise a Python list of floats to the pgvector text literal expected
    by PostgREST when passed as an RPC parameter, e.g. '[0.1,0.2,...]'.
    """
    return "[" + ",".join(map(str, embedding)) + "]"


# ── Public functions ──────────────────────────────────────────────────────────

def search_penal_code(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.3,
    chapter_filter: Optional[str] = None,
    book_filter: Optional[str] = None,
) -> list[dict]:
    """
    Semantic vector search over the penal code.

    Embeds `query` with text-embedding-3-large, then calls the
    `match_penal_code` Postgres RPC function which uses the HNSW index for
    fast cosine-similarity retrieval.

    Args:
        query:               Arabic natural-language query.
        limit:               Maximum number of articles to return.
        similarity_threshold: Minimum cosine similarity (0–1).  Lower values
                             return more (but less relevant) results.
        chapter_filter:      If given, only return articles from this chapter.
        book_filter:         If given, only return articles from this book.

    Returns:
        List of dicts with keys:
            id, article_number, book_title, book_description,
            chapter_title, article_text, similarity (0–1).
    """
    embedding = _embed_query(query)

    results = (
        get_supabase_client()
        .rpc(
            "match_penal_code",
            {
                "query_embedding": _vector_to_pg(embedding),
                "match_threshold": similarity_threshold,
                "match_count": limit,
            },
        )
        .execute()
        .data
    )

    # Optional client-side filters (cheaper than extra RPC parameters)
    if chapter_filter:
        results = [r for r in results if chapter_filter in r["chapter_title"]]
    if book_filter:
        results = [r for r in results if book_filter in r["book_title"]]

    return results


def get_article_by_number(
    article_number: str,
    chapter_title: Optional[str] = None,
) -> list[dict]:
    """
    Direct lookup by article number.

    Because many articles share the same `article_number` (e.g. several
    variants of article 86), this returns a list.  Pass `chapter_title` to
    narrow the results to a specific chapter.

    Args:
        article_number: e.g. "86"
        chapter_title:  Optional substring match on the chapter title.

    Returns:
        List of matching article dicts (without a similarity score).
    """
    supabase = get_supabase_client()
    q = (
        supabase.table(TABLE)
        .select(
            "id, article_number, book_title, book_description, "
            "chapter_title, article_text"
        )
        .eq("article_number", article_number)
    )
    if chapter_title:
        q = q.ilike("chapter_title", f"%{chapter_title}%")

    return q.execute().data

