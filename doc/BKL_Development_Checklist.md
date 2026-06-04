# BKL Skill Engine Development Checklist

Status: active development checklist for v0.1.

This checklist turns the technical spec and installation-form decision into implementation order. The rule is to keep one Core Engine and make CLI, API, SDK, and future Desktop reuse it.

## 1. P0 Completed Baseline

- [x] Python package skeleton with `pyproject.toml`
- [x] shared Pydantic schemas and structured errors
- [x] Tool loader for `tool.yaml`
- [x] Python Tool runner with JSON stdin/stdout
- [x] Tool registry
- [x] standard Skill loader: `SKILL.md + skill.config.json`
- [x] Skill registry
- [x] Skill runtime tool-calling loop
- [x] Mock model provider
- [x] OpenAI-compatible model provider
- [x] Anthropic-compatible model provider
- [x] model profiles from `bkl.yaml + .env`
- [x] in-memory run store
- [x] in-memory trace store
- [x] local artifact store
- [x] CLI basics: version, tool test, skill run
- [x] FastAPI basics: register Tool, register Skill, run Skill, query run/trace/artifact
- [x] OpenAPI Tool importer skeleton
- [x] `bkl init`
- [x] `bkl serve`
- [x] installation-form architecture document
- [x] example Skill: `examples/skills/talking_video`
- [x] example Skill: `examples/skills/wangbudong_experiment`
- [x] example Tool: `examples/tools/wangbudong_write_prompt_pack`

## 2. Current Iteration: Persistent Catalog

Goal: make Tool and Skill imports survive CLI/API/server restarts.

- [x] add `.bkl/catalog.json` schema
- [x] add `JsonCatalogStore`
- [x] persist registered Tools with id, package path, enabled flag, and validation timestamp
- [x] persist registered Skills with id, package path, enabled flag, and validation timestamp
- [x] load catalog entries during `SkillEngine.load`
- [x] make CLI `tool register` and `skill register` write catalog entries
- [x] make CLI/API list registered catalog entries after restart
- [x] keep tests isolated with explicit temporary catalog paths
- [x] document catalog behavior in README and installation-form doc

Acceptance:

- [x] registering a Tool writes `.bkl/catalog.json`
- [x] registering a Skill writes `.bkl/catalog.json`
- [x] a fresh `SkillEngine.load(..., catalog_path=...)` loads registered packages
- [x] CLI register commands can write to a specified catalog path
- [x] full test suite, ruff, and mypy pass

## 3. Next Iteration: Natural Language Management

Goal: allow users to manage the engine through natural language without duplicating runtime logic.

- [ ] add Skill Router: natural language request -> candidate `skill_id`
- [ ] add confidence threshold and user confirmation for ambiguous routing
- [ ] add Scene Mapping: `scene_id -> skill_id`
- [ ] expose input schema for schema-driven forms
- [ ] document how frontend derives form fields from `input.schema.json`
- [ ] add `bkl chat`
- [ ] add safe management actions: configure model, import Tool, import Skill, validate, run, list catalog
- [ ] use deterministic code paths for writes
- [ ] require confirmation before file writes or destructive changes
- [ ] persist chat session trace
- [ ] expose equivalent `/chat/messages` API

Acceptance:

- [ ] user can ask to import a Tool by path
- [ ] user can ask to import a Skill by path
- [ ] user can ask to run a registered Skill with natural language input
- [ ] chat actions are recorded in trace
- [ ] unsafe writes require confirmation

## 4. Server Deployment Iteration

Goal: make `bkl serve` usable by other services beyond local testing.

- [ ] API key auth middleware
- [ ] configurable workspace root
- [ ] request id and structured access logs
- [ ] Dockerfile
- [ ] health and readiness endpoints
- [ ] persistent run/trace/artifact storage adapter
- [ ] queue/worker skeleton for async runs

Acceptance:

- [ ] service can start from Docker
- [ ] authenticated API clients can register and run Skills
- [ ] unauthenticated requests are rejected when auth is enabled
- [ ] run and trace survive process restart

## 5. Desktop / Local GUI Iteration

Goal: make a local user interface without creating a second engine.

- [ ] choose shell: Tauri, Electron, or browser-only local UI
- [ ] local server lifecycle manager
- [ ] model profile screen
- [ ] Tool catalog screen
- [ ] Skill catalog screen
- [ ] run console
- [ ] trace viewer
- [ ] artifact viewer

Acceptance:

- [ ] GUI starts or connects to local `bkl serve`
- [ ] GUI manages model config through the same API
- [ ] GUI registers Tools and Skills through the same API
- [ ] GUI runs Skills and displays trace/artifacts

## 6. Built-in Skill Packs

Goal: ship useful starter packs without hardcoding product-specific behavior into the engine.

- [ ] `core/model-config-assistant`
- [ ] `core/tool-import-assistant`
- [ ] `core/skill-creator`
- [ ] `core/skill-validator`
- [ ] `core/skill-runner`
- [x] `media/talking-video` example
- [x] `media/wangbudong-experiment` example
- [ ] `data/openapi-tool-builder`

Acceptance:

- [ ] built-in packs use the same `SKILL.md + skill.config.json` format
- [ ] users can disable or remove built-in packs
- [ ] built-in packs are documented as examples, not engine internals

## 7. Quality Gates

Every implementation iteration must pass:

```bash
uv --cache-dir .uv-cache run --extra dev pytest
uv --cache-dir .uv-cache run --extra dev ruff check .
uv --cache-dir .uv-cache run --extra dev mypy bkl_engine
```

For model/API features, tests must use mock providers by default. Real provider tests are smoke tests only and must not print secrets.
