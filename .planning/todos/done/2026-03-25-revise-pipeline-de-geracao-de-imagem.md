---
created: 2026-03-25T17:07:48.201Z
title: Revise pipeline de geracao de imagem
area: general
files:
  - src/image_gen/gemini_client.py
  - src/pipeline/async_orchestrator.py
  - src/pipeline/workers/image_worker.py
---

## Problem

A pipeline de geração de imagem não está funcionando. Os logs indicam que 20 imagens de referência estão sendo carregadas, o que excede o limite da API. Além disso:

1. **Limite de referências excedido**: O log reporta 20 imagens carregadas — precisa ser limitado (máx configurado é 14, ideal ~3).
2. **Sem log de payload**: As requisições ao Google/Gemini não estão sendo logadas com o payload enviado, dificultando debug.
3. **Tokens de input não estimados**: A quantidade de tokens do input não está sendo estimada nem otimizada antes do envio.
4. **Separação de outputs ausente**: Memes (com frase) e backgrounds (sem frase) precisam ser salvos em pastas separadas para que backgrounds possam ser reutilizados com frases diferentes.
5. **Frases no background**: O Gemini está gerando texto/frases renderizados no background — precisa garantir que backgrounds sejam gerados sem texto.

## Solution

1. Auditar `src/image_gen/gemini_client.py` — verificar onde as referências são carregadas e aplicar limite rígido (≤3 por padrão, configurável).
2. Adicionar logging detalhado do payload enviado ao Google (número de refs, tamanho estimado em tokens, situação/prompt).
3. Implementar estimativa de tokens de input antes do envio (baseada em tamanho das imagens em base64 + texto do prompt).
4. Separar saída em dois diretórios:
   - `generated_mago/backgrounds/` — imagens sem texto (geradas com NEGATIVE_TRAITS explícito "NO TEXT, NO LETTERS")
   - `generated_mago/memes/` — composição final com frase sobreposta pelo Pillow
5. Garantir que NEGATIVE_TRAITS sempre inclua proibição de texto/letras na imagem gerada.
