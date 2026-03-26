# memeLab

Dashboard React para gerenciar o pipeline multi-agente clip-flow de memes "O Mago Mestre".

## Stack

- **Next.js 15** (App Router) + **React 19** + **TypeScript 5.8**
- **Tailwind CSS 4** — via `@tailwindcss/postcss`, sem tailwind.config (usa `@theme` em globals.css)
- **shadcn/ui pattern** — Radix UI + CVA + tailwind-merge + clsx (componentes em `src/components/ui/`)
- **SWR** — data fetching com revalidacao automatica
- **SVG interativo** — diagrama do pipeline com drag, zoom, pan e sub-nós (substituiu Mermaid.js)
- **Lucide React** — icones

## Como Executar

```bash
cd memelab
npm install
npm run dev    # porta 3000
```

Requer o backend FastAPI rodando em `localhost:8000` (a API e proxied via Next.js rewrites).

## Arquitetura

### Proxy API

Todas as chamadas frontend vao para `/api/*` que o Next.js rewrite redireciona para `http://127.0.0.1:8000/*`. Nao ha rotas API no Next.js — tudo e proxy para o FastAPI.

### Estrutura de Arquivos

```
memelab/
  src/
    app/
      layout.tsx              # Root layout (dark mode, Inter font, Shell wrapper)
      page.tsx                # Redirect / → /dashboard
      globals.css             # Tailwind 4 @theme com design tokens
      dashboard/page.tsx      # Stats + imagens recentes + status
      agents/page.tsx         # Grid de agentes + fetch dialog
      pipeline/page.tsx       # Controles + diagrama Mermaid + historico
      gallery/page.tsx        # Grid de imagens + filtro tema + compose dialog
      phrases/page.tsx        # Gerar frases por tema (Suspense para useSearchParams)
      trends/page.tsx         # Trending topics com tabs por fonte
    components/
      layout/
        shell.tsx             # Sidebar + Header + content area
        sidebar.tsx           # Navegacao lateral
        header.tsx            # Status da API + contadores
      panels/
        stats-card.tsx        # Card de estatistica reutilizavel
        pipeline-diagram.tsx  # Diagrama SVG interativo — drag/zoom/pan, nos principais + sub-nos por layer
      ui/                     # 11 componentes shadcn/ui (button, card, dialog, etc.)
    hooks/
      use-api.ts              # SWR hooks tipados (useStatus, useAgents, useDriveImages, etc.)
      use-pipeline.ts         # Hook de execucao do pipeline com polling
    lib/
      api.ts                  # Client HTTP tipado — 15 interfaces + todas as funcoes de API
      constants.ts            # NAV_ITEMS, AGENT_TYPE_COLORS, STATUS_COLORS
      utils.ts                # cn() helper (clsx + tailwind-merge)
```

### Tipos da API (CRITICO)

Os tipos em `src/lib/api.ts` espelham EXATAMENTE as respostas do FastAPI. Cuidado ao modificar:

- `GET /agents` → retorna `AgentInfo[]` (array plano, NAO `{agents:[...]}`)
- `GET /drive/images` → retorna `{total, offset, limit, images: ImageInfo[]}` (NAO array plano)
- `GET /drive/images/latest` → retorna `{count, images: ImageInfo[]}` (NAO array plano)
- `GET /drive/themes` → retorna `{themes: string[], counts: Record<string,number>}`
- `GET /pipeline/runs` → retorna `Record<string, {status, packages}>` (dict, NAO array)
- `POST /generate/compose` → `image_path` e caminho absoluto — extrair filename para URL
- `POST /themes/enhance` → corpo usa `input_text`, NAO `concept`
- `GET /drive/images/{filename}` → FileResponse servindo PNG (usado por `imageUrl()`)

### Design Tokens (globals.css)

- Primary: `#7C3AED` (roxo)
- Background: `#09090b`, Cards: `#1c1c22`
- Radius: `12px`
- Font: Inter

## Convencoes

- Todos os componentes sao `"use client"` (SWR + interatividade)
- `useSearchParams()` requer `<Suspense>` boundary (Next.js 15)
- SWR cache keys sao strings deterministicas (nao `JSON.stringify`)
- Imagens carregam via `imageUrl(filename)` que gera `/api/drive/images/{filename}`
- Navegacao entre paginas via `router.push()` (nao `window.location.href`)
- UI em portugues brasileiro

## Paginas

| Rota | Funcao |
|------|--------|
| `/dashboard` | Stats gerais, imagens recentes, status do pipeline |
| `/agents` | Lista agentes, fetch individual com resultado em dialog |
| `/pipeline` | Executar pipeline, diagrama SVG interativo (L1-L5 + sub-nos), historico de runs |
| `/gallery` | Grid de imagens com filtro por tema, preview, compose meme |
| `/phrases` | Gerar frases por tema (aceita `?topic=` da pagina de trends) |
| `/trends` | Trending topics com tabs: Todos/Google/Reddit/RSS |

## Pipeline Diagram (pipeline-diagram.tsx)

Diagrama SVG puro (sem React Flow ou Mermaid), renderizado em `panels/pipeline-diagram.tsx`.

**Interacoes:** scroll to zoom (non-passive wheel), drag nos, click to inspect (side panel deslizante).

**Layout:**
- 5 nos principais (L1-L5) em linha horizontal com stagger Y leve
- No `output` ao final da cadeia
- Sub-nos abaixo de cada layer mostrando workers/agents individuais
- Edges S-curve com gradient, orbs animados e dash flow em running

**Sub-nos por layer:**
- L1 Monitoring: 6 agents ativos + 3 stubs (TikTok, Instagram, Twitter)
- L2 Broker: Ingest Queue → Dedup Filter → Rank & Sort (sequential)
- L3 Curator: Gemini Analyzer → Keyword Map → WorkOrders (sequential)
- L4 Generation: PhraseWorker + ImageWorker (parallel)
- L5 Post-Prod: CaptionWorker + HashtagWorker + QualityWorker (parallel)

**Status herdado:** sub-nos herdam status do no pai (pulse em running, checkmark em done, stubs sempre dimados).

**Tecnico:**
- `animateTransform` SVG para rotacao (evita issues de transformOrigin no SVG)
- `{ passive: false }` no wheel listener para zoom funcionar
- Capture `dragging.current` em variavel local antes de `setNodes` (evita race condition com null)
- Sub-nos sao posicoes computadas do pai — seguem automaticamente no drag sem estado extra
