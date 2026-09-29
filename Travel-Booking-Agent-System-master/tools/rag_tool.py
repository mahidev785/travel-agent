"""Lightweight RAG retrieval over the destination-guide corpus.

Uses TF-IDF instead of an embedding API so the retrieval step needs zero
network calls and zero extra API keys -- good for a demo/resume project.
Swapping this for Chroma + Gemini embeddings for real semantic search is a
drop-in replacement: keep the same `retrieve(destination, query, k)`
signature and nothing else in the graph needs to change.
"""

from __future__ import annotations

import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_GUIDE_DIR = Path(__file__).resolve().parent.parent / "data" / "destination_guides"


def _load_chunks() -> list[dict]:
    """Split every guide file into bullet-point chunks with a city tag."""
    chunks = []
    for path in sorted(_GUIDE_DIR.glob("*.md")):
        city = path.stem.replace("_", " ")
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.startswith("- "):
                chunks.append({"city": city, "text": line[2:]})
    return chunks


_CHUNKS = _load_chunks()
_VECTORIZER = TfidfVectorizer(stop_words="english")
_MATRIX = _VECTORIZER.fit_transform([c["text"] for c in _CHUNKS]) if _CHUNKS else None


def retrieve(destination: str, query: str = "", k: int = 4) -> list[str]:
    """Return up to k relevant guide snippets for a destination.

    Filters to the matching city first (cheap, exact), then ranks by
    TF-IDF similarity to the traveler's stated preferences so the most
    relevant bullet points come first.
    """
    if not _CHUNKS:
        return []

    dest_norm = re.sub(r"[^a-z ]", "", destination.lower())
    city_chunks = [c for c in _CHUNKS if c["city"] in dest_norm or dest_norm in c["city"]]
    if not city_chunks:
        return []

    if not query:
        return [c["text"] for c in city_chunks[:k]]

    idxs = [_CHUNKS.index(c) for c in city_chunks]
    query_vec = _VECTORIZER.transform([query])
    sims = cosine_similarity(query_vec, _MATRIX[idxs]).flatten()
    ranked = [c for _, c in sorted(zip(sims, city_chunks), key=lambda p: -p[0])]
    return [c["text"] for c in ranked[:k]]
