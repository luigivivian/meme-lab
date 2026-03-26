# Notes: Refatoracao pipeline_agents.ipynb

## Arquitetura do Workflow (Skill: Workflow Automation)

### Pattern: Orchestrator-Worker (5 Layers Sequenciais com Paralelismo Interno)

```
L1 MonitoringLayer  ─── asyncio.gather() ──→ [GoogleTrends, Reddit, RSS] (paralelo)
        │
        ▼
L2 TrendBroker      ─── asyncio.Queue ────→ dedup + ranking via TrendAggregator
        │
        ▼
L3 CuratorAgent     ─── asyncio.to_thread ─→ Gemini API (JSON response)
        │
        ▼
L4 GenerationLayer  ─── asyncio.gather() ──→ [PhraseWorker + ImageWorker] (paralelo por order)
        │
        ▼
L5 PostProductionLayer ─ asyncio.gather() ─→ [CaptionWorker, HashtagWorker, QualityWorker] (paralelo)
```

### Semaphores (Rate Limiting)
- `GEMINI_MAX_CONCURRENT = 5` → PhraseWorker, CaptionWorker
- `COMFYUI_MAX_CONCURRENT = 1` → ImageWorker (GPU)

### Durable Execution Gaps
- Nenhum checkpoint entre layers — se L4 falha, precisa re-executar L1-L3
- Notebook layer-by-layer (celulas 8-12) resolve isso parcialmente
- Pipeline completo (celula 13) nao tem recovery

### Data Flow
```
TrendEvent[] → TrendEvent[] (deduped) → WorkOrder[] → ContentPackage[] → ContentPackage[] (enriched)
```

## Problemas de Sintaxe Colab Encontrados

### 1. Celulas code vs markdown
- Notebook atual mistura corretamente markdown e code
- Formato interno usa `<cell_type>markdown</cell_type>` — precisa verificar formato .ipynb real

### 2. Top-level await
- Colab suporta nativamente desde IPython 7.0+
- nest_asyncio necessario apenas se usar asyncio.run() (que nao usamos)
- Mas manter nest_asyncio por seguranca — nao causa problemas

### 3. !pip install vs %pip install
- `!pip install` funciona mas `%pip install` e recomendado pelo Colab
- `%pip install` garante instalacao no kernel correto

### 4. sys.path manipulation
- `sys.path.insert(0, str(PROJECT_DIR))` correto para Colab
- `sys.modules["config"] = config` necessario para evitar conflito

## Modulos do Pipeline (Skill: Agent Development)

### Agents existentes (L1)
| Agent | Fonte | Status |
|-------|-------|--------|
| GoogleTrendsAgent | trendspyg RSS | Funcional |
| RedditMemesAgent | feedparser RSS | Funcional |
| RSSFeedAgent | feedparser | Funcional |
| TikTokTrendsAgent | stub | Nao implementado |
| InstagramExploreAgent | stub | Nao implementado |
| TwitterXAgent | stub | Nao implementado |
| FacebookViralAgent | stub | Nao implementado |
| YouTubeShortsAgent | stub | Nao implementado |

### Workers existentes (L4-L5)
| Worker | Funcao | API |
|--------|--------|-----|
| PhraseWorker | Gera frases | Gemini |
| ImageWorker | Compoe imagem | Pillow (+ComfyUI opcional) |
| CaptionWorker | Legenda Instagram | Gemini |
| HashtagWorker | Hashtags | Local (keyword map) |
| QualityWorker | Validacao imagem | Local (Pillow check) |

## Correcoes Necessarias no Notebook

1. ✅ `!pip install` → `%pip install` (best practice Colab)
2. ✅ Adicionar logging config na celula de setup
3. ✅ Adicionar try/except nas celulas de teste (6-7)
4. ✅ Verificar que `src.image_gen.prompt_builder` importa corretamente
5. ✅ Adicionar celula de reset/cleanup
6. ✅ Melhorar output visual com markdown formatado
7. ✅ Garantir que cada celula tem docstring clara no topo
