"""
Scheme Knowledge Base Ingester

Downloads, chunks, embeds, and stores government schemes in PostgreSQL + pgvector.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import asyncpg
from sentence_transformers import SentenceTransformer


@dataclass
class Scheme:
    name: str
    state: str
    category: str
    description: str
    eligibility: dict[str, Any]
    benefits: dict[str, Any]
    documents_required: list[str]
    application_process: str
    contact_info: dict[str, str]
    source_url: str
    last_updated: str


class SchemeIngester:
    """
    Ingests government schemes into PostgreSQL with pgvector embeddings.

    Chunking strategy:
    - Each scheme → multiple chunks (overview, eligibility, benefits, docs, process)
    - Chunk size ~500 tokens for optimal retrieval
    - Metadata includes all structured fields for filtering
    """

    def __init__(
        self,
        database_url: str = None,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        table_name: str = "scheme_chunks",
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.table_name = table_name
        self.embedding_model = SentenceTransformer(embedding_model)
        self._pool: asyncpg.Pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
            await self._ensure_schema()
        return self._pool

    async def _ensure_schema(self):
        """Create table and vector index if not exists."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding VECTOR(768),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Create HNSW index for fast similarity search
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                ON {self.table_name} USING hnsw (embedding vector_cosine_ops)
            """)

            # Create metadata indexes for filtering
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_state_idx
                ON {self.table_name} ((metadata->>'state'))
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_category_idx
                ON {self.table_name} ((metadata->>'category'))
            """)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _generate_chunk_id(self, scheme_name: str, chunk_type: str, index: int) -> str:
        """Generate deterministic chunk ID."""
        raw = f"{scheme_name}:{chunk_type}:{index}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _chunk_scheme(self, scheme: Scheme) -> list[dict]:
        """Split scheme into semantic chunks for embedding."""
        chunks = []

        # 1. Overview chunk
        chunks.append(
            {
                "type": "overview",
                "text": f"Scheme: {scheme.name}\nState: {scheme.state}\nCategory: {scheme.category}\nDescription: {scheme.description}",
                "metadata": {
                    "scheme_name": scheme.name,
                    "state": scheme.state,
                    "category": scheme.category,
                    "chunk_type": "overview",
                    "source_url": scheme.source_url,
                    "last_updated": scheme.last_updated,
                },
            }
        )

        # 2. Eligibility chunk
        if scheme.eligibility:
            elig_text = "Eligibility:\n" + "\n".join(
                f"- {k}: {v}" for k, v in scheme.eligibility.items()
            )
            chunks.append(
                {
                    "type": "eligibility",
                    "text": elig_text,
                    "metadata": {
                        "scheme_name": scheme.name,
                        "state": scheme.state,
                        "category": scheme.category,
                        "chunk_type": "eligibility",
                    },
                }
            )

        # 3. Benefits chunk
        if scheme.benefits:
            bene_text = "Benefits:\n" + "\n".join(f"- {k}: {v}" for k, v in scheme.benefits.items())
            chunks.append(
                {
                    "type": "benefits",
                    "text": bene_text,
                    "metadata": {
                        "scheme_name": scheme.name,
                        "state": scheme.state,
                        "category": scheme.category,
                        "chunk_type": "benefits",
                    },
                }
            )

        # 4. Documents chunk
        if scheme.documents_required:
            docs_text = "Documents Required:\n" + "\n".join(
                f"- {d}" for d in scheme.documents_required
            )
            chunks.append(
                {
                    "type": "documents",
                    "text": docs_text,
                    "metadata": {
                        "scheme_name": scheme.name,
                        "state": scheme.state,
                        "category": scheme.category,
                        "chunk_type": "documents",
                    },
                }
            )

        # 5. Application process chunk
        if scheme.application_process:
            chunks.append(
                {
                    "type": "application",
                    "text": f"Application Process: {scheme.application_process}",
                    "metadata": {
                        "scheme_name": scheme.name,
                        "state": scheme.state,
                        "category": scheme.category,
                        "chunk_type": "application",
                    },
                }
            )

        return chunks

    async def ingest_scheme(self, scheme: Scheme) -> int:
        """
        Ingest a single scheme: chunk, embed, store.

        Returns number of chunks inserted.
        """
        pool = await self._get_pool()
        chunks = self._chunk_scheme(scheme)
        inserted = 0

        async with pool.acquire() as conn, conn.transaction():
            for i, chunk in enumerate(chunks):
                chunk_id = self._generate_chunk_id(scheme.name, chunk["type"], i)
                embedding = self.embedding_model.encode(chunk["text"]).tolist()
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                await conn.execute(
                    f"""
                        INSERT INTO {self.table_name} (id, text, metadata, embedding)
                        VALUES ($1, $2, $3, $4::vector)
                        ON CONFLICT (id) DO UPDATE SET
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                        """,
                    chunk_id,
                    chunk["text"],
                    json.dumps(chunk["metadata"]),
                    embedding_str,
                )
                inserted += 1

        return inserted

    async def ingest_batch(self, schemes: list[Scheme]) -> dict[str, int]:
        """Ingest multiple schemes, return counts per scheme."""
        results = {}
        for scheme in schemes:
            try:
                count = await self.ingest_scheme(scheme)
                results[scheme.name] = count
            except Exception as e:
                results[scheme.name] = f"ERROR: {e}"
        return results

    async def clear_all(self):
        """Delete all schemes (use with caution)."""
        pool = await self._get_pool()
        await pool.execute(f"TRUNCATE {self.table_name}")

    async def count_schemes(self) -> int:
        """Count unique schemes in KB."""
        pool = await self._get_pool()
        return await pool.fetchval(
            f"SELECT COUNT(DISTINCT metadata->>'scheme_name') FROM {self.table_name}"
        )
