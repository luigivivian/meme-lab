# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

**Files:**
- Python: lowercase with underscores (`async_orchestrator.py`, `image_worker.py`, `prompt_builder.py`)
- TypeScript: camelCase (`use-api.ts`, `character-context.tsx`, `agent-modal.tsx`)
- React components: PascalCase (`DashboardPage.tsx`, `AgentModal.tsx`, `StatsCard.tsx`)
- Test files: `test_*.py` or `*.test.ts` (though testing is minimal)

**Functions & Methods:**
- Python: snake_case (`async def fetch()`, `def _init_gemini_image()`, `def generate_phrases()`)
- Private/internal methods: prefix with `_` (`_get_client()`, `_ollama_available()`, `_try_gemini()`)
- Async functions: use `async def` keyword, prefix with `a` when wrapping sync (e.g., `agenerate_image()`)
- TypeScript: camelCase (`useStatus()`, `getDriveImages()`, `handleQuickRun()`)

**Variables:**
- Python: snake_case (`work_order`, `trend_item`, `background_path`, `gemini_client`)
- Semaphores/locks: `_[resource]_semaphore` (e.g., `_gpu_semaphore`, `_gemini_image_semaphore`)
- Global clients: `_[client]` (e.g., `_client`, `_ollama_client`)
- TypeScript: camelCase (`activeCharacter`, `isLoading`, `sourceDistribution`)

**Types & Classes:**
- Python: PascalCase (`AsyncSourceAgent`, `GoogleTrendsAgent`, `ContentGenerator`, `TrendBroker`)
- TypeScript interfaces: PascalCase (`StatusResponse`, `AgentInfo`, `ContentPackage`)
- Dataclasses: PascalCase with descriptive name (`TrendEvent`, `WorkOrder`, `ComposeResult`)
- Enums: PascalCase values (`TrendSource.BLUESKY`, `TrendSource.HACKERNEWS`)

**Constants:**
- Python: UPPER_SNAKE_CASE in `config.py` (`PIPELINE_IMAGES_PER_RUN`, `GEMINI_MAX_CONCURRENT`, `TEXT_VERTICAL_POSITION`)
- TypeScript: UPPER_SNAKE_CASE for constants, but most use PascalCase dict objects (`NAV_ITEMS`, `STATUS_COLORS`, `AGENT_TYPE_COLORS`)

## Code Style

**Formatting:**
- No explicit formatter configured (no `.eslintrc`, `.prettierrc`, or `pyproject.toml` with formatting)
- Python follows PEP 8 informally: 4-space indentation, max 88 chars (observed)
- TypeScript uses standard conventions: 2-space indentation, semicolons present

**Linting:**
- Python: No linter configuration detected, but code follows standards
- TypeScript: ESLint configured via Next.js default (`eslint: ^9.27.0`, `eslint-config-next: ^15.3.3`)
- Next.js built-in linting via `npm run lint` command

**Line Length:**
- Python source: typical 80-120 characters
- Comments: 88-100 characters preferred
- TypeScript: 88-100 characters typical

## Import Organization

**Order (Python):**
1. Standard library (`asyncio`, `logging`, `json`, `os`, `pathlib`)
2. Third-party (`google.genai`, `sqlalchemy`, `fastapi`, `pydantic`)
3. Config (`from config import ...`)
4. Local project (`from src.pipeline import ...`, `from src.database import ...`)
5. Blank line between groups

Example from `src/pipeline/async_orchestrator.py`:
```python
import logging
import time
import traceback
from datetime import datetime

from config import (
    PIPELINE_GOOGLE_TRENDS_GEO,
    PIPELINE_REDDIT_SUBREDDITS,
    PIPELINE_RSS_FEEDS,
)
from src.pipeline.agents.async_base import SyncAgentAdapter
from src.pipeline.monitoring import MonitoringLayer
```

**Order (TypeScript):**
1. React/Next.js imports (`"use client"` directive first if present)
2. Standard imports (`import { useState } from "react"`)
3. Third-party (`import { motion } from "framer-motion"`)
4. Local imports (`import { Button } from "@/components/ui/button"`)
5. Alias imports use `@/` prefix

Example from `memelab/src/app/dashboard/page.tsx`:
```typescript
"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Image, Bot, Workflow } from "lucide-react";
import { staggerContainer } from "@/lib/animations";
import { StatsCard } from "@/components/panels/stats-card";
```

**Path Aliases:**
- TypeScript: `@/` points to `src/` directory (defined in `tsconfig.json`)
- All imports use alias: `@/hooks`, `@/components`, `@/lib`, `@/contexts`

## Error Handling

**Patterns:**

**Python — Try/Except with Logging:**
```python
try:
    result = await operation()
except TimeoutError as e:
    logger.error(f"Operation timed out: {e}")
    return fallback_value  # or raise after logging
except Exception as e:
    logger.warning(f"Non-critical error: {e}")
    return None  # Handle gracefully or use fallback
```

**Python — Optional Return (implicit None):**
```python
def _try_gemini(self, work_order: WorkOrder) -> tuple:
    if not self._gemini_client:
        return None, "static", {}  # Tuple unpacking expected
    try:
        result = await self._gemini_client.agenerate_image(...)
        if result:
            return result.path, "gemini", {metadata}
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
    return None, "static", {}
```

