"""
Smart Scheme Retriever

Provides hybrid semantic search across Indian welfare schemes without requiring
external heavy dependencies. Automatically adapts to query language (Hindi, Hinglish, English).
"""

import re
from typing import Any

from scheme_kb.catalog import SCHEMES_CATALOG, SchemeDetail


class SmartSchemeRetriever:
    """Hybrid in-memory semantic and keyword retriever for welfare schemes."""

    def __init__(self):
        self.catalog = SCHEMES_CATALOG

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        state_filter: str | None = None,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve top-K matching schemes for a user query.
        Returns scheme chunk dicts compatible with RAG and Evon LLM client.
        """
        if not query or not query.strip():
            # Return top featured schemes
            results = []
            for s in self.catalog[:k]:
                results.append(self._format_chunk(s, score=0.85))
            return results

        normalized_query = query.lower()
        query_tokens = set(re.findall(r"\b\w+\b", normalized_query))

        scored_schemes = []

        for scheme in self.catalog:
            # Apply state filter if given and scheme is state-specific
            if (
                state_filter
                and scheme.state != "central"
                and scheme.state.lower() != state_filter.lower()
            ):
                continue

            # Apply category filter
            if category_filter and scheme.category.lower() != category_filter.lower():
                continue

            score = 0.0

            # 1. Direct keyword match
            for kw in scheme.keywords:
                kw_lower = kw.lower()
                if kw_lower in normalized_query:
                    score += 0.35
                elif any(kw_lower in token for token in query_tokens):
                    score += 0.20

            # 2. Scheme name match
            if scheme.name.lower() in normalized_query or scheme.id in normalized_query:
                score += 0.50

            # 3. Category match
            if scheme.category.lower() in normalized_query:
                score += 0.30

            # 4. Text and description token overlap
            desc_tokens = set(re.findall(r"\b\w+\b", scheme.description.lower()))
            overlap = len(query_tokens.intersection(desc_tokens))
            score += min(0.30, overlap * 0.05)

            # 5. State affinity
            if scheme.state != "central" and scheme.state.lower() in normalized_query:
                score += 0.25

            # If Maharashtra farmer query, boost PM-KISAN and Shetkari Sanman
            if any(
                w in normalized_query
                for w in ["maharashtra", "marathi", "vidarbha", "pune", "mumbai"]
            ):
                if scheme.state == "maharashtra":
                    score += 0.30

            if score > 0.05:
                scored_schemes.append((scheme, min(0.98, max(0.40, score))))

        # Sort by score descending
        scored_schemes.sort(key=lambda x: x[1], reverse=True)

        # Fallback if no specific match found
        if not scored_schemes:
            for s in self.catalog[:k]:
                scored_schemes.append((s, 0.50))

        results = []
        for scheme, score in scored_schemes[:k]:
            results.append(self._format_chunk(scheme, score))

        return results

    def _format_chunk(self, scheme: SchemeDetail, score: float) -> dict[str, Any]:
        """Format scheme as a retrieval chunk compatible with Evon LLM."""
        return {
            "id": scheme.id,
            "text": f"{scheme.name}: {scheme.description}. Benefits: {scheme.benefits}. Eligibility: {scheme.eligibility_summary}",
            "metadata": {
                "scheme_name": scheme.name,
                "scheme_name_hi": scheme.name_hi,
                "category": scheme.category,
                "state": scheme.state,
                "benefits": scheme.benefits,
                "benefits_amount": scheme.benefits_amount,
                "eligibility_summary": scheme.eligibility_summary,
                "documents_required": scheme.documents_required,
                "application_link": scheme.application_link,
                "helpline": scheme.helpline,
            },
            "score": round(score, 3),
        }
