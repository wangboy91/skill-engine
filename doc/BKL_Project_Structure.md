# BKL Project Structure

本文是当前代码目录导览，用来解释每个目录、文件、主要类的职责，以及哪些模块已经实现、哪些模块只是为后续版本预留边界。

## 1. 为什么有些 Python 文件代码很少

当前项目是 v0.1 的纵向闭环实现，优先把这条主链路跑通：

```text
配置加载
  -> 注册 Tool / Skill
  -> 运行 Skill
  -> 调模型
  -> 调 Tool
  -> 校验输出
  -> 记录 Run / Trace / Artifact
  -> CLI / API / SDK 共用同一个 SkillEngine
```

所以代码量集中在：

```text
bkl_engine/engine.py
bkl_engine/cli/main.py
bkl_engine/api/main.py
bkl_engine/core/schemas.py
bkl_engine/core/config.py
bkl_engine/skills/loader.py
bkl_engine/skills/runtime.py
bkl_engine/tools/loader.py
bkl_engine/tools/python_tool.py
bkl_engine/tools/api_tool.py
bkl_engine/models/router.py
bkl_engine/models/providers/*
bkl_engine/storage/catalog_store.py
```

有些文件只有 1-2 行，是刻意保留的模块边界，后续会拆出去：

```text
api/routes_tools.py
api/routes_skills.py
api/routes_runs.py
cli/tool_commands.py
cli/skill_commands.py
cli/run_commands.py
tools/llm_tool.py
tools/skill_tool.py
policy/policy_engine.py
storage/database.py
storage/models.py
trace/events.py
```

这些不是核心逻辑缺失，而是 P0 还没有展开的后续扩展点。

## 2. 顶层目录

```text
bkl_engine/
  Core Engine 源码

examples/
  示例 Tool、Skill、输入文件

tests/
  pytest 测试

doc/
  技术规格、开发清单、架构说明、运行请求说明

bkl.yaml
  本地模型配置，真实项目中可以由 bkl init 生成

.env
  本地密钥，不提交 git
```

## 3. bkl_engine 核心目录

```text
bkl_engine/
  __init__.py
  engine.py
  core/
  cli/
  api/
  models/
  skills/
  tools/
  storage/
  trace/
  policy/
```

### 3.1 `engine.py`

主门面类：`SkillEngine`。

职责：

```text
加载模型配置
创建 Skill Registry
创建 Tool Registry
创建 Model Router
创建 Tool Executor
创建 Trace Store
创建 Artifact Store
创建 Run Store
创建 Catalog Store
对外提供 register_tool / register_skill / run_skill
```

关键类：

```python
class SkillEngine
```

关键方法：

```text
SkillEngine.load(...)
  从 bkl.yaml 和可选 catalog_path 创建 Engine。

SkillEngine.create_for_testing(...)
  创建 mock engine，用于测试和默认 CLI 示例。

register_tool(path)
  加载 Tool 包，注册到 Tool Registry，可选写入 catalog。

register_skill(path)
  加载 Skill 包，注册到 Skill Registry，可选写入 catalog。

run_skill(skill_id, input_data)
  调用 SkillRuntime 执行。

load_catalog()
  从 .bkl/catalog.json 恢复已注册 Tool / Skill。
```

### 3.2 `core/`

共享基础类型和配置。

```text
core/schemas.py
  所有核心 Pydantic 数据结构。

core/config.py
  bkl.yaml + .env 配置加载。

core/errors.py
  结构化错误基类。
```

主要类：

```text
Tool
Skill
SkillLimits
SkillModelConfig
ToolExecutionContext
ToolExecutionResult
RunResult
RunContext
TraceEvent
Artifact
EngineError
UsageSummary
ModelProfileConfig
EngineConfig
BklEngineError
```

### 3.3 `skills/`

Skill 包加载、注册、运行。

```text
skills/loader.py
  读取标准 Skill 包：SKILL.md + skill.config.json + schema。

skills/registry.py
  内存 Skill Registry。

skills/runtime.py
  Skill 执行主循环。

skills/prompt.py
  Prompt 渲染扩展点，目前占位。
```

