---
phase: quick
plan: 260325-qhl
type: execute
wave: 1
depends_on: []
files_modified:
  - src/image_gen/gemini_client.py
  - src/database/models.py
  - src/database/migrations/versions/011_add_cost_usd_to_api_usage.py
  - src/database/repositories/usage_repo.py
  - src/api/routes/generation.py
  - src/api/routes/auth.py
  - src/auth/schemas.py
autonomous: true
requirements: [COST-TRACK]

must_haves:
  truths:
    - "Token estimation uses real tile-based calculation (ceil(w/768)*ceil(h/768)*258) per input image instead of flat 258"
    - "Each generation logs estimated cost in USD to the console"
    - "ImageGenerationResult carries estimated_cost_usd field"
    - "api_usage table has cost_usd column tracking cumulative cost per day/service bucket"
    - "GET /auth/me/cost-stats returns total cost, image count, and average cost per image"
  artifacts:
    - path: "src/image_gen/gemini_client.py"
      provides: "Tile-based token estimation, cost constants, estimate_cost() function"
      contains: "def estimate_generation_cost"
    - path: "src/database/migrations/versions/011_add_cost_usd_to_api_usage.py"
      provides: "Alembic migration adding cost_usd column"
      contains: "cost_usd"
    - path: "src/database/repositories/usage_repo.py"
      provides: "Updated increment() accepting cost_usd, get_cost_stats() method"
      contains: "cost_usd"
    - path: "src/api/routes/auth.py"
      provides: "GET /auth/me/cost-stats endpoint"
      contains: "cost-stats"
  key_links:
    - from: "src/image_gen/gemini_client.py"
      to: "src/api/routes/generation.py"
      via: "ImageGenerationResult.estimated_cost_usd passed to _increment_usage"
      pattern: "estimated_cost_usd"
    - from: "src/api/routes/generation.py"
      to: "src/database/repositories/usage_repo.py"
      via: "_increment_usage passes cost_usd to repo.increment()"
      pattern: "cost_usd"
---

<objective>
Add real Gemini Image cost tracking: fix token estimation to use tile-based calculation, add cost_usd to the usage table, and expose a cost stats endpoint.

Purpose: Currently token estimation uses a flat 258 tokens per image regardless of dimensions. The real Gemini pricing uses ceil(w/768)*ceil(h/768)*258 tokens per input image tile. Image output tokens (~1290 per image at 1024px) cost 100x more than text ($30/1M vs $0.30/1M). Without accurate cost tracking, there is no visibility into actual API spend.

Output: Accurate per-generation cost estimates logged and persisted, cumulative cost stats available via API.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/image_gen/gemini_client.py
@src/database/models.py
@src/database/repositories/usage_repo.py
@src/api/routes/generation.py
@src/api/routes/auth.py
@src/auth/schemas.py

<interfaces>
<!-- Key types and contracts the executor needs -->

From src/image_gen/gemini_client.py:
```python
@dataclass
class ImageGenerationResult:
    path: str
    theme_key: str = ""
    pose: str = ""
    scene: str = ""
    prompt_used: str = ""
    source: str = "gemini"
    is_refined: bool = False
    refinement_passes: int = 0
    reference_images: list[str] = field(default_factory=list)
    rendering_config: dict = field(default_factory=dict)
    phrase_context_used: bool = False
    character_dna_used: bool = False
```

From src/image_gen/gemini_client.py (_tentar_gerar, line 797-798):
```python
# Current WRONG estimation — flat 258 per image:
estimated_tokens = len(img_parts) * 258 + text_chars // 4
```

From src/image_gen/gemini_client.py (_pil_para_part, line 574):
```python
# Images are resized to max 1024px before sending:
img_r = _redimensionar(img, 1024)
```

From src/database/models.py (ApiUsage):
```python
class ApiUsage(TimestampMixin, Base):
    __tablename__ = "api_usage"
    id, user_id, service, tier, date, usage_count, status
    # NO cost_usd column currently
```

From src/database/repositories/usage_repo.py:
```python
async def increment(self, user_id, service, tier, status="success") -> int:
    # No cost_usd parameter currently
```

From src/api/routes/generation.py:
```python
async def _increment_usage(session, user_id, tier):
    repo = UsageRepository(session)
    await repo.increment(user_id=user_id, service="gemini_image", tier=tier.replace("gemini_", ""))
    await session.commit()
```

From src/auth/schemas.py:
```python
class ServiceUsage(BaseModel):
    service: str; tier: str; used: int; limit: int; remaining: int

class UsageResponse(BaseModel):
    services: list[ServiceUsage]; resets_at: str
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix token estimation and add cost calculation to gemini_client.py</name>
  <files>src/image_gen/gemini_client.py</files>
  <action>
  1. Add cost constants at module level (after the MODELOS_IMAGEM section, around line 78):

  ```python
  # Gemini 2.5 Flash Image pricing (pay-as-you-go, per 1M tokens)
  GEMINI_INPUT_PRICE_PER_M = 0.30    # $0.30/1M input tokens
  GEMINI_IMAGE_OUTPUT_PRICE_PER_M = 30.00  # $30.00/1M image output tokens
  GEMINI_IMAGE_OUTPUT_TOKENS = 1290   # ~tokens per generated image at 1024px
  ```

  2. Add a module-level function `estimate_image_input_tokens(width: int, height: int) -> int` that implements the real tile-based calculation:
     - `tiles = math.ceil(width / 768) * math.ceil(height / 768)`
     - `return tiles * 258`
     - Import math at the top of the file.

  3. Add a module-level function `estimate_generation_cost(input_images: list[tuple[int, int]], text_chars: int) -> dict` that:
     - Calculates input image tokens using `estimate_image_input_tokens()` for each (width, height) tuple
     - Calculates text input tokens as `text_chars // 4`
     - Total input tokens = sum of all image tokens + text tokens
     - Output tokens = `GEMINI_IMAGE_OUTPUT_TOKENS` (fixed per image)
     - `input_cost = total_input_tokens * GEMINI_INPUT_PRICE_PER_M / 1_000_000`
     - `output_cost = GEMINI_IMAGE_OUTPUT_TOKENS * GEMINI_IMAGE_OUTPUT_PRICE_PER_M / 1_000_000`
     - `total_cost = input_cost + output_cost`
     - Returns `{"input_tokens": int, "output_tokens": int, "estimated_cost_usd": float}`

  4. Add `estimated_cost_usd: float = 0.0` field to `ImageGenerationResult` dataclass (add after `character_dna_used`).

  5. Fix the token estimation in `_tentar_gerar()` (line 797-798). Replace the flat `len(img_parts) * 258` with tile-based calculation:
     - For each img_part in `img_parts`, decode the inline_data back to PIL to get dimensions (or better: extract dimensions from the parts list before encoding). Since `_tentar_gerar` receives `partes` which are already encoded Parts, the simplest approach is: keep a separate path. Instead, modify `_tentar_gerar` to accept an optional `input_image_dims: list[tuple[int, int]] | None = None` parameter. When provided, use tile-based calc; when None, fall back to the old flat estimate. This avoids breaking the method signature for other callers.
     - Update `_tentar_modelos` similarly to pass through `input_image_dims`.
     - Calculate and log the cost estimate alongside the token estimate.

  6. In `generate_image()`, before calling `_tentar_modelos()`:
     - Collect the dimensions of the resized reference images: `ref_dims = [(img.size[0], img.size[1]) for img in refs]` (note: `_pil_para_part` calls `_redimensionar(img, 1024)` so use the resized dimensions — call `_redimensionar` on each ref to get actual sent size, or compute: for a ref of size (w,h) after resize to max 1024, the dimensions are `(int(w*ratio), int(h*ratio))` where `ratio = min(1, 1024/max(w,h))`).
     - Simplest: collect dims from the refs AFTER resize. Since `_pil_para_part` resizes internally, compute it externally: `ref_dims = [_redimensionar(img, 1024).size for img in refs]`.
     - Compute text_chars from the prompt text parts.
     - Call `estimate_generation_cost(ref_dims, text_chars)` to get cost info.
     - Pass `input_image_dims=ref_dims` to `_tentar_modelos()`.
     - After successful generation, set `result.estimated_cost_usd = cost_info["estimated_cost_usd"]` on the returned `ImageGenerationResult`.
     - Log: `logger.info(f"[cost] estimated: ${cost_info['estimated_cost_usd']:.6f} (input={cost_info['input_tokens']} tokens, output={cost_info['output_tokens']} tokens)")`.

  7. In `refine_image()`, apply the same cost estimation pattern. Collect dims from imagem_base (after resize) plus any additional reference images. Log cost. The refine method returns a path string (not ImageGenerationResult), so just log the cost — no need to attach it to return value.

  Do NOT change the public API signatures of `generate_image()` or `refine_image()`. The `input_image_dims` parameter is only internal to `_tentar_gerar` / `_tentar_modelos`.
  </action>
  <verify>
    <automated>cd C:/Users/VIP/testeDev/clip-flow && python -c "from src.image_gen.gemini_client import estimate_image_input_tokens, estimate_generation_cost, ImageGenerationResult; r = ImageGenerationResult(path='test'); assert hasattr(r, 'estimated_cost_usd'); assert estimate_image_input_tokens(1024, 1024) == 2*2*258; assert estimate_image_input_tokens(768, 768) == 258; assert estimate_image_input_tokens(500, 500) == 258; cost = estimate_generation_cost([(1024, 1024)], 1000); assert cost['input_tokens'] == 2*2*258 + 250; assert cost['output_tokens'] == 1290; assert cost['estimated_cost_usd'] > 0; print('All assertions passed')"</automated>
  </verify>
  <done>
    - estimate_image_input_tokens correctly computes ceil(w/768)*ceil(h/768)*258
    - estimate_generation_cost returns input_tokens, output_tokens, estimated_cost_usd
    - ImageGenerationResult has estimated_cost_usd field
    - _tentar_gerar uses tile-based token estimation when dims provided
    - generate_image() populates estimated_cost_usd on the result and logs cost
  </done>
</task>

<task type="auto">
  <name>Task 2: Add cost_usd to database and update usage tracking</name>
  <files>
    src/database/models.py,
    src/database/migrations/versions/011_add_cost_usd_to_api_usage.py,
    src/database/repositories/usage_repo.py,
    src/api/routes/generation.py
  </files>
  <action>
  1. In `src/database/models.py`, add `cost_usd` column to `ApiUsage` class (after `usage_count`):
     ```python
     cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
     ```

  2. Create migration `src/database/migrations/versions/011_add_cost_usd_to_api_usage.py` following the project pattern (see 010 for format):
     - revision: '011', down_revision: '010'
     - `upgrade()`: `op.add_column('api_usage', sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0.0'))`
     - `downgrade()`: `op.drop_column('api_usage', 'cost_usd')`

  3. Update `UsageRepository.increment()` to accept optional `cost_usd: float = 0.0` parameter:
     - Add `cost_usd` to the `values` dict.
     - For MySQL upsert (`on_duplicate_key_update`), accumulate: `cost_usd=ApiUsage.cost_usd + cost_usd` (add to existing, same as usage_count increments).
     - For SQLite upsert (`on_conflict_do_update`), accumulate: `"cost_usd": ApiUsage.cost_usd + cost_usd`.

  4. Add method `get_cost_stats(self, user_id: int) -> dict` to `UsageRepository`:
     - Query `api_usage` where `user_id=user_id`, `service="gemini_image"`, `status="success"`.
     - Use `func.sum(ApiUsage.cost_usd)` for total cost.
     - Use `func.sum(ApiUsage.usage_count)` for total image count.
     - Use `func.count()` for number of day-buckets.
     - Return: `{"total_cost_usd": float, "total_images": int, "avg_cost_per_image": float, "days_tracked": int}`.
     - Handle None results (no rows) gracefully: return zeros.

  5. Update `_increment_usage()` in `src/api/routes/generation.py` to accept and pass `cost_usd`:
     - Change signature: `async def _increment_usage(session, user_id, tier, cost_usd: float = 0.0):`
     - Pass `cost_usd=cost_usd` to `repo.increment()`.

  6. In `generate_single()`, after successful generation, extract cost from the result:
     - For non-refine path: `cost = result.estimated_cost_usd if result else 0.0`
     - Pass to: `await _increment_usage(session, current_user.id, resolution.tier, cost_usd=cost)`
     - Add `"estimated_cost_usd": cost` to the response dict.

  7. In `compose_image()`, after successful Gemini background generation:
     - Extract `cost = bg_result.estimated_cost_usd if bg_result else 0.0` (non-refine path)
     - Pass to `_increment_usage`.
     - Add `"estimated_cost_usd": cost` to the response dict.

  8. In `refine_existing()`, the cost is harder since refine_image returns a path. For now, use a rough estimate: `cost = estimate_generation_cost([], 0)["estimated_cost_usd"] * len(resultados)` (output cost only, since we do not have ref dims here easily). Import `estimate_generation_cost` from `src.image_gen.gemini_client`. Pass to `_increment_usage`.
  </action>
  <verify>
    <automated>cd C:/Users/VIP/testeDev/clip-flow && python -c "from src.database.models import ApiUsage; assert hasattr(ApiUsage, 'cost_usd'); print('ApiUsage.cost_usd exists')" && python -c "import ast; tree = ast.parse(open('src/database/migrations/versions/011_add_cost_usd_to_api_usage.py').read()); print('Migration parses OK')" && python -c "import inspect; from src.database.repositories.usage_repo import UsageRepository; sig = inspect.signature(UsageRepository.increment); assert 'cost_usd' in sig.parameters; assert 'get_cost_stats' in dir(UsageRepository); print('UsageRepository updated OK')"</automated>
  </verify>
  <done>
    - ApiUsage model has cost_usd column (Float, default 0.0)
    - Migration 011 adds the column
    - UsageRepository.increment() accepts and accumulates cost_usd
    - UsageRepository.get_cost_stats() returns total/avg cost stats
    - generation.py passes cost_usd through to the repo on each successful generation
    - API responses include estimated_cost_usd
  </done>
</task>

<task type="auto">
  <name>Task 3: Add cost stats endpoint</name>
  <files>
    src/api/routes/auth.py,
    src/auth/schemas.py
  </files>
  <action>
  1. In `src/auth/schemas.py`, add a new Pydantic model after `UsageResponse`:
     ```python
     class CostStatsResponse(BaseModel):
         total_cost_usd: float
         total_images: int
         avg_cost_per_image: float
         days_tracked: int
     ```

  2. In `src/api/routes/auth.py`, add a new endpoint after the existing `/me/usage` endpoint:
     ```python
     @router.get("/me/cost-stats", response_model=CostStatsResponse)
     async def me_cost_stats(
         current_user=Depends(get_current_user),
         session: AsyncSession = Depends(db_session),
     ):
         """Return cumulative Gemini Image cost statistics for the current user."""
         from src.database.repositories.usage_repo import UsageRepository
         repo = UsageRepository(session)
         data = await repo.get_cost_stats(current_user.id)
         return data
     ```
     - Import `CostStatsResponse` from `src.auth.schemas` (add to the existing import line that already imports `UsageResponse`).

  3. Verify the import of CostStatsResponse is added to the existing import statement in auth.py. The current import likely looks like `from src.auth.schemas import ..., UsageResponse` — add `CostStatsResponse` to that import list.
  </action>
  <verify>
    <automated>cd C:/Users/VIP/testeDev/clip-flow && python -c "from src.auth.schemas import CostStatsResponse; c = CostStatsResponse(total_cost_usd=0.5, total_images=10, avg_cost_per_image=0.05, days_tracked=3); print(c.model_dump()); print('Schema OK')" && python -c "from src.api.routes.auth import router; routes = [r.path for r in router.routes]; assert '/me/cost-stats' in routes; print('Endpoint registered OK')"</automated>
  </verify>
  <done>
    - CostStatsResponse schema exists with total_cost_usd, total_images, avg_cost_per_image, days_tracked
    - GET /auth/me/cost-stats endpoint returns cumulative cost stats for the authenticated user
    - Endpoint is properly wired with auth dependency and returns CostStatsResponse
  </done>
</task>

</tasks>

<verification>
1. Token estimation is mathematically correct:
   - 768x768 image = 1 tile = 258 tokens
   - 1024x1024 image = 4 tiles (ceil(1024/768)=2 per axis) = 1032 tokens
   - 500x500 image = 1 tile = 258 tokens
2. Cost calculation matches Gemini pricing:
   - Output cost per image: 1290 * $30/1M = $0.0387
   - Input cost for 3 refs at 1024x1024: 3 * 1032 * $0.30/1M = ~$0.000929
   - Total per generation: ~$0.0396
3. Migration 011 adds cost_usd column
4. Usage tracking accumulates cost_usd per day bucket
5. Cost stats endpoint returns correct aggregates
</verification>

<success_criteria>
- `estimate_image_input_tokens(1024, 1024)` returns 1032 (2*2*258)
- `estimate_image_input_tokens(768, 768)` returns 258 (1*1*258)
- `estimate_generation_cost([(1024,1024)]*3, 2000)` returns sensible cost ~$0.04
- ImageGenerationResult has estimated_cost_usd field
- ApiUsage ORM model has cost_usd Float column
- Migration 011 exists and parses without errors
- UsageRepository.increment() accepts cost_usd parameter
- UsageRepository.get_cost_stats() returns dict with total_cost_usd, total_images, avg_cost_per_image, days_tracked
- GET /auth/me/cost-stats returns CostStatsResponse
- All generation endpoints pass estimated cost to usage tracking
</success_criteria>

<output>
After completion, create `.planning/quick/260325-qhl-gemini-image-cost-tracking-and-token-val/260325-qhl-SUMMARY.md`
</output>
