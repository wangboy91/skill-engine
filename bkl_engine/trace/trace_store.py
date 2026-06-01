"""Trace store primitives."""

from uuid import uuid4

from bkl_engine.core.schemas import TraceEvent


class InMemoryTraceStore:
    def __init__(self) -> None:
        self._events: dict[str, list[TraceEvent]] = {}

    def record(
        self,
        run_id: str,
        event_type: str,
        message: str,
        data: dict[str, object],
    ) -> TraceEvent:
        event = TraceEvent(
            id=f"trace_{uuid4().hex}",
            run_id=run_id,
            type=event_type,
            message=message,
            data=self._redact(data),
        )
        self._events.setdefault(run_id, []).append(event)
        return event

    def list_events(self, run_id: str) -> list[TraceEvent]:
        return list(self._events.get(run_id, []))

    def _redact(self, data: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        sensitive_parts = ("authorization", "api_key", "password", "secret", "token", "credential")
        for key, value in data.items():
            if any(part in key.lower() for part in sensitive_parts):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact(value)
            else:
                redacted[key] = value
        return redacted
