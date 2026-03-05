# Mago Mestre — Gerador de Imagens Consistentes

Notebook Jupyter/Colab para geração de imagens do personagem **O Mago Mestre** usando Google Gemini com referências visuais.

## Arquivo principal

- [mago_mestre_generator.ipynb](mago_mestre_generator.ipynb) — notebook completo (11 células funcionais)

## Stack

- `google-genai` (SDK oficial Google)
- `Pillow` (PIL) para manipulação de imagens
- `tqdm` para progresso em lote
- Ambiente: Google Colab (primário) ou Jupyter local

## Modelos Gemini (ordem de prioridade)

```python
MODELOS_IMAGEM = [
    "gemini-2.5-flash-image",                 # produção, estável
    "gemini-2.0-flash-exp-image-generation",  # experimental, rápido
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
]
```

**Modelos disponíveis na API (confirmados):**
- `models/gemini-2.0-flash-exp-image-generation`
- `models/gemini-2.5-flash-image`
- `models/gemini-3-pro-image-preview`
- `models/gemini-3.1-flash-image-preview`
- `models/imagen-4.0-generate-001`
- `models/imagen-4.0-ultra-generate-001`
- `models/imagen-4.0-fast-generate-001`

**DEPRECIADO — não usar:** `gemini-2.0-flash-lite` (retorna 404)

## Configurações padrão

| Parâmetro | Valor | Notas |
|-----------|-------|-------|
| `TEMPERATURA` | `0.85` | criatividade (0.0–2.0) |
| `N_REFERENCIAS` | `5` | imagens de referência por geração (recomendado 3–7, máx 14) |
| `RESOLUCAO_MAX_REF` | `1024` | limite de redimensionamento das refs |
| `MAX_TENTATIVAS_429` | `2` | retries ao receber rate limit |
| `ESPERA_BASE_429` | `60s` | base de espera (dobra a cada tentativa) |
| Aspect ratio | `4:5` | 1080×1350px vertical |

## Diretórios

```
assets/backgrounds/mago/   ← imagens de referência do personagem
generated_mago/            ← saída das imagens geradas
```

**Google Drive (Colab):**
```
/content/drive/MyDrive/clip-flow/assets/backgrounds/mago   ← refs no Drive
/content/drive/MyDrive/clip-flow/output/mago_gerado        ← saída no Drive
```

## API Key

- No Colab: configurar em **Secrets** (ícone 🔑) como `GOOGLE_API_KEY`
- Local: `export GOOGLE_API_KEY='sua-chave'`
- Cliente: `genai.Client(api_key=GOOGLE_API_KEY)`

## Fluxo das células

| Célula | Função |
|--------|--------|
| 1 | Setup e dependências, carrega API key |
| 2 | Carrega imagens de referência (local / Drive / upload) |
| 3 | Define `CHARACTER_DNA`, `COMPOSITION`, `NEGATIVE_TRAITS`, 13 situações em `SITUACOES` |
| 4 | Configura cliente Gemini e funções de geração (`gerar_imagem`, `_tentar_gerar`) |
| 5 | Geração individual — configurar `SITUACAO` e executar |
| 6 | Geração em lote — lista `LOTE`, configura `N_REFS_LOTE` e `PAUSA_SEGUNDOS` |
| 7 | Refinamento img2img — usa imagem gerada como nova referência |
| 8 | Preview grid de todas as imagens geradas |
| 9 | Download como ZIP, para Drive, ou individual |
| 10 | Copia aprovadas para `assets/backgrounds/mago/` |
| 11 | Diagnóstico: `resumo_estado()`, `testar_api()`, `listar_modelos_imagem()` |

## 13 situações pré-definidas

`sabedoria` | `confusao` | `segunda_feira` | `vitoria` | `tecnologia` |
`cafe` | `comida` | `trabalho` | `relaxando` | `meditando` |
`relacionamento` | `confronto` | `surpresa` | `custom`

Para situação livre: `SITUACAO = "custom"` + preencher `ACAO_CUSTOM` e `CENARIO_CUSTOM` em inglês.

## DNA do personagem (traços imutáveis)

Definido em `CHARACTER_DNA` (célula 3). Pontos críticos:
- Barba: longa, branca/prateada, ondulada até o peito
- Chapéu: pontudo, azul-cinza (`#4A5568`), nunca remover
- Robe: azul midnight escuro (`#1A1A3E`) com bordados dourados
- Cajado: madeira escura com ponta brilhante dourada (`#FFD54F`)
- Estilo: cartoon semi-realista, cel-shading suave
- Composição: vertical 4:5, personagem no terço inferior, topo 35–40% livre para texto

## Limites e cotas

- **Cota gratuita:** ~15 imagens/dia (Google AI Studio)
- **Reset:** meia-noite UTC
- **429 RESOURCE_EXHAUSTED:** aguarda `ESPERA_BASE_429`s e tenta próximo modelo
- **404 NOT_FOUND:** passa imediatamente ao próximo modelo
- Para cota maior: ativar billing no Google AI Studio

## Pipeline integration

Após aprovar imagens, copiar para assets via **Célula 10** e rodar:
```bash
python -m src.pipeline_cli --mode once
```

## Diagnóstico rápido

```python
resumo_estado()        # status geral
testar_api()           # testa conectividade
listar_modelos_imagem()  # modelos disponíveis na sua API key
```
