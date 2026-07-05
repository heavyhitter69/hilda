"""
memory/semantic_memory.py — ChromaDB-backed semantic memory for Hilda.

Three collections:
  - conversations: past conversation turns searchable by meaning
  - user_facts: extracted facts about the user (preferences, personal info)
  - knowledge: things Hilda has been told or learned

All embeddings use Ollama's local embedding model — no cloud needed.
"""
from __future__ import annotations


import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_client = None
_collections: dict[str, Any] = {}


def _get_client():
    """Lazy-init ChromaDB persistent client."""
    global _client
    if _client is None:
        try:
            import chromadb
            db_path = str(settings.WRITABLE_ROOT / "memory" / "chroma_db")
            Path(db_path).mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(path=db_path)
            log.info("ChromaDB initialized at %s", db_path)
        except ImportError:
            log.warning("chromadb not installed — semantic memory disabled.")
            return None
        except Exception as e:
            log.error("ChromaDB init failed: %s", e)
            return None
    return _client


def _get_collection(name: str):
    """Get or create a ChromaDB collection."""
    if name in _collections:
        return _collections[name]
    client = _get_client()
    if client is None:
        return None
    try:
        coll = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        _collections[name] = coll
        return coll
    except Exception as e:
        log.error("Failed to get collection '%s': %s", name, e)
        return None


def _generate_embedding(text: str) -> Optional[list[float]]:
    """Generate embedding using Ollama's embedding endpoint."""
    try:
        import ollama
        response = ollama.embed(
            model="nomic-embed-text",
            input=text,
        )
        # Response format: {"embeddings": [[...]]}
        embeddings = response.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
    except Exception:
        pass

    # Fallback: try with the main model
    try:
        import ollama
        response = ollama.embed(
            model=settings.OLLAMA_MODEL,
            input=text,
        )
        embeddings = response.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
    except Exception as e:
        log.debug("Embedding generation failed: %s", e)
    return None


class SemanticMemory:
    """High-level interface for Hilda's semantic memory system."""

    def remember(
        self,
        text: str,
        category: str = "conversations",
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Store a piece of information with its semantic embedding.

        Parameters
        ----------
        text : str — the text to remember
        category : str — collection name (conversations, user_facts, knowledge)
        metadata : dict — optional metadata (timestamp, source, etc.)
        """
        coll = _get_collection(category)
        if coll is None:
            return False

        try:
            embedding = _generate_embedding(text)
            doc_id = f"{category}_{int(time.time() * 1000)}_{hash(text) % 10000}"
            meta = {
                "timestamp": datetime.now().isoformat(),
                "category": category,
            }
            if metadata:
                meta.update({k: str(v) for k, v in metadata.items()})

            kwargs: dict[str, Any] = {
                "ids": [doc_id],
                "documents": [text],
                "metadatas": [meta],
            }
            if embedding:
                kwargs["embeddings"] = [embedding]

            coll.add(**kwargs)
            log.debug("Remembered in '%s': %s", category, text[:60])
            return True
        except Exception as e:
            log.error("remember() failed: %s", e)
            return False

    def recall(
        self,
        query: str,
        category: str = "conversations",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Semantically search memory for relevant entries.

        Returns list of dicts with 'text', 'distance', and 'metadata'.
        """
        coll = _get_collection(category)
        if coll is None:
            return []

        try:
            embedding = _generate_embedding(query)
            kwargs: dict[str, Any] = {"n_results": min(top_k, 20)}

            if embedding:
                kwargs["query_embeddings"] = [embedding]
            else:
                kwargs["query_texts"] = [query]

            results = coll.query(**kwargs)

            items = []
            if results and results.get("documents"):
                docs = results["documents"][0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]

                for i, doc in enumerate(docs):
                    items.append({
                        "text": doc,
                        "distance": distances[i] if i < len(distances) else 1.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                    })

            return items
        except Exception as e:
            log.error("recall() failed: %s", e)
            return []

    def recall_all_categories(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search across all memory categories and merge results."""
        all_results = []
        for cat in ("conversations", "user_facts", "knowledge"):
            results = self.recall(query, category=cat, top_k=top_k)
            for r in results:
                r["category"] = cat
            all_results.extend(results)

        # Sort by distance (lower = more relevant)
        all_results.sort(key=lambda x: x.get("distance", 1.0))
        return all_results[:top_k * 2]

    def store_fact(self, fact: str, source: str = "conversation") -> bool:
        """Store a user fact (convenience wrapper)."""
        return self.remember(
            fact,
            category="user_facts",
            metadata={"source": source},
        )

    def store_knowledge(self, knowledge: str, source: str = "user") -> bool:
        """Store a piece of knowledge (convenience wrapper)."""
        return self.remember(
            knowledge,
            category="knowledge",
            metadata={"source": source},
        )

    def get_user_facts(self, top_k: int = 15) -> list[str]:
        """Return all known user facts (for system prompt injection)."""
        coll = _get_collection("user_facts")
        if coll is None:
            return []
        try:
            results = coll.get(limit=top_k)
            if results and results.get("documents"):
                return results["documents"]
        except Exception as e:
            log.error("get_user_facts failed: %s", e)
        return []

    def get_relevant_context(self, query: str, top_k: int = 5) -> dict[str, list[str]]:
        """
        Get relevant context for a query from all memory sources.
        Returns dict with keys: 'memories', 'facts', 'knowledge'.
        """
        result: dict[str, list[str]] = {"memories": [], "facts": [], "knowledge": []}

        for cat, key in [("conversations", "memories"), ("user_facts", "facts"), ("knowledge", "knowledge")]:
            items = self.recall(query, category=cat, top_k=top_k)
            result[key] = [
                item["text"] for item in items
                if item.get("distance", 1.0) < 0.7  # Only include relevant results
            ]

        return result

    def count(self, category: str = "conversations") -> int:
        """Return the number of items in a collection."""
        coll = _get_collection(category)
        if coll is None:
            return 0
        try:
            return coll.count()
        except Exception:
            return 0


# Singleton instance
_instance: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    global _instance
    if _instance is None:
        _instance = SemanticMemory()
    return _instance
