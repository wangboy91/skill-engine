# BKL Skill Engine

BKL Skill Engine is a reusable Python runtime for loading Skills, executing Tools, and returning structured results, artifacts, and traces.

## What Works Now

- Load local Tool packages from `tool.yaml`
- Execute Python Tools through JSON stdin/stdout
- Load standard Skill packages from `SKILL.md` frontmatter and Markdown body
- Run a synchronous Skill Runtime loop with mock tool-calling model behavior
- Record in-memory runs and traces
- Save local artifacts
- Use the same `SkillEngine` facade from SDK, CLI, and FastAPI
- Import simple OpenAPI operations as API Tools

## Skill Format

Skills use the standard `SKILL.md` shape: YAML frontmatter followed by Markdown instructions.
The required industry-standard fields are `name` and `description`; BKL runtime metadata lives
under the `bkl:` extension key.

```md
---
name: talking-video
description: Use when generating a structured talking-video draft.
bkl:
  id: talking_video
  version: 0.1.0
  input_schema: input.schema.json
  output_schema: output.schema.json
  model:
    profile: mock
  tools:
    allow:
      - subtitle_generate_srt
---

# AI 口播视频生成

Follow the workflow and return JSON matching `output.schema.json`.
```

Only `SKILL.md` Skill packages are supported.

## Development

Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run the baseline checks:

```bash
python3 -m pytest
ruff check .
mypy bkl_engine
```

Run the CLI:

```bash
bkl --version
```

## Model Configuration

Model providers are configured in `bkl.yaml`. The engine supports multiple profiles and uses
`models.active_profile` to choose the active one.

Copy the example config and set environment variables outside git:

```bash
cp bkl.example.yaml bkl.yaml
export ANTHROPIC_AUTH_TOKEN=...
export ANTHROPIC_MODEL=astron-code-latest
export ANTHROPIC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic
export OPENAI_COMPATIBLE_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
```

Supported protocols:

- `openai-compatible`: calls `{base_url}/chat/completions`
- `anthropic`: calls `{base_url}/v1/messages`

Only secret environment variable names are stored in config, not secret values.

## CLI Examples

Execute the example Python Tool:

```bash
uv --cache-dir .uv-cache run --extra dev bkl tool test \
  examples/tools/subtitle_generate_srt \
  examples/inputs/subtitle_input.json \
  --output json
```

Run the example Skill with the default mock model provider:

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  talking_video \
  examples/inputs/talking_video_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --output json
```

## Python SDK Example

```python
import asyncio

from bkl_engine.engine import SkillEngine


async def main() -> None:
    engine = SkillEngine.create_for_testing()
    await engine.register_tool("examples/tools/subtitle_generate_srt")
    await engine.register_skill("examples/skills/talking_video")
    result = await engine.run_skill(
        "talking_video",
        {
            "topic": "适合程序员的护眼台灯",
            "platform": "xiaohongshu",
            "duration_seconds": 60,
        },
    )
    print(result.model_dump(mode="json"))


asyncio.run(main())
```

## API Example

Start FastAPI with:

```bash
uv --cache-dir .uv-cache run --extra dev uvicorn bkl_engine.api.main:app --reload
```

Then register and run:

```bash
curl -X POST http://127.0.0.1:8000/tools/register \
  -H 'Content-Type: application/json' \
  -d '{"path":"examples/tools/subtitle_generate_srt"}'

curl -X POST http://127.0.0.1:8000/skills/register \
  -H 'Content-Type: application/json' \
  -d '{"path":"examples/skills/talking_video"}'

curl -X POST http://127.0.0.1:8000/skills/talking_video/runs \
  -H 'Content-Type: application/json' \
  -d '{"input":{"topic":"适合程序员的护眼台灯","platform":"xiaohongshu","duration_seconds":60},"mode":"sync"}'
```
