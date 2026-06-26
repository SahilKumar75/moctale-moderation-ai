"""Vector-based policy store using ChromaDB."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from .rules import PolicyRule, PolicyRuleLoader

log = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".chroma_db"

# Fix Transformers Keras 3 incompatibility — set before any chromadb/tf import
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")


def _try_import_chromadb():
    """Lazy import chromadb so a missing/broken install doesn't crash the module."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        return chromadb, embedding_functions
    except Exception as exc:
        log.warning(
            "chromadb unavailable (%s). RAG policy store will return empty results. "
            "Install with: pip install 'moctale-moderation[ml]'",
            exc,
        )
        return None, None


class PolicyStore:
    """Manages the vector database for policy rules. Degrades gracefully if chromadb unavailable."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(db_path) if db_path else str(_DEFAULT_DB_PATH)
        self._available = False

        chromadb, embedding_functions = _try_import_chromadb()
        if chromadb is None:
            self.client = None
            self.collection = None
            self.emb_fn = None
            return

        try:
            self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                backend="onnx",
                model_kwargs={"file_name": "onnx/model_O3.onnx"},
            )
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name="policy_rules",
                embedding_function=self.emb_fn,
            )
            self._available = True
        except Exception as exc:
            log.warning("PolicyStore init failed (%s). RAG disabled.", exc)
            self.client = None
            self.collection = None
            self.emb_fn = None

    def clear(self) -> None:
        if not self._available:
            return
        try:
            self.client.delete_collection("policy_rules")
        except ValueError:
            pass
        self.collection = self.client.create_collection(
            name="policy_rules",
            embedding_function=self.emb_fn,
        )

    def build_from_yaml(self, path: Path | str) -> None:
        """Load rules from YAML and build the vector index."""
        if not self._available:
            log.warning("PolicyStore unavailable — skipping index build.")
            return

        rules = PolicyRuleLoader.from_yaml(path)
        if not rules:
            log.warning("No rules loaded, skipping index build.")
            return

        self.clear()

        ids = []
        documents = []
        metadatas = []

        for rule in rules:
            ids.append(rule.id)
            documents.append(rule.embedding_text)
            meta = rule.to_dict()
            # ChromaDB metadata cannot contain lists — JSON-serialize examples
            meta["examples"] = json.dumps(meta["examples"])
            metadatas.append(meta)

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        log.info("Indexed %d policy rules in ChromaDB.", len(rules))

    def retrieve(self, text: str, k: int = 5, max_distance: float = 1.2) -> list[PolicyRule]:
        """Retrieve top-K most relevant policy rules. Returns [] if store unavailable."""
        if not self._available or self.collection is None:
            return []

        try:
            count = self.collection.count()
        except Exception:
            try:
                self.collection = self.client.get_or_create_collection(
                    name="policy_rules",
                    embedding_function=self.emb_fn,
                )
                count = self.collection.count()
            except Exception as exc:
                log.warning("PolicyStore collection refresh failed: %s", exc)
                return []

        if count == 0:
            return []

        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=min(k, count),
                include=["metadatas", "distances"],
            )
        except Exception as exc:
            log.warning("PolicyStore query failed: %s", exc)
            return []

        if not results["metadatas"] or not results["metadatas"][0]:
            return []

        distances = results.get("distances", [[0.0] * len(results["metadatas"][0])])[0]
        rules: list[PolicyRule] = []

        for meta, dist in zip(results["metadatas"][0], distances):
            if dist > max_distance:
                continue
            try:
                examples = json.loads(str(meta.get("examples", "[]")))
            except json.JSONDecodeError:
                examples = []

            rules.append(PolicyRule(
                id=str(meta.get("id")),
                description=str(meta.get("description")),
                action=str(meta.get("action")),
                category=str(meta.get("category")),
                severity=str(meta.get("severity")),
                examples=examples,
            ))

        return rules


# Process-wide singleton with double-checked locking
_STORE_INSTANCE: PolicyStore | None = None
_STORE_LOCK = threading.Lock()


def get_policy_store() -> PolicyStore:
    global _STORE_INSTANCE
    if _STORE_INSTANCE is None:
        with _STORE_LOCK:
            if _STORE_INSTANCE is None:
                _STORE_INSTANCE = PolicyStore()
    return _STORE_INSTANCE
