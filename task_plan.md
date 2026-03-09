# Task Plan: Refatorar pipeline_agents.ipynb para Google Colab

## Goal
Refatorar o notebook pipeline_agents.ipynb com sintaxe 100% correta para Google Colab, usando as skills Workflow Automation, Planning with Files e Agent Development.

## Phases
- [x] Phase 1: Analise completa do notebook atual e dependencias
- [x] Phase 2: Mapear problemas de sintaxe e arquitetura (Workflow Automation)
- [x] Phase 3: Refatorar notebook celula por celula (14 celulas refatoradas)
- [x] Phase 4: Revisar e entregar fluxo completo explicado

## Problemas Identificados

### P1: Import `image_gen.prompt_builder` no Colab
- `curator.py` importa `from src.image_gen.prompt_builder import KEYWORD_MAP`
- No Colab, `image_gen/` pode nao existir se o repo nao tiver ComfyUI
- **Solucao**: Notebook precisa de fallback ou garantir que o modulo existe

### P2: Celulas sem tratamento de erro robusto
- Celulas 6-7 (testes rapidos) falham silenciosamente se API key ausente
- Celula 8 (L1) nao tem timeout explicito
- **Solucao**: Adicionar try/except e mensagens claras

### P3: Variavel `frases` entre celulas 6 e 7
- Celula 7 depende de `frases` da celula 6
- Se celula 6 falhar, celula 7 quebra sem mensagem util
- **Solucao**: Fallback com frase padrao ja existe mas precisa review

### P4: Duplicacao de imports IPython.display
- `IPyImage` e `display` importados em celulas 7, 11 e 14
- **Solucao**: Mover para celula de setup ou manter (aceitavel em notebooks)

### P5: Config import via importlib
- Celula 4 usa `importlib.util.spec_from_file_location` para evitar conflito
- Correto para Colab — manter

### P6: Falta celula de cleanup/reset
- Nao ha celula para limpar output/ entre execucoes
- **Solucao**: Adicionar celula opcional

### P7: nest_asyncio ja aplicado mas await top-level
- Colab suporta `await` top-level nativamente desde 2023
- nest_asyncio ainda necessario para asyncio.run() dentro de event loop existente
- **Solucao**: Manter nest_asyncio, esta correto

### P8: Logging duplicado
- Celula 13 configura logging com `force=True` mas celulas anteriores nao
- Logs podem aparecer duplicados
- **Solucao**: Mover config de logging para celula de setup

## Decisions Made
- Manter google-genai como LLM provider (ja migrado de Anthropic)
- Manter nest_asyncio (necessario para Colab)
- Manter importlib hack para config.py (evita conflito com modulo builtin)
- Adicionar celula de logging no setup
- Adicionar tratamento de erro em todas as celulas de execucao

## Status
**CONCLUIDO** — Todas as 4 fases completadas com sucesso.
