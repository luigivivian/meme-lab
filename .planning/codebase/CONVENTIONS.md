# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

**Files:**
- React components: `kebab-case.tsx` (e.g., `step-analysis.tsx`, `loading-overlay.tsx`)
- React hooks: `use-kebab-case.ts` (e.g., `use-api.ts`, `use-pipeline.ts`, `use-ads.ts`)
- Next.js pages: `page.tsx` per route directory
- Python modules: `snake_case.py` (e.g., `bg_remover.py`, `scene_composer.py`)
- Python test files: `test_snake_case.py` (e.g., `test_auth.py`, `test_atomic_counter.py`)

**Functions (TypeScript):**
- Regular functions: `camelCase` (e.g., `formatDate`, `toggleSection`, `inferSource`)
- React components: `PascalCase` (e.g., `AdWizard`, `ImageDropzone`, `SubmitOverlay`)
- Hook exports: `useCamelCase` (e.g., `useStatus`, `useAdJobs`, `usePipeline`)
- Event handlers: `handleNoun` or `handleVerb` (e.g., `handleSubmit`, `handleImageUpload`, `handleAnalyze`)
- Toggle helpers: `toggleNoun` (e.g., `toggleSection`, `toggleFormat`)

**Functions (Python):**
- Module-level helpers: `snake_case` (e.g., `_init_step_state`, `_calc_progress`, `_get_user_job`)
- Private helpers prefixed with `_` (e.g., `_job_to_response`, `_mock_session_for_list`)
- Async DB dependencies: `async def db_session()`, `async def get_current_user()`

**Variables:**
- TypeScript: `camelCase` for locals, `SCREAMING_SNAKE_CASE` for module-level constants
- Python: `snake_case` for locals, `SCREAMING_SNAKE_CASE` for module constants
- Color/status maps: `NOUN_COLORS`, `STATUS_BADGE`, `STYLE_LABELS` — `Record<string, string>`

**Types:**
- TypeScript interfaces: `PascalCase` prefixed with subject (e.g., `AdCreateRequest`, `DriveImagesResponse`)
- TypeScript enums/union types: string literals (e.g., `"idle" | "running" | "done" | "error"`)
- Python Pydantic models: `PascalCase` (e.g., `SingleRequest`, `EnhanceRequest`, `AdJobResponse`)

## Code Style

**Formatting:**
- No Prettier or ESLint config file found — formatting is not enforced via tooling
- ESLint is installed (`eslint-config-next`) but no custom `.eslintrc` — uses Next.js defaults
- TypeScript strict mode enabled (`"strict": true` in `tsconfig.json`)

**Python:**
- No `black` or `ruff` config found — style is hand-maintained
- Docstrings only on module files and class-level defs where the intent is non-obvious
- Inline comments used for decision references: `# per D-20`, `# Phase 8`, `# QUOT-02`

**TypeScript:**
- Single quotes not enforced — double quotes used in JSX attributes, backticks for template strings
- Semicolons: not enforced — style is implicit
- `"use client"` directive at the top of every interactive component/page

## Import Organization

**TypeScript order (observed):**
1. React and Next.js (`"react"`, `"next/navigation"`, `"next/link"`)
2. Third-party libraries (`"framer-motion"`, `"lucide-react"`, `"swr"`)
3. UI primitives from `@/components/ui/` (Radix-based shadcn components)
4. Project components from `@/components/`
5. Hooks from `@/hooks/`
6. Utilities and constants from `@/lib/` (`api`, `utils`, `constants`, `animations`)
7. Types imported via `import type { ... }` at end of block

**Path Aliases:**
- `@/*` maps to `memelab/src/*` (configured in `tsconfig.json` and `vitest.config.ts`)

**Python order (observed):**
1. Standard library (`logging`, `asyncio`, `os`, `uuid`)
2. Third-party (`fastapi`, `sqlalchemy`, `pydantic`)
3. Internal `src.*` imports (absolute, not relative)

## Error Handling

**TypeScript — API errors:**
- `request<T>()` in `src/lib/api.ts` throws `Error("API {status}: {text}")` for non-2xx
- 401 errors trigger automatic logout + redirect to `/login` (except for `/auth/` endpoints)
- Component-level catches assign to a local `error: string | null` state variable
- Silent failures in non-critical paths (e.g., `analyze` in `wizard.tsx` catches and does nothing)
- Optimistic UI updates with explicit revert on catch (in `use-pipeline.ts`: `approve`, `reject`, etc.)
- Polling loops use empty `catch {}` with comment `// keep polling` to avoid breaking the interval