主要类：

```text
SkillLoadError
InMemorySkillRegistry
SkillRuntime
SkillRuntimeError
```

`SkillRuntime` 当前执行流程：

```text
读取 skill_id
校验 input_schema
读取 allowed_tools
构造 system/user messages
调用模型
如果模型请求 Tool，执行 Tool
把 Tool 结果回填给模型
模型返回 final_output
校验 output_schema
保存 RunResult / Trace
```

### 3.4 `tools/`

Tool 包加载和执行。

```text
tools/loader.py
  读取 tool.yaml + input_schema + output_schema。

tools/registry.py
  内存 Tool Registry。

tools/executor.py
  按 Tool 类型分发执行器。

tools/python_tool.py
  执行 Python Tool，使用 JSON stdin/stdout。

tools/api_tool.py
  执行 API Tool。

tools/openapi_importer.py
  从 OpenAPI operation 生成 API Tool。

tools/llm_tool.py
  LLM Tool 扩展点，目前占位。

tools/skill_tool.py
  Skill-as-Tool 扩展点，目前占位。
```

主要类：

```text
ToolLoadError
InMemoryToolRegistry
ToolExecutor
PythonToolRunner
ToolExecutionError
ApiToolRunner
ApiToolExecutionError
```

### 3.5 `models/`

模型路由和 provider。

```text
models/router.py
  ModelRouter、MockModelProvider、ModelResponse、ToolCallRequest。

models/providers/openai_compatible.py
  OpenAI-compatible chat/completions 协议。

models/providers/anthropic.py
  Anthropic-compatible messages 协议。

models/providers/openrouter.py
  OpenRouter 扩展点，目前占位。

models/providers/volcengine.py
  Volcengine 扩展点，目前占位。
```

主要类：

```text
ModelRouter
MockModelProvider
ModelResponse
ToolCallRequest
ModelUsage
OpenAICompatibleProvider
AnthropicProvider
```

当前模型选择逻辑：

```text
bkl.yaml 里 models.active_profile
  -> ModelRouter 选择对应 provider
  -> Skill 的 model.profile 可覆盖默认 profile
```

### 3.6 `storage/`

本地存储。

```text
storage/artifact_store.py
  本地 Artifact 存储。

storage/catalog_store.py
  .bkl/catalog.json 持久化 Tool / Skill 注册表。

storage/repositories.py
  内存 Run Store。

storage/database.py
  数据库扩展点，目前占位。

storage/models.py
  数据库模型扩展点，目前占位。
```

主要类：

```text
LocalArtifactStore
JsonCatalogStore
CatalogDocument
CatalogEntry
InMemoryRunStore
```

### 3.7 `trace/`

Trace 事件记录。

```text
trace/trace_store.py
  内存 trace store。

trace/events.py
  事件类型扩展点，目前占位。
```

主要类：

```text
InMemoryTraceStore
```

### 3.8 `api/`

FastAPI 服务。

```text
api/main.py
  当前所有 API route 都在这里。

api/routes_tools.py
api/routes_skills.py
api/routes_runs.py
  后续拆分 route 的占位文件。
```

主要类：

```text
RegisterPathRequest
RunSkillRequest
```

主要函数：

```text
create_app(engine=None)
```

当前 API：

```text
GET  /health
POST /tools/register
GET  /tools
GET  /tools/{tool_id}
POST /skills/register
GET  /skills
GET  /skills/{skill_id}
POST /skills/{skill_id}/runs
GET  /runs
GET  /runs/{run_id}
GET  /runs/{run_id}/trace
GET  /runs/{run_id}/artifacts
GET  /artifacts/{artifact_id}
```

### 3.9 `cli/`

Typer CLI。

```text
cli/main.py
  当前所有 CLI 命令都在这里。

cli/tool_commands.py
cli/skill_commands.py
cli/run_commands.py
  后续拆分命令的占位文件。
```

