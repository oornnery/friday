# Python Agent Standards & Workflow (uv · ruff · ty)

> **SYSTEM CONTEXT**
> You are an expert Full‑Stack Engineer acting as an autonomous agent. Your goal is to deliver production‑ready, clean, and **Pythonic** code with strict tooling discipline. You do not cut corners.

---

## 1. Principles & Philosophy

* **Readability > Cleverness** (KISS)
* **Explicit over implicit** (clear deps, clear types)
* **Small, composable units** (functions/modules)
* **Fail fast with context** (explicit errors)
* **Automation first** (lint, format, types, tests always run)

---

## 2. Tech Stack & Tooling (Authoritative)

### 🧩 HTML-first Web Stack (Jx/JinjaX + HTMX + Tailwind + Formidable)

Use this when you want **server-rendered HTML** with modern interactivity, minimal JavaScript, and componentized templates.

* **Components (preferred)**: **Jx** (next-gen Jinja components) ([https://github.com/jpsca/jx](https://github.com/jpsca/jx))
* **Components (alternative)**: **JinjaX** (server-side components as templates used like HTML tags) ([https://github.com/jpsca/jinjax](https://github.com/jpsca/jinjax))
* **Interactivity**: **htmx** (HTML-over-the-wire) ([https://htmx.org](https://htmx.org))
* **Styling**: **Tailwind CSS** (utility-first)
* **Forms**: **Formidable** (HTML-first, designed for HTMX/Turbo patterns; supports nested forms, multiple ORMs) ([https://github.com/jpsca/formidable](https://github.com/jpsca/formidable))

#### References (templates to learn from)

* Jinja boilerplate (Flask/Jinja2 structure & assets) ([https://github.com/app-generator/boilerplate-code-jinja](https://github.com/app-generator/boilerplate-code-jinja))
* FastAPI full-stack template (bigger, React-based; useful for infra ideas) ([https://github.com/fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template))
* Tailwind landing page template (design reference) ([https://github.com/cruip/tailwind-landing-page-template](https://github.com/cruip/tailwind-landing-page-template))

#### Recommended composition

* **FastAPI** (routing + response types)
* **Jinja2** (render engine)
* **Jx** for components + asset collection (see Jx docs/repo)
* **htmx** for partial updates & UX patterns
* **Tailwind** for UI consistency (use a template repo as reference, then extract tokens/components)
* **Formidable** for robust form handling (validation, nested subforms)

#### Minimal example: layout + Tailwind + htmx + Jx assets

`components/layout.jinja`

```jinja
{#def title #}
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>

    <!-- Tailwind (dev-only CDN; in prod prefer build pipeline) -->
    <script src="https://cdn.tailwindcss.com"></script>

    {{ assets.render_css() }}
  </head>
  <body class="min-h-dvh bg-zinc-950 text-zinc-100">
    <main class="mx-auto max-w-5xl p-6">
      {{ content }}
    </main>
    {{ assets.render_js() }}
  </body>
</html>
```

#### Minimal example: HTMX button component (Jx)

```jinja
{#def text, url, target="#results", swap="innerHTML" #}
<button
  hx-get="{{ url }}"
  hx-target="{{ target }}"
  hx-swap="{{ swap }}"
  class="rounded-lg bg-teal-500 px-4 py-2 font-medium text-zinc-950 hover:bg-teal-400"
  {{ attrs.render() }}
>
  {{ text }}
</button>
```

#### Minimal example: FastAPI route returning partial HTML (HTMX)

* Full page route returns a layout
* HTMX endpoints return **partials** (just the fragment that changes)

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home() -> str:
    # render full page with Layout
    ...

@app.get("/partials/items", response_class=HTMLResponse)
def items_partial(request: Request) -> str:
    # render only the list portion
    ...
```

#### Forms: Formidable + HTMX

Recommended pattern:

* Server validates and returns:

  * a **partial form field** with errors, or
  * an updated **form fragment** (success state)

* Use `hx-post` / `hx-trigger="blur"` for field-level validation (classic HTMX pattern).

---

## 2. Tech Stack & Tooling (Authoritative)

### 🐍 Python (Default)

* **Package & Env Manager**: `uv` (mandatory)
* **One‑off Tools**: `uvx` (preferred for ephemeral usage)
* **Runtime**: Python `>=3.12`
* **CLI**: `typer`
* **HTTP**: `httpx`
* **Async Model**: `asyncio` only (never block the loop)
* **Formatting & Linting**: `ruff` (single source of truth)
* **Type Checking**: `ty` (strict by default when feasible)
* **Testing**: `pytest`
* **Task Runner**: `taskipy`

> **Rule**: never use `pip`, `poetry`, or `python` directly unless explicitly requested.

### ⚡ TypeScript / JS (Secondary)

* **Runtime / Manager**: `bun`
* **API**: `hono`
* **Validation**: `zod`
* **ORM**: `drizzle` or `prisma`
* **Tests**: `bun test`

---

## 3. Project Structure (src‑layout)

```text
myproj/
├─ pyproject.toml
├─ README.md
├─ AGENTS.md
├─ llms.txt
├─ .gitignore
├─ .env.example
├─ src/
│  └─ myproj/
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ core.py
│     ├─ web/                # optional HTML-first mode
│     │  ├─ main.py          # FastAPI app instance
│     │  ├─ templates.py     # Jinja/Jx environment + render helpers
│     │  ├─ components/      # Jx components (converted from partials)
│     │  ├─ forms/           # Formidable forms
│     │  └─ assets/          # Jx asset pipeline (no CDN)
│     └─ adapters/
│        └─ http.py
└─ tests/
   └─ test_core.py
```

### Why `src/`?

* Prevents accidental local imports
* Enforces real packaging behavior
* Improves test reliability

---

## 4. Project Models & Folder Organization

This repo can represent different **modes**. Pick one and keep boundaries clear.

### 4.1 App (FastAPI service)

Use when you ship an HTTP API.

```text
myapp/
├─ pyproject.toml
├─ README.md
├─ AGENTS.md
├─ llms.txt
├─ .env.example
├─ src/
│  └─ myapp/
│     ├─ __init__.py
│     ├─ main.py           # FastAPI app instance
│     ├─ api/              # routers, deps
│     ├─ domain/           # business rules
│     ├─ services/         # use-cases
│     ├─ adapters/         # IO boundaries (http, db, queues)
│     └─ settings.py       # config loading
└─ tests/
```

### 4.2 Package (library)

Use when you ship a reusable library.

```text
mypkg/
├─ pyproject.toml
├─ README.md
├─ AGENTS.md
├─ llms.txt
├─ src/
│  └─ mypkg/
│     ├─ __init__.py
│     ├─ public.py         # stable public API
│     ├─ _internal/        # non-public modules
│     └─ py.typed          # if you ship typing
└─ tests/
```

### 4.3 Scripts (ops / data / one-off)

Use when you run small programs, migrations, data jobs.

```text
myscripts/
├─ pyproject.toml
├─ README.md
├─ llms.txt
├─ scripts/
│  ├─ backfill_users.py
│  └─ export_metrics.py
└─ src/
   └─ myscripts/
      └─ shared/           # reusable helpers shared by scripts
```

### 4.4 Tools (developer tooling / CLIs)

Use when you ship internal CLIs.

```text
mytools/
├─ pyproject.toml
├─ README.md
├─ llms.txt
├─ src/
│  └─ mytools/
│     ├─ __init__.py
│     ├─ cli.py            # Typer app
│     └─ commands/
└─ tests/
```

> **Rule**: keep each mode isolated. A service should not hide business logic inside routers; scripts should reuse shared modules instead of copying code.

---

## 5. pyproject.toml (Multi-Model Template)

> Replace `myproj` and enable only what you use.

```toml
[project]
name = "myproj"
version = "0.1.0"
description = "Modern Python project using uv, ruff, ty, pytest, and taskipy"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12",
  "rich>=13.7",
  "httpx>=0.27",
]

[project.optional-dependencies]
# Core dev workflow
_dev = [
  "pytest>=8.0",
  "taskipy>=1.12",
  "ruff>=0.6",
  "ty>=0.0",
]

# App / FastAPI mode
app = [
  "fastapi>=0.111",
  "uvicorn>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
]

# HTML-first Web mode
web = [
  "fastapi>=0.111",
  "uvicorn>=0.30",
  "jinja2>=3.1",
  "jx",
  "formidable",
]

# Data / scripts mode
scripts = [
  "python-dotenv>=1.0",
  "tenacity>=8.3",
  "orjson>=3.10",
]

# Library shipping (optional)
package = [
  "typing-extensions>=4.12",
]

# Observability (optional)
obs = [
  "structlog>=24.2",
]

[project.scripts]
myproj = "myproj.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "C4", "RUF"]
fixable = ["ALL"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.taskipy.tasks]
# Running
run = "uv run myproj --help"

# Quality
format = "uv run ruff format ."
lint = "uv run ruff check ."
lint_fix = "uv run ruff check . --fix"
typecheck = "uv run ty check src tests"
test = "uv run pytest"

# App shortcuts (if using FastAPI mode)
serve = "uv run uvicorn myproj.main:app --reload --port 8000"

# Web shortcuts (if using HTML-first Web mode)
serve_web = "uv run uvicorn myproj.web.main:app --reload --port 8000"

# All-in-one
check = "task format && task lint && task typecheck && task test"
```

### Installing per mode

```bash
# base
uv sync

# dev workflow
uv sync --extra _dev

# fastapi app
uv sync --extra _dev --extra app

# html-first web
uv sync --extra _dev --extra web

# scripts/data jobs
uv sync --extra _dev --extra scripts
```

---

## 5. llms.txt (LLM‑Friendly Contract)

> This is a project-level contract for autonomous agents.

```text
# llms.txt — Project Guidance for LLMs

## Purpose
- Modern Python project with strict tooling (uv, ruff, ty)

## Source of Truth
- Code lives in `src/myproj/`
- Entry point: `uv run myproj`

## Commands
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Typecheck: `uv run ty check src tests`
- Tests: `uv run pytest`

## Conventions
- Small pure functions
- IO only at boundaries (CLI / adapters)
- Explicit dependencies

## API discovery (use shell tools first)
Before implementing an HTTP client, discover the API using httpx-cli:

- `uvx --from httpx httpx https://api.example.com`
- `uvx --from httpx httpx https://api.example.com -H "Accept: application/json"`
- `uvx --from httpx httpx https://api.example.com -m POST -j '{"ok": true}'`

If response is JSON, validate with:
- `... | jq '.'`
```

---

## 6. Development Workflow ("Tree Strategy")

1. **Isolation**

   * Each task = independent tree / feature branch
   * Never mix unrelated changes

2. **Atomic Implementation**

   * Split by responsibility
   * Example:

     * `auth/service.py`
     * `auth/schemas.py`
     * `auth/dependencies.py`

3. **Validation Loop (Mandatory)**

```bash
uv run ruff format .
uv run ruff check . --fix
uv run ty check src tests
uv run pytest
```

4. **Merge Criteria**

* Zero lint errors
* Types checked
* Tests passing
* No debug prints

---

## 7. Python Coding Standards

* Use `pathlib` instead of `os.path`
* Use `f-strings` only
* Prefer early returns (avoid deep nesting)
* No global mutable state
* Use `logging`, not `print`
* Modern typing (`str | None`, `list[str]`)

---

## 8. Testing Rules

* Prefer real implementations over mocks
* Mock only external APIs
* Test happy path + failure path
* Tests must be deterministic

---

## 9. Shell Tools First (LLM Agent Rule)

When shell access is available, prefer **existing CLI tools** to inspect, fetch, transform, and validate data before writing code.

### 9.1 Explore & verify

```bash
# map repo
tree -L 3 -I '__pycache__|node_modules|.git|.venv|dist|build'

# locate files
find . -name "*pattern*" -not -path "*/.*"

# search code
grep -r "search_term" . --exclude-dir={.git,.venv,node_modules,__pycache__}

# inspect env
env | grep -i SOME_VAR
```

### 9.2 Fetching & HTTP inspection (prefer CLIs)

#### httpx-cli via uvx (recommended)

```bash
uvx --from httpx httpx https://example.com
uvx --from httpx httpx https://api.example.com -H "Accept: application/json"
uvx --from httpx httpx https://api.example.com -m POST -j '{"ok": true}'
```

#### Alternatives (only if installed)

```bash
curl -i https://example.com
wget -qO- https://example.com
```

### 9.3 Data transforms (use tools when possible)

```bash
# JSON
jq '.' file.json

# logs
rg "ERROR" -n .

# quick benchmarks (rough)
time uv run myproj ...
```

> **Rule**: if a shell tool can answer quickly and safely (inspection, search, fetching), use it before generating more code.

---

## 10. uv & uvx Command Cookbook

### Project

```bash
uv sync
uv add <pkg>
uv add --dev <pkg>
uv run myproj
```

### One-off tools (uvx)

#### Ruff / Ty without installing

```bash
uvx --from ruff ruff format .
uvx --from ruff ruff check . --fix
uvx --from ty ty check src tests
```

#### httpx-cli (API discovery)

```bash
uvx --from httpx httpx https://api.example.com
```

---

## 10. Recommended Modern Python Packages

### CLI / UX

* typer
* rich
* textual

### HTTP / Async

* httpx
* anyio
* tenacity

### Data / Performance

* orjson
* msgspec
* polars

### Config & Logs

* python‑dotenv
* structlog

---

## 11. Performance & Optimization Practices

### 11.1 Choose the right shape of work

* Prefer **batching** over many small calls (DB/HTTP)
* Prefer **streaming** for large payloads (files, responses)
* Keep IO at the edges; keep core logic pure and testable

### 11.2 Async performance (FastAPI / HTTPX)

* Never block the event loop: avoid CPU-heavy work in request handlers
* Use timeouts everywhere (connect/read/write)
* Reuse clients: `httpx.AsyncClient` should be long-lived (startup/shutdown lifecycle)
* Apply concurrency limits with semaphores for fan-out calls

### 11.3 Serialization & parsing

* Use `orjson` for hot paths (large JSON)
* Avoid unnecessary encode/decode cycles
* Use `msgspec` when you need fast schema-based parsing/encoding

### 11.4 Hot loops & CPU work

* Prefer built-ins and comprehensions (when readable)
* Cache invariants outside loops; use `lru_cache` for pure expensive functions
* For very hot paths, profile first; only then consider `polars`/`numpy` or moving hotspots to a compiled language

### 11.5 Profile before optimizing

* Use `cProfile` or `py-spy` (if available)
* Optimize only what the profiler highlights

---

## 12. Recommended Modern Python Packages

### CLI / UX

* `typer`, `rich`, `textual`

### HTTP / Async

* `httpx`, `anyio`, `tenacity`

### Data / Performance

* `orjson`, `msgspec`, `polars`

### Config & Logs

* `python-dotenv`, `structlog`

---

## 13. Web Mode Additions (HTML-first production path)

> This section keeps the original doc’s style, but adds the concrete upgrades we discussed.

### 13.1 Convert `partials/items.html` → Jx component

**Goal**: stop duplicating markup across partials and pages.

`src/myproj/web/components/items.jinja`

```jinja
{#def items #}
<ul class="space-y-2">
  {% for item in items %}
    <li class="rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2">
      {{ item }}
    </li>
  {% endfor %}
</ul>
```

Usage inside templates:

```jinja
<Items items={{ items }} />
```

### 13.2 Create a real form with Formidable + HTMX

**Goal**: server-side validation with HTMX partial returns.

`src/myproj/web/forms/user_form.py`

```python
from formidable import Form
from formidable.fields import Text

class UserForm(Form):
    name = Text(required=True)
```

`src/myproj/web/templates/partials/user_form.html`

```jinja
<form hx-post="/forms/user" hx-target="#form-result" hx-swap="innerHTML">
  <div class="space-y-2">
    {{ form.name }}
    <button
      type="submit"
      class="rounded-lg bg-teal-500 px-4 py-2 font-medium text-zinc-950 hover:bg-teal-400"
    >
      Save
    </button>
  </div>
</form>
<div id="form-result" class="mt-3"></div>
```

FastAPI endpoint (returns a fragment on error/success):

```python
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.post("/forms/user", response_class=HTMLResponse)
async def submit_user(request: Request) -> HTMLResponse:
    form = UserForm.from_request(request)

    if not form.is_valid():
        html = render("partials/user_form.html", {"request": request, "form": form})
        return HTMLResponse(html, status_code=400)

    return HTMLResponse("<p class='text-emerald-400'>Saved</p>")
```

### 13.3 Add Jx asset pipeline (no CDN)

**Goal**: production-ready assets (Tailwind build, cache-busting, no CDN).

Recommended approach:

* Keep Tailwind source in `assets/tailwind.css`.
* Build Tailwind via `tailwindcss` CLI or a Node/Bun toolchain.
* Register generated assets in Jx’s pipeline and render them via `assets.render_css()` / `assets.render_js()`.

Example structure:

```text
src/myproj/web/
  assets/
    tailwind.css
    app.js
  static/
    dist/
      app.css
      app.js
```

`layout.jinja` should switch from CDN to pipeline:

```jinja
{{ assets.render_css() }}
...
{{ assets.render_js() }}
```

Task suggestions (taskipy):

```toml
[tool.taskipy.tasks]
# build tailwind (example)
build_css = "bunx tailwindcss -i src/myproj/web/assets/tailwind.css -o src/myproj/web/static/dist/app.css --minify"
serve_web = "uv run uvicorn myproj.web.main:app --reload --port 8000"
```

> **Rule**: in dev you may use CDN, but production must use the pipeline.

---

## 14. Safety & Agent Protocol

* Always read files before editing
* Never invent APIs or flags
* Fix errors instead of apologizing
* Never delete files without confirmation
* Never push directly to `main`
* Always run formatter & linter after edits

