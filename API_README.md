# Clip-Flow API — Guia Rapido

**Base URL:** `http://127.0.0.1:8000`
**Swagger:** `http://127.0.0.1:8000/docs`

## Iniciar

```bash
python -m src.api --port 8000
# Com ngrok (Colab):
python -m src.api --port 8000 --ngrok SEU_TOKEN
```

---

## Pipeline (Multi-Agente)

### `POST /pipeline/run` — Executa em background
```json
{
  "count": 5,
  "use_gemini_image": true,
  "use_phrase_context": false
}
```
Retorna `run_id` para consultar status.

### `POST /pipeline/run-sync` — Executa e aguarda
Mesmo body acima, retorna resultado completo.

### `GET /pipeline/status/{run_id}` — Status da execucao

### `GET /pipeline/runs` — Lista todas as execucoes

---

## Frases

### `POST /phrases/generate`
```json
{ "topic": "segunda-feira", "count": 5 }
```

---

## Composicao (Background + Frase = Imagem Final)

### `POST /generate/compose`
```json
{
  "phrase": "O maior feitico e fingir que segunda nao existe",
  "situacao": "sabedoria",
  "use_phrase_context": true
}
```

---

## Geracao de Backgrounds

### `POST /generate/single`
```json
{
  "theme_key": "cafe",
  "auto_refine": false
}
```

### `POST /generate/refine`
```json
{
  "filename": "single_cafe_20260309.png",
  "instrucao": "more dramatic lighting",
  "passes": 2
}
```

---

## Batch (Lote)

### `POST /jobs/batch`
```json
{
  "themes": ["sabedoria", "cafe", {"key": "custom", "acao": "...", "cenario": "...", "count": 2}],
  "pausa": 15,
  "auto_refine": false
}
```

### `POST /jobs/batch/from-config` — Usa themes.yaml

### `GET /jobs/{job_id}` — Status do job

### `GET /jobs` — Lista todos os jobs

---

## Temas

### `GET /themes` — Lista temas disponiveis

### `POST /themes` — Adiciona tema customizado
```json
{
  "key": "taverna_medieval",
  "label": "🍺 Taverna",
  "acao": "wizard drinking ale in medieval tavern",
  "cenario": "warm candlelit medieval tavern, wooden beams"
}
```

### `DELETE /themes/{key}` — Remove tema

### `POST /themes/generate` — Auto-gera temas via IA
```json
{ "count": 5, "categories": ["humor", "fantasia"], "save_to_yaml": true }
```

### `POST /themes/enhance` — Conceito simples → prompt detalhado
```json
{ "input_text": "mago tomando cafe", "save_to_yaml": false }
```

---

## Agentes

### `GET /agents` — Lista agentes e disponibilidade

### `POST /agents/{agent_name}/fetch` — Fetch de um agente
Agentes: `google_trends`, `reddit_memes`, `rss_feeds`

---

## Drive Browser (sub-app em /drive)

### `GET /drive/images` — Lista imagens geradas
Query params: `theme`, `limit`, `offset`

### `GET /drive/images/latest?count=5` — N mais recentes

### `GET /drive/images/by-theme/{theme_key}` — Por tema

### `GET /drive/images/{filename}` — Serve o PNG

### `GET /drive/themes` — Temas nas imagens geradas

### `GET /drive/health` — Status do drive

---

## Status

### `GET /status` — Estado geral do servico
Retorna: API key OK, refs carregadas, imagens geradas, jobs ativos, models.