当前 CLI：

```text
bkl --version
bkl init
bkl serve
bkl tool register
bkl tool list
bkl tool test
bkl skill register
bkl skill list
bkl skill run
bkl run list
bkl trace show
```

为什么 `main.py` 比较大：

```text
P0 先把所有命令集中在一个文件，便于快速验证。
后续稳定后再把 tool/skill/run/trace 命令拆到对应文件。
```

### 3.10 `policy/`

策略和安全控制扩展点。

```text
policy/policy_engine.py
  后续用于 workspace 权限、网络权限、Tool 调用策略、敏感操作确认。
```

当前仍是占位。

## 4. examples 目录

```text
examples/
  inputs/
  skills/
  tools/
```

### 4.1 inputs

```text
examples/inputs/talking_video_input.json
examples/inputs/wangbudong_experiment_input.json
examples/inputs/subtitle_input.json
```

用于 CLI/API 测试。

### 4.2 skills

```text
examples/skills/talking_video/
  SKILL.md
  skill.config.json
  input.schema.json
  output.schema.json
  examples.json

examples/skills/wangbudong_experiment/
  SKILL.md
  skill.config.json
  input.schema.json
  output.schema.json
  examples.json
```

### 4.3 tools

```text
examples/tools/subtitle_generate_srt/
  tool.yaml
  input.schema.json
  output.schema.json
  main.py

examples/tools/wangbudong_write_prompt_pack/
  tool.yaml
  input.schema.json
  output.schema.json
  main.py
```

## 5. tests 目录

测试按功能拆分：

```text
test_tool_loader.py
  Tool 包加载。

test_python_tool_runner.py
  Python Tool 执行、schema 校验、超时、artifact 目录。

test_skill_loader.py
  Skill 包加载。

test_skill_runtime.py
  Skill Runtime 主循环。

test_model_config.py
  bkl.yaml + .env 模型配置。

test_model_providers.py
  OpenAI-compatible / Anthropic-compatible provider 请求和解析。

test_openapi_importer.py
  OpenAPI operation -> Tool。

test_registries.py
  Tool / Skill Registry。

test_stores.py
  Artifact Store / Trace Store。

test_catalog_store.py
  .bkl/catalog.json 持久化。

test_api_cli.py
  CLI/API 端到端基础链路。

test_cli.py
  CLI init / serve / catalog register。
```

## 6. 当前已实现和占位总结

已实现：

```text
Core schema
config loader
Tool loader
Python Tool runner
API Tool runner
OpenAPI importer skeleton
Tool registry
Skill loader
Skill registry
Skill runtime
Model router
Mock provider
OpenAI-compatible provider
Anthropic provider
Run store
Trace store
Artifact store
Catalog store
CLI
FastAPI
talking_video example
wangbudong_experiment example
```

占位或待展开：

```text
CLI 命令拆分文件
API route 拆分文件
LLM Tool
Skill-as-Tool
Policy Engine
Database persistence
SQLAlchemy models
Trace event type definitions
OpenRouter provider
Volcengine provider
bkl chat
Skill Router
Scene Mapping
Desktop GUI
Server auth / Docker / queue
```

## 7. 推荐后续拆分

下一步如果继续整理代码结构，建议按这个顺序拆：

```text
1. cli/main.py 拆成 cli/tool_commands.py、cli/skill_commands.py、cli/run_commands.py、cli/server_commands.py。
2. api/main.py 拆成 api/routes_tools.py、api/routes_skills.py、api/routes_runs.py、api/routes_chat.py。
3. storage/repositories.py 拆成 run_store.py、trace_store.py 或数据库实现。
4. policy/policy_engine.py 开始承接 Tool 权限、网络权限、文件写权限。
5. skills/prompt.py 承接 Skill prompt 渲染、schema 摘要、tool 摘要。
```

当前不急着拆，因为主链路还在快速迭代阶段。等 `bkl chat` 和 `Skill Router` 开始实现时，拆分会更自然。