**Python — FastAPI errors:**
- `HTTPException(status_code=..., detail="...")` for all user-facing errors
- 404 for not found, 403 for forbidden, 401 for auth failures, 409 for conflicts
- Private helper `_get_user_job()` centralizes 404 check per resource type
- Internal Python exceptions (`PermissionError`, `ValueError`) raised from repositories, caught and converted at the route layer

## Logging

**Python:**
- Each module creates its own logger: `logger = logging.getLogger("clip-flow.api.ads")`
- Root config in `src/api/app.py`: `format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"`
- Log sanitizer (`src/api/log_sanitizer.py`) strips API keys, tokens, and DB passwords from all log records
- Startup events logged at INFO level with relevant state (model count, scheduler status)

**TypeScript:**
- No logging framework — console only (not observed in component code)

## Comments

**Decision references:** Python code uses inline comments like `# per D-20`, `# Phase 8`, `# QUOT-02` to link implementation to planning decisions. Do not remove these — they trace why a behavior exists.

**Section separators:** Both languages use `# ── Section name ──` or `// ── Section name ──` to divide large files into logical blocks.

**JSDoc/TSDoc:** Not used. Types are expressed through TypeScript interfaces and Pydantic models, not prose comments.

**When to comment:**
- Decision rationale (especially workarounds): `// Use UTC methods to avoid server/client hydration mismatch`
- Non-obvious algorithmic choices: `// Capture dragging.current in local var before setNodes (race condition)`
- Empty catch blocks must explain intent: `// keep polling on transient errors`

## Function Design

**Size:** Functions stay focused — large pages are split into private sub-components (e.g., `Section`, `ImageDropzone`, `SubmitOverlay` in `wizard.tsx`)

**Parameters:** Typed via interfaces or inline types. Optional params use `?` or `= defaultValue`. No positional-only patterns.

**Return Values:**
- TypeScript async functions return `Promise<void>` or `Promise<T>` explicitly in hooks
- Python route handlers return Pydantic response models or dicts
- Python helpers that can fail return `None` and callers check (e.g., `scalar_one_or_none()`)

## Module Design

**Exports:**
- TypeScript: named exports for everything except page components (which are default exports)
- No barrel `index.ts` files — each module is imported directly by path
- Python: no `__all__` — modules export everything; private helpers prefixed with `_`

**Barrel Files:** Not used. Import directly from `@/lib/api`, `@/lib/constants`, `@/hooks/use-api`.

## Component Design Patterns

**Shadcn/UI pattern:** UI primitives in `src/components/ui/` use `React.forwardRef`, `cva()` for variants, and `cn()` for class merging. New UI components must follow this pattern.

**Page components:** All pages are `"use client"` — no server components in use. Pages own data fetching via SWR hooks and render sub-components with derived state.

**Sub-components in page files:** When a component is only used within one page, it is defined in the same file (not extracted). Example: `Section`, `ImageDropzone`, `SubmitOverlay` all live in `wizard.tsx`.

**SWR key pattern:** Cache keys are deterministic strings composed from params:
```typescript
const key = `drive-images-${query?.theme ?? ""}-${query?.category ?? ""}-${query?.limit ?? 20}-${query?.offset ?? 0}`;
```
Never use `JSON.stringify()` for SWR keys. Never use `null` unless conditionally disabling (e.g., `slug ? \`character-${slug}\` : null`).

**Conditional SWR:** Pass `null` as key to disable a hook until a condition is met:
```typescript
return useSWR(
  slug && enabled ? `refs-generate-${slug}` : null,
  () => (slug ? api.getRefsGenerateStatus(slug) : null),
  { refreshInterval: 2000 }
);
```

**Status/color maps:** Use `Record<string, string>` maps defined at module level for status-to-class mappings. Access with fallback: `STATUS_BADGE[job.status] ?? STATUS_BADGE.draft`.

**Optimistic updates:** Use `setState(s => ({...s, items: s.items.map(...)}))` pattern, then revert on catch.

---

*Convention analysis: 2026-03-30*
