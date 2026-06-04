"""Persistent Tool and Skill catalog store."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from bkl_engine.core.errors import BklEngineError
from bkl_engine.core.schemas import Skill, Tool


class CatalogEntry(BaseModel):
    id: str
    path: str
    enabled: bool = True
    last_validated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CatalogDocument(BaseModel):
    version: int = 1
    tools: dict[str, CatalogEntry] = Field(default_factory=dict)
    skills: dict[str, CatalogEntry] = Field(default_factory=dict)


class JsonCatalogStore:
    """JSON-backed catalog for registered local Tool and Skill packages."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> CatalogDocument:
        if not self.path.exists():
            return CatalogDocument()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return CatalogDocument.model_validate(raw)
        except json.JSONDecodeError as exc:
            raise BklEngineError("CATALOG_INVALID", f"Invalid catalog JSON: {self.path}") from exc
        except ValidationError as exc:
            raise BklEngineError("CATALOG_INVALID", f"Invalid catalog shape: {self.path}") from exc

    def save(self, catalog: CatalogDocument) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(catalog.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def upsert_tool(self, tool: Tool) -> None:
        catalog = self.load()
        catalog.tools[tool.id] = CatalogEntry(
            id=tool.id,
            path=_package_path(tool.package_path, "Tool", tool.id),
            enabled=tool.enabled,
        )
        self.save(catalog)

    def upsert_skill(self, skill: Skill) -> None:
        catalog = self.load()
        catalog.skills[skill.id] = CatalogEntry(
            id=skill.id,
            path=_package_path(skill.package_path, "Skill", skill.id),
            enabled=skill.enabled,
        )
        self.save(catalog)

    def list_tools(self) -> list[CatalogEntry]:
        return list(self.load().tools.values())

    def list_skills(self) -> list[CatalogEntry]:
        return list(self.load().skills.values())


def _package_path(path: Path | None, kind: str, package_id: str) -> str:
    if path is None:
        raise BklEngineError("CATALOG_INVALID", f"{kind} package path missing: {package_id}")
    return path.as_posix()
