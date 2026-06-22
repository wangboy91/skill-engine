import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BKL_ENGINE_ROOT = PROJECT_ROOT / "bkl_engine"
APPLICATION_ROOT = PROJECT_ROOT / "bkl_engine" / "application"


def test_bkl_engine_top_level_uses_ddd_layout_only() -> None:
    allowed_directories = {"application", "domain", "infrastructure", "interfaces"}
    actual_directories = {
        path.name
        for path in BKL_ENGINE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }

    assert actual_directories == allowed_directories


def test_application_layer_has_no_infrastructure_or_facade_imports() -> None:
    banned_prefixes = (
        "bkl_engine.engine",
        "bkl_engine.infrastructure",
        "bkl_engine.models",
        "bkl_engine.storage",
        "bkl_engine.trace",
    )

    violations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        imported_modules = _imported_modules(path)
        for module in imported_modules:
            if module.startswith(banned_prefixes):
                relative = path.relative_to(PROJECT_ROOT)
                violations.append(f"{relative}: {module}")

    assert violations == []


def test_domain_models_have_canonical_modules() -> None:
    from bkl_engine.domain.execution import RunResult
    from bkl_engine.domain.skill import Skill
    from bkl_engine.domain.tool import Tool

    assert Skill.__module__ == "bkl_engine.domain.skill.schemas"
    assert Tool.__module__ == "bkl_engine.domain.tool.schemas"
    assert RunResult.__module__ == "bkl_engine.domain.execution.schemas"


def test_in_memory_adapters_live_in_infrastructure_layer() -> None:
    from bkl_engine.infrastructure.persistence.artifact_store import LocalArtifactStore
    from bkl_engine.infrastructure.persistence.catalog_store import JsonCatalogStore
    from bkl_engine.infrastructure.persistence.run_store import InMemoryRunStore
    from bkl_engine.infrastructure.repositories.skill_registry import InMemorySkillRegistry
    from bkl_engine.infrastructure.repositories.tool_registry import InMemoryToolRegistry
    from bkl_engine.infrastructure.tracing.trace_store import InMemoryTraceStore

    assert InMemorySkillRegistry.__module__ == (
        "bkl_engine.infrastructure.repositories.skill_registry"
    )
    assert InMemoryToolRegistry.__module__ == (
        "bkl_engine.infrastructure.repositories.tool_registry"
    )
    assert LocalArtifactStore.__module__ == "bkl_engine.infrastructure.persistence.artifact_store"
    assert JsonCatalogStore.__module__ == "bkl_engine.infrastructure.persistence.catalog_store"
    assert InMemoryRunStore.__module__ == "bkl_engine.infrastructure.persistence.run_store"
    assert InMemoryTraceStore.__module__ == "bkl_engine.infrastructure.tracing.trace_store"


def test_interface_adapters_have_canonical_modules() -> None:
    from bkl_engine.interfaces.cli import main as cli_module
    from bkl_engine.interfaces.http.main import create_app

    assert create_app.__module__ == "bkl_engine.interfaces.http.main"
    assert cli_module.__name__ == "bkl_engine.interfaces.cli.main"


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules
