---
phase: quick-260330-tgu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/api/routes/reels.py
  - memelab/src/lib/api.ts
  - memelab/src/app/(app)/reels/page.tsx
autonomous: true
requirements: [ENHANCE-THEME-01]
must_haves:
  truths:
    - "After selecting a sub-theme, user sees a 'Sugerir Temas' button"
    - "Clicking the button calls Gemini and shows 5-8 topic suggestion pills"
    - "Clicking a suggestion pill populates the tema textarea with that text"
    - "Button shows loading spinner while Gemini is processing"
    - "Button is hidden when no sub-theme is selected"
  artifacts:
    - path: "src/api/routes/reels.py"
      provides: "POST /reels/enhance-theme endpoint"
      contains: "enhance_theme"
    - path: "memelab/src/lib/api.ts"
      provides: "enhanceReelTheme API function"
      contains: "enhanceReelTheme"
    - path: "memelab/src/app/(app)/reels/page.tsx"
      provides: "Sugerir Temas button + suggestion pills UI"
      contains: "Sugerir Temas"
  key_links:
    - from: "memelab/src/app/(app)/reels/page.tsx"
      to: "memelab/src/lib/api.ts"
      via: "enhanceReelTheme function call"
      pattern: "enhanceReelTheme"
    - from: "memelab/src/lib/api.ts"
      to: "/reels/enhance-theme"
      via: "POST request"
      pattern: "reels/enhance-theme"
    - from: "src/api/routes/reels.py"
      to: "src/llm_client"
      via: "Gemini API call"
      pattern: "_get_client.*generate_content"
---

<objective>
Add an "Enhance Theme" (Sugerir Temas) button to the reels creation page that generates AI-powered trending topic suggestions using Gemini after the user selects a sub-theme.

Purpose: Help users discover viral/trending video topics within their selected niche+sub-theme instead of having to brainstorm titles manually.
Output: Backend endpoint + frontend API function + button with suggestion pills UI in the reels form.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/api/routes/reels.py (add endpoint — follow ads.py /analyze pattern)
@src/api/routes/ads.py lines 392-429 (Gemini call pattern to replicate)
@memelab/src/lib/api.ts (add API function — follow analyzeProduct pattern at line 1659)
@memelab/src/app/(app)/reels/page.tsx (add button + suggestions UI in GenerationForm)
@memelab/src/components/reels/reel-niches.ts (getNicheById for label lookup)

<interfaces>
<!-- Existing patterns the executor needs -->

From src/api/routes/ads.py (Gemini call pattern):
```python
@router.post("/analyze")
async def analyze_product(req: dict, current_user=Depends(get_current_user)):
    from src.llm_client import _get_client, _extract_text
    client = _get_client()
    resp = await asyncio.to_thread(client.models.generate_content, model="gemini-2.5-flash", contents=prompt)
    text = _extract_text(resp)
    result = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
```

From memelab/src/lib/api.ts (API call pattern):
```typescript
export async function analyzeProduct(productName: string): Promise<AdAnalysisResult> {
  return request<AdAnalysisResult>("/ads/analyze", {
    method: "POST",
    body: JSON.stringify({ product_name: productName }),
  });
}
```

From memelab/src/components/reels/reel-niches.ts:
```typescript
export function getNicheById(id: string): ReelNiche | undefined;
// ReelNiche has: id, label, labelEn, subThemes, hookTemplates, etc.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend endpoint + frontend API function</name>
  <files>src/api/routes/reels.py, memelab/src/lib/api.ts</files>
  <action>
  1. In `src/api/routes/reels.py`, add a new endpoint `POST /enhance-theme` right after the presets section (before the generate endpoint). Follow the exact pattern from `src/api/routes/ads.py` lines 392-429:

  ```python
  @router.post("/enhance-theme")
  async def enhance_theme(req: dict, current_user=Depends(get_current_user)):
  ```

  - Extract `niche_id` (string) and `sub_theme` (string) from `req` dict
  - Validate both are non-empty, raise HTTPException 400 if missing
  - Build a Gemini prompt in PT-BR that asks for 5-8 specific viral/trending video topic titles for the given niche+sub-theme. The prompt should request short hook-style titles (like "3 habitos para ter apos acordar", "5 dicas para ser uma pessoa melhor") and return ONLY valid JSON: `{"suggestions": ["title1", "title2", ...]}`
  - Use `from src.llm_client import _get_client, _extract_text` (same import pattern as ads.py)
  - Call `await asyncio.to_thread(client.models.generate_content, model="gemini-2.5-flash", contents=prompt)`
  - Parse JSON response, strip markdown fences. Return the `{"suggestions": [...]}` dict
  - On exception, log warning and return `{"suggestions": []}` (graceful fallback, same as ads analyze)
  - Add `import asyncio` to imports if not already present

  2. In `memelab/src/lib/api.ts`, add after the `analyzeProduct` function (around line 1664):

  ```typescript
  export async function enhanceReelTheme(nicheId: string, subTheme: string): Promise<{ suggestions: string[] }> {
    return request<{ suggestions: string[] }>("/reels/enhance-theme", {
      method: "POST",
      body: JSON.stringify({ niche_id: nicheId, sub_theme: subTheme }),
    });
  }
  ```
  </action>
  <verify>
    <automated>cd /Users/luigivivian/meme-lab && python -c "from src.api.routes.reels import router; routes = [r.path for r in router.routes]; assert '/enhance-theme' in routes, f'Missing route. Found: {routes}'; print('OK: /enhance-theme route exists')"</automated>
  </verify>
  <done>POST /reels/enhance-theme endpoint exists and returns {suggestions: string[]}. Frontend enhanceReelTheme function exists in api.ts.</done>
</task>

<task type="auto">
  <name>Task 2: Enhance Theme button + suggestion pills in reels page</name>
  <files>memelab/src/app/(app)/reels/page.tsx</files>
  <action>
  In `memelab/src/app/(app)/reels/page.tsx`, modify the `GenerationForm` component:

  1. Add `Sparkles` to the lucide-react import (alongside existing icons).

  2. Add `enhanceReelTheme` to the import from `@/lib/api`.

  3. Add three new state variables inside GenerationForm (after existing state):
     ```typescript
     const [enhancing, setEnhancing] = useState(false);
     const [suggestions, setSuggestions] = useState<string[]>([]);
     const [enhanceError, setEnhanceError] = useState<string | null>(null);
     ```

  4. Add the handler function:
     ```typescript
     async function handleEnhanceTheme() {
       if (!selectedNiche || !selectedSubTheme) return;
       setEnhancing(true);
       setEnhanceError(null);
       setSuggestions([]);
       try {
         const res = await enhanceReelTheme(selectedNiche, selectedSubTheme);
         setSuggestions(res.suggestions ?? []);
       } catch (err) {
         setEnhanceError(err instanceof Error ? err.message : "Erro ao sugerir temas");
       } finally {
         setEnhancing(false);
       }
     }
     ```

  5. Insert UI between the sub-theme pills section (closing `</div>` of the sub-theme IIFE around line 306) and the `<Textarea>` (line 309). The new block:

     ```tsx
     {/* Enhance theme button + suggestions */}
     {selectedSubTheme && (
       <div className="space-y-2">
         <Button
           variant="outline"
           size="sm"
           onClick={handleEnhanceTheme}
           disabled={enhancing}
         >
           {enhancing ? (
             <Loader2 className="mr-2 h-4 w-4 animate-spin" />
           ) : (
             <Sparkles className="mr-2 h-4 w-4" />
           )}
           Sugerir Temas
         </Button>

         {enhanceError && (
           <p className="text-xs text-red-400">{enhanceError}</p>
         )}

         {suggestions.length > 0 && (
           <div className="flex flex-wrap gap-1.5">
             {suggestions.map((s, i) => (
               <button
                 key={i}
                 type="button"
                 onClick={() => setTema(s)}
                 className="px-2.5 py-1 rounded-full text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 hover:bg-purple-500/20 hover:border-purple-500/40 transition-all"
               >
                 {s}
               </button>
             ))}
           </div>
         )}
       </div>
     )}
     ```

  6. Clear suggestions when niche or sub-theme changes: in the niche button onClick (where `setSelectedSubTheme("")` is called), add `setSuggestions([])`. In the sub-theme button onClick, also add `setSuggestions([])`.
  </action>
  <verify>
    <automated>cd /Users/luigivivian/meme-lab/memelab && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Sparkles "Sugerir Temas" button appears when sub-theme is selected. Clicking it calls backend and shows suggestion pills. Clicking a suggestion pill populates the tema textarea. Suggestions clear when niche/sub-theme changes.</done>
</task>

</tasks>

<verification>
1. TypeScript compiles without errors: `cd memelab && npx tsc --noEmit`
2. Backend route exists: `python -c "from src.api.routes.reels import router; print([r.path for r in router.routes])"`
3. Manual: Start both servers, select a niche, select a sub-theme, click "Sugerir Temas", verify pills appear, click a pill and verify tema textarea populates
</verification>

<success_criteria>
- POST /reels/enhance-theme returns {suggestions: string[]} with 5-8 viral topic titles
- "Sugerir Temas" button visible only when sub-theme selected
- Loading spinner during Gemini call
- Suggestion pills clickable and populate tema textarea
- Suggestions clear on niche/sub-theme change
- TypeScript compiles clean
</success_criteria>

<output>
After completion, create `.planning/quick/260330-tgu-add-enhance-theme-button-to-reels-creati/260330-tgu-01-SUMMARY.md`
</output>
