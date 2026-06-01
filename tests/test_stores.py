from pathlib import Path

from bkl_engine.storage.artifact_store import LocalArtifactStore
from bkl_engine.trace.trace_store import InMemoryTraceStore


def test_artifact_store_saves_and_lists_text_artifacts(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)

    artifact = store.save_text(
        run_id="run_1",
        content="hello",
        artifact_type="text",
        filename="hello.txt",
        tool_call_id="call_1",
    )

    assert artifact.id
    assert store.read_text(artifact.id) == "hello"
    assert store.list_by_run("run_1") == [artifact]


def test_trace_store_records_run_events() -> None:
    store = InMemoryTraceStore()

    event = store.record("run_1", "skill_started", "Skill started", {"skill_id": "demo"})

    assert event.id
    assert store.list_events("run_1")[0].type == "skill_started"
    assert store.list_events("run_1")[0].data["skill_id"] == "demo"
