# BKL Skill Engine

Language: [中文](#中文) | [English](#english)

---

## 中文

BKL Skill Engine 是一个可复用的 Python Skill 运行时，用于加载标准 `SKILL.md`、执行 Tools，并返回结构化结果、Artifacts 和 Trace。

### 当前能力

- 加载本地 Tool 包：`tool.yaml`
- 通过 JSON stdin/stdout 执行 Python Tool
- 加载标准 Skill 包：`SKILL.md` frontmatter + Markdown instructions + `skill.config.json`
- 支持同步 Skill Runtime 和 tool-calling loop
- 支持 Mock、OpenAI-compatible、Anthropic-compatible 模型协议
- 支持 `bkl.yaml + .env` 多模型 profile 配置，并通过 `models.active_profile` 启用其中一个
- 记录 in-memory Run 和 Trace
- 保存本地 Artifact
- SDK、CLI、FastAPI 共用同一个 `SkillEngine` facade
- 支持从简单 OpenAPI operation 导入 API Tool

### 安装形态

BKL 只维护一个 Core Engine，按使用场景提供不同入口：

- **CLI / SDK**：适合开发者、本地脚本、CI 和服务器批处理
- **Server / HTTP**：通过 `bkl serve` 部署 FastAPI 服务，供其他系统调用
- **Desktop / Local GUI**：后续本地界面启动本机 `bkl serve`，通过 HTTP API 管理模型、Tool、Skill 和运行记录

Skill、Tool、模型配置在所有形态下保持同一套规范。

详细架构决策见 [BKL Core Engine Installation Forms](doc/BKL_Core_Engine_Installation_Forms.md)。

Skill 运行请求和路由选择见 [BKL Skill Run Request and Routing](doc/BKL_Skill_Run_Request_and_Routing.md)。

Agent 工程化设计见 [BKL Agent Runtime Engineering Plan](doc/BKL_Agent_Runtime_Engineering.md)。

代码目录结构和文件职责见 [BKL Project Structure](doc/BKL_Project_Structure.md)。

### Skill 格式

Skill 包只支持一套规范：标准 `SKILL.md` + BKL `skill.config.json`。

`SKILL.md` 遵循行业常见 Skill 形态：YAML frontmatter 只保留标准元数据 `name` 和 `description`，后面是 Markdown instructions。BKL 引擎自己的运行时配置不写进 `SKILL.md`，统一放在同目录的 `skill.config.json`。

```text
talking_video/
  SKILL.md
  skill.config.json
  input.schema.json
  output.schema.json
  examples.json
```

```md
---
name: talking-video
description: Use when generating a structured talking-video draft.
---

# AI 口播视频生成

Follow the workflow and return JSON matching `output.schema.json`.
```

```json
{
  "id": "talking_video",
  "version": "0.1.0",
  "input_schema": "input.schema.json",
  "output_schema": "output.schema.json",
  "model": {
    "profile": "mock"
  },
  "tools": {
    "allow": [
      "subtitle_generate_srt"
    ]
  }
}
```

### 开发环境

安装开发依赖：

```bash
python3 -m pip install -e ".[dev]"
```

运行基础检查：

```bash
python3 -m pytest
ruff check .
mypy bkl_engine
```

查看 CLI 版本：

```bash
bkl --version
```

### 模型配置

模型配置位于 `bkl.yaml`。可以同时配置多个 profile，并通过 `models.active_profile` 选择当前启用的模型。

可以用启动向导生成配置：

```bash
uv --cache-dir .uv-cache run --extra dev bkl init \
  --protocol openai-compatible \
  --profile xfyun_openai \
  --base-url https://maas-coding-api.cn-huabei-1.xf-yun.com/v2 \
  --model astron-code-latest \
  --api-key "你的密钥"
```

也可以复制示例配置：

```bash
cp bkl.example.yaml bkl.yaml
```

在 `.env` 中配置密钥和模型，不要把真实密钥提交到 git：

```bash
OPENAI_COMPATIBLE_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
OPENAI_AUTH_TOKEN=...
OPENAI_MODEL=astron-code-latest

ANTHROPIC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic
ANTHROPIC_AUTH_TOKEN=...
ANTHROPIC_MODEL=astron-code-latest
```

支持的协议：

- `openai-compatible`：调用 `{base_url}/chat/completions`
- `anthropic`：调用 `{base_url}/v1/messages`

配置文件只保存环境变量名称，不保存密钥值。

### Catalog 持久化

`bkl tool register` 和 `bkl skill register` 默认会写入 `.bkl/catalog.json`。`bkl serve` 启动时会读取这个 catalog，因此服务重启后仍能看到已导入的 Tool 和 Skill。

```bash
uv --cache-dir .uv-cache run --extra dev bkl tool register \
  examples/tools/subtitle_generate_srt

uv --cache-dir .uv-cache run --extra dev bkl skill register \
  examples/skills/talking_video
```

可以通过 `--catalog` 指定其他 catalog 文件，便于测试或多工作区隔离。

### CLI 示例

启动 HTTP 服务：

```bash
uv --cache-dir .uv-cache run --extra dev bkl serve \
  --host 127.0.0.1 \
  --port 8000 \
  --config bkl.yaml
```

执行示例 Python Tool：

```bash
uv --cache-dir .uv-cache run --extra dev bkl tool test \
  examples/tools/subtitle_generate_srt \
  examples/inputs/subtitle_input.json \
  --output json
```

使用 Mock 模型运行示例 Skill：

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  talking_video \
  examples/inputs/talking_video_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --output json
```

运行「王不懂的小实验」示例 Skill：

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  wangbudong_experiment \
  examples/inputs/wangbudong_experiment_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --output json
```

该 Skill 会调用 `wangbudong_write_prompt_pack`，在本次 run 的 artifact 目录里写入 `00-实验拆解.md`、`01-首图提示词.md`、`02-分步骤提示词.md`、`03-小红书文案.md`。

使用 `bkl.yaml + .env` 中的真实模型配置运行示例 Skill：

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  talking_video \
  examples/inputs/talking_video_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --config bkl.yaml \
  --output json
```

判断 Skill 是否真正触发 Tool，看返回里的 `trace_summary`：

```json
{
  "llm_called": 2,
  "tool_called": 1,
  "tool_succeeded": 1,
  "tool_failed": 0
}
```

### Python SDK 示例

```python
import asyncio

from bkl_engine.engine import SkillEngine


async def main() -> None:
    engine = SkillEngine.load("bkl.yaml")
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

### API 示例

启动 FastAPI：

```bash
uv --cache-dir .uv-cache run --extra dev bkl serve --config bkl.yaml
```

注册 Tool 和 Skill，然后运行：

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

---

## English

BKL Skill Engine is a reusable Python runtime for loading standard `SKILL.md` packages, executing Tools, and returning structured results, Artifacts, and Trace data.

### Current Capabilities

- Load local Tool packages from `tool.yaml`
- Execute Python Tools through JSON stdin/stdout
- Load standard Skill packages from `SKILL.md` frontmatter + Markdown instructions + `skill.config.json`
- Run a synchronous Skill Runtime with a tool-calling loop
- Support Mock, OpenAI-compatible, and Anthropic-compatible model protocols
- Support multiple model profiles through `bkl.yaml + .env`, with `models.active_profile` selecting the active one
- Record in-memory Runs and Traces
- Save local Artifacts
- Share the same `SkillEngine` facade across SDK, CLI, and FastAPI
- Import simple OpenAPI operations as API Tools

### Installation Forms

BKL keeps one Core Engine and exposes different entrypoints for different deployment targets:

- **CLI / SDK**: local scripts, CI, developer workflows, and server batch jobs
- **Server / HTTP**: deploy FastAPI through `bkl serve` for other systems to call
- **Desktop / Local GUI**: a future local UI can start `bkl serve` locally and manage models, Tools, Skills, and runs through HTTP

Skill, Tool, and model configuration formats stay the same across all forms.

See [BKL Core Engine Installation Forms](doc/BKL_Core_Engine_Installation_Forms.md) for the detailed architecture decision.

See [BKL Skill Run Request and Routing](doc/BKL_Skill_Run_Request_and_Routing.md) for run request and routing details.

See [BKL Agent Runtime Engineering Plan](doc/BKL_Agent_Runtime_Engineering.md) for the Agent orchestration design.

See [BKL Project Structure](doc/BKL_Project_Structure.md) for source layout and file responsibilities.

### Skill Format

Only one Skill package format is supported: standard `SKILL.md` + BKL `skill.config.json`.

`SKILL.md` follows the common Skill shape: YAML frontmatter contains only the standard `name` and `description` metadata, followed by Markdown instructions. BKL runtime configuration does not live inside `SKILL.md`; it belongs in the sibling `skill.config.json` file.

```text
talking_video/
  SKILL.md
  skill.config.json
  input.schema.json
  output.schema.json
  examples.json
```

```md
---
name: talking-video
description: Use when generating a structured talking-video draft.
---

# AI Talking Video Generation

Follow the workflow and return JSON matching `output.schema.json`.
```

```json
{
  "id": "talking_video",
  "version": "0.1.0",
  "input_schema": "input.schema.json",
  "output_schema": "output.schema.json",
  "model": {
    "profile": "mock"
  },
  "tools": {
    "allow": [
      "subtitle_generate_srt"
    ]
  }
}
```

### Development

Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run baseline checks:

```bash
python3 -m pytest
ruff check .
mypy bkl_engine
```

Check the CLI version:

```bash
bkl --version
```

### Model Configuration

Model providers are configured in `bkl.yaml`. You can define multiple profiles and choose the active one with `models.active_profile`.

Generate configuration with the init command:

```bash
uv --cache-dir .uv-cache run --extra dev bkl init \
  --protocol openai-compatible \
  --profile xfyun_openai \
  --base-url https://maas-coding-api.cn-huabei-1.xf-yun.com/v2 \
  --model astron-code-latest \
  --api-key "your-api-key"
```

You can also copy the example config:

```bash
cp bkl.example.yaml bkl.yaml
```

Set credentials and model names in `.env`. Do not commit real secrets:

```bash
OPENAI_COMPATIBLE_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
OPENAI_AUTH_TOKEN=...
OPENAI_MODEL=astron-code-latest

ANTHROPIC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic
ANTHROPIC_AUTH_TOKEN=...
ANTHROPIC_MODEL=astron-code-latest
```

Supported protocols:

- `openai-compatible`: calls `{base_url}/chat/completions`
- `anthropic`: calls `{base_url}/v1/messages`

Config files store environment variable names only, not secret values.

### Catalog Persistence

`bkl tool register` and `bkl skill register` write to `.bkl/catalog.json` by default. `bkl serve` loads that catalog on startup, so imported Tools and Skills remain available after restart.

```bash
uv --cache-dir .uv-cache run --extra dev bkl tool register \
  examples/tools/subtitle_generate_srt

uv --cache-dir .uv-cache run --extra dev bkl skill register \
  examples/skills/talking_video
```

Use `--catalog` to select another catalog file for tests or separate workspaces.

### CLI Examples

Start the HTTP service:

```bash
uv --cache-dir .uv-cache run --extra dev bkl serve \
  --host 127.0.0.1 \
  --port 8000 \
  --config bkl.yaml
```

Execute the example Python Tool:

```bash
uv --cache-dir .uv-cache run --extra dev bkl tool test \
  examples/tools/subtitle_generate_srt \
  examples/inputs/subtitle_input.json \
  --output json
```

Run the example Skill with the mock model:

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  talking_video \
  examples/inputs/talking_video_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --output json
```

Run the Wangbudong experiment example Skill:

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  wangbudong_experiment \
  examples/inputs/wangbudong_experiment_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --output json
```

This Skill calls `wangbudong_write_prompt_pack` and writes `00-实验拆解.md`, `01-首图提示词.md`, `02-分步骤提示词.md`, and `03-小红书文案.md` into the run artifact directory.

Run the example Skill with the real model profile from `bkl.yaml + .env`:

```bash
uv --cache-dir .uv-cache run --extra dev bkl skill run \
  talking_video \
  examples/inputs/talking_video_input.json \
  --skills-dir examples/skills \
  --tools-dir examples/tools \
  --config bkl.yaml \
  --output json
```

To confirm that the Skill triggered a Tool, check `trace_summary`:

```json
{
  "llm_called": 2,
  "tool_called": 1,
  "tool_succeeded": 1,
  "tool_failed": 0
}
```

### Python SDK Example

```python
import asyncio

from bkl_engine.engine import SkillEngine


async def main() -> None:
    engine = SkillEngine.load("bkl.yaml")
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

### API Example

Start FastAPI:

```bash
uv --cache-dir .uv-cache run --extra dev bkl serve --config bkl.yaml
```

Register a Tool and Skill, then run:

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
