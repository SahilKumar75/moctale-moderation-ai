"""Audit logging for moderation decisions."""
from __future__ import annotations

import hashlib
import json
import logging
import logging.handlers
import time
from pathlib import Path
from typing import Any

from .schemas import ModerationResult

log = logging.getLogger(__name__)

_AUDIT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
_AUDIT_BACKUP_COUNT = 5


class _PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        return record.getMessage()


class AuditLogger:
    """GDPR-safe audit logger for moderation decisions.

    Writes structured JSONL. Rotates at 10 MB, keeping 5 backups.
    Stores irreversible SHA-256 hashes instead of raw text (GDPR compliance).
    """

    def __init__(self, log_dir: str | Path = "logs", filename: str = "audit.jsonl") -> None:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        filepath = log_dir_path / filename

        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=_AUDIT_MAX_BYTES,
            backupCount=_AUDIT_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(_PlainFormatter())

        self._audit_log = logging.getLogger(f"moctale.audit.{id(self)}")
        self._audit_log.propagate = False
        self._audit_log.setLevel(logging.INFO)
        self._audit_log.addHandler(handler)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def log_decision(
        self,
        text: str,
        context_type: str,
        result: ModerationResult,
        latency_ms: float,
        request_id: str | None = None,
    ) -> None:
        if result.predicted_action == "allow":
            return

        entry: dict[str, Any] = {
            "timestamp": time.time(),
            "request_id": request_id,
            "text_hash": self._hash_text(text),
            "context_type": context_type,
            "action": result.predicted_action,
            "category": result.predicted_category,
            "severity": result.predicted_severity,
            "reason_codes": list(result.reason_codes),
            "triggered_rules": result.triggered_rules,
            "latency_ms": round(latency_ms, 2),
        }

        try:
            self._audit_log.info(json.dumps(entry))
        except Exception as e:
            log.error("Failed to write audit log", extra={"error": str(e), "entry": entry})
