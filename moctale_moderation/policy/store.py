"""Vector-based policy store using ChromaDB."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

# Fix Transformers Keras 3 incompatibility with tf-keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import chromadb
from chromadb.utils import embedding_functions

from .rules import PolicyRule, PolicyRuleLoader

log = logging.getLogger(__name__)

# Fallback path if None
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".chroma_db"

class PolicyStore:
    """Manages the vector database for policy rules."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(db_path) if db_path else str(_DEFAULT_DB_PATH)
        
        # Use sentence-transformers with ONNX runtime for 3x speedup and lower memory
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            backend="onnx",
            model_kwargs={"file_name": "onnx/model_O3.onnx"}
        )
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="policy_rules",
            embedding_function=self.emb_fn
        )

    def clear(self) -> None:
        """Clear the policy rule collection."""
        try:
            self.client.delete_collection("policy_rules")
        except ValueError:
            pass
        self.collection = self.client.create_collection(
            name="policy_rules",
            embedding_function=self.emb_fn
        )

    def build_from_yaml(self, path: Path | str) -> None:
        """Load rules from YAML and build the vector index."""
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
            
            # ChromaDB metadata cannot contain lists, so we JSON serialize examples
            meta = rule.to_dict()
            meta["examples"] = json.dumps(meta["examples"])
            metadatas.append(meta)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        log.info("Indexed %d policy rules in ChromaDB.", len(rules))

    def retrieve(self, text: str, k: int = 5, max_distance: float = 1.2) -> list[PolicyRule]:
        """Retrieve the top-K most relevant policy rules for a given text."""
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                return []
        except Exception:
            # Refresh collection if stale (e.g. after index rebuild)
            self.collection = self.client.get_or_create_collection(
                name="policy_rules",
                embedding_function=self.emb_fn
            )
            if self.collection.count() == 0:
                return []

        results = self.collection.query(
            query_texts=[text],
            n_results=min(k, self.collection.count()),
            include=["metadatas", "distances"]
        )
        
        rules = []
        if not results["metadatas"] or not results["metadatas"][0]:
            return rules
            
        distances = results.get("distances", [[0.0] * len(results["metadatas"][0])])[0]
            
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
                examples=examples
            ))
            
        return rules

# Process-wide singleton
_STORE_INSTANCE: PolicyStore | None = None

def get_policy_store() -> PolicyStore:
    global _STORE_INSTANCE
    if _STORE_INSTANCE is None:
        _STORE_INSTANCE = PolicyStore()
    return _STORE_INSTANCE
