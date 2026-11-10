"""
Scheme Knowledge Base Retriever

Embeds user queries and retrieves relevant scheme chunks from PostgreSQL + pgvector.
"""

import os
from dataclasses import dataclass
from typing import Any

try:
    import asyncpg
    from sentence_transformers import SentenceTransformer

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

from scheme_kb.smart_retriever import SmartSchemeRetriever


@dataclass
class SchemeChunk:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float


class SchemeRetriever:
    """
    Retrieves relevant government schemes using semantic search.
    Uses pgvector when available; otherwise falls back to smart hybrid search.
    """

    def __init__(
        self,
        database_url: str = None,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        table_name: str = "scheme_chunks",
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.table_name = table_name
        self.smart_retriever = SmartSchemeRetriever()
        self._use_pg = bool(
            HAS_PGVECTOR and self.database_url and "localhost" not in self.database_url
        )
        self._pool = None
        if self._use_pg:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
            except Exception:
                self._use_pg = False

    async def _get_pool(self):
        if self._pool is None and self._use_pg:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        return self._pool

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def retrieve(
        self, query: str, k: int = 5, state_filter: str = None, category_filter: str = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve top-K relevant scheme chunks for a query.
        """
        if not self._use_pg:
            return await self.smart_retriever.retrieve(
                query, k=k, state_filter=state_filter, category_filter=category_filter
            )

        try:
            pool = await self._get_pool()
            query_embedding = self.embedding_model.encode(query).tolist()
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            filters = []
            params = [embedding_str, k]
            param_idx = 3

            if state_filter:
                filters.append(f"metadata->>'state' = ${param_idx}")
                params.append(state_filter)
                param_idx += 1

            if category_filter:
                filters.append(f"metadata->>'category' = ${param_idx}")
                params.append(category_filter)
                param_idx += 1

            where_clause = "WHERE " + " AND ".join(filters) if filters else ""

            sql = f"""
                SELECT id, text, metadata,
                       1 - (embedding <=> $1::vector) as score
                FROM {self.table_name}
                {where_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """

            rows = await pool.fetch(sql, *params)
            return [
                {
                    "id": row["id"],
                    "text": row["text"],
                    "metadata": row["metadata"],
                    "score": float(row["score"]),
                }
                for row in rows
            ]
        except Exception:
            return await self.smart_retriever.retrieve(
                query, k=k, state_filter=state_filter, category_filter=category_filter
            )

    async def get_scheme_by_id(self, scheme_id: str) -> SchemeChunk | None:
        """Get full scheme details by ID."""
        pool = await self._get_pool()
        row = await pool.fetchrow(
            f"SELECT id, text, metadata FROM {self.table_name} WHERE id = $1", scheme_id
        )
        if row:
            return SchemeChunk(id=row["id"], text=row["text"], metadata=row["metadata"], score=1.0)
        return None

    async def search_by_keywords(self, keywords: list[str], k: int = 10) -> list[SchemeChunk]:
        """Fallback keyword search if embeddings fail."""
        pool = await self._get_pool()
        conditions = " OR ".join([f"text ILIKE '%{kw}%'" for kw in keywords])
        sql = f"""
            SELECT id, text, metadata, 0.5 as score
            FROM {self.table_name}
            WHERE {conditions}
            LIMIT $1
        """
        rows = await pool.fetch(sql, k)
        return [
            SchemeChunk(
                id=row["id"], text=row["text"], metadata=row["metadata"], score=float(row["score"])
            )
            for row in rows
        ]