**Python — Fallback Chains:**
```python
# Priority: ComfyUI → Gemini → Static
bg_path, source, metadata = await self._try_comfyui(...)
if not bg_path:
    bg_path, source, metadata = await self._try_gemini(...)
if not bg_path:
    bg_path = get_static_background()
```

**TypeScript — Fetch Error Wrapping:**
```typescript
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {...options});
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}
```

**TypeScript — Hook Error Handling (via SWR):**
```typescript
const { data: status, isLoading, error } = useStatus();
// SWR handles retries (errorRetryCount: 2) and automatic recovery
// Components typically show loading state then fallback value
```

**Global Exception Handlers:**
- Python: Agent methods catch internally and return empty lists, logged as warnings
- Python: Worker methods catch and fallback to next strategy
- TypeScript: API layer throws with HTTP status, caller handles

## Logging

**Framework:**
- Python: `logging` module (standard library)
- TypeScript: Console (no structured logging detected)
- No external logging service (Sentry, LogRocket)

**Patterns:**

**Python — Logger Setup:**
```python
import logging
logger = logging.getLogger("clip-flow.[module_name]")

# Configured in src/api/app.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
```

**Logger Names:**
- `clip-flow.api`
- `clip-flow.async_orchestrator`
- `clip-flow.worker.image`
- `clip-flow.llm`
- `clip-flow.analyzer`

**When/How to Log:**

| Level | When | Example |
|-------|------|---------|
| `INFO` | Start/stop operations, config | `logger.info(f"Background mode: {mode}")` |
| `WARNING` | Recoverable errors, fallbacks | `logger.warning(f"Gemini unavailable: {e}")` |
| `ERROR` | Unrecoverable, request fails | `logger.error(f"Agent {name} failed: {e}")` |
| `DEBUG` | Detailed flow (not seen at INFO) | Would use but not in codebase |

**No Debug Logging:**
- No `logger.debug()` calls observed in production code
- Focus is INFO for state changes, WARNING for issues

## Comments

**When to Comment:**
- Module docstring: Always (describe purpose, key functions)
- Function docstring: Key functions only (not every method)
- Inline comments: Explain "why" not "what" (code should be self-documenting)
- TODOs: Mark known limitations or deferred work

**DocString Format:**

**Python — Google-style (informal):**
```python
def analyze(self, trends: list[TrendItem], count: int = 5) -> list[AnalyzedTopic]:
    """Envia trends para LLM e recebe topicos curados."""
    # Detailed comments in code if needed
```

**Python — Module docstring (detailed):**
```python
"""ImageWorker — gera background e compoe imagem final.

Prioridade de geracao de background (config.IMAGE_BACKEND_PRIORITY):
- "comfyui": ComfyUI local (custo zero) → Gemini API → estatico
- "gemini":  Gemini API → ComfyUI local → estatico

Usa Semaphore para serializar acessos a recursos limitados.
"""
```

**TypeScript — TSDoc minimal:**
```typescript
// Usually no explicit JSDoc — types are self-documenting
const { data: status, isLoading } = useStatus();  // Clear from function name
```

## Function Design

**Size:**
- Python functions: 10-50 lines typical, up to 100 for complex workers
- Async orchestrator methods: up to 150 lines (event-driven pattern)
- Break into `_private_helper()` methods for clarity

**Parameters:**
- Use positional for first 1-2 required args
- Use keyword-only for optional config (preferred in Python 3.8+)
- Avoid more than 5 positional params (use dataclass if more needed)

Example:
```python
async def agenerate_image(
    self,
    situacao_key: str,
    semaphore: asyncio.Semaphore,
    phrase_context: str = "",
) -> GenerateResult | None:
    """Keep simple: required → optional → semaphore."""
```

**Return Values:**
- Single return type preferred (not Union unless necessary)
- Optional returns: return `None` explicitly, never silent `None`
- Tuple unpacking: `path, source, metadata = await worker()`
- Dict with consistent keys for structured data

## Module Design

**Exports:**
- Python: No `__all__` observed; export public classes/functions at module level
- TypeScript: Named exports preferred over default
- Examples: `export function useStatus()`, `export interface StatusResponse`

**Barrel Files:**
- Used in `src/api/routes/__init__.py`: imports all route modules (allows `from src.api.routes import generation`)
- Used in `src/database/repositories/__init__.py`: exports all repo classes
- Minimal re-export, mostly for organizational clarity

**Organization by Feature:**
- Database: `models.py` (ORM) → `repositories/` (queries) → `session.py` (connection)
- Pipeline: `models_v2.py` (data) → `agents/` (sources) → `processors/` (logic) → `workers/` (workers)
- API: `app.py` (FastAPI) → `routes/` (endpoints) → `models.py` (Pydantic) → `serializers.py` (conversion)

## Language-Specific Notes

**Python:**
- Type hints used throughout (no bare `*args`, `**kwargs`)
- Async/await consistently used for I/O
- Dataclasses preferred for simple data holders
- String formatting: f-strings only

**TypeScript:**
- Strict mode implied (tsconfig.json default)
- Interface over type for contracts
- React hooks: `use*` naming convention
- No `any` types observed (proper typing throughout)

---

*Convention analysis: 2026-03-23*
