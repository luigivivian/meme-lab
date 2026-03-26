graph TD
    subgraph API["REST API (FastAPI + ngrok)"]
        direction LR
        EP1["POST /generate/single"]
        EP2["POST /generate/refine"]
        EP3["POST /generate/compose"]
        EP4["POST /jobs/batch"]
        EP5["POST /themes/generate"]
        EP6["POST /themes/enhance"]
        EP7["POST /pipeline/run"]
        EP8["POST /phrases/generate"]
        EP9["POST /agents/{name}/fetch"]
        EP10["GET /drive/images"]
    end

    subgraph NANO["NANO BANANA PIPELINE"]
        GEN["Gemini Image API\n(referencias visuais)"]
        REF["Refinamento Iterativo\n(N passes, temp=0.4)"]
        GEN -->|"v0"| REF
        REF -->|"v1..vN"| FINAL["Imagem Final"]
    end

    subgraph L1["LAYER 1: MONITORAMENTO (paralelo)"]
        GT["GoogleTrendsAgent"]
        RD["RedditMemesAgent"]
        RSS["RSSFeedAgent"]
        TK["TikTokAgent (stub)"]
        IG["InstagramAgent (stub)"]
        TW["TwitterXAgent (stub)"]
        FB["FacebookAgent (stub)"]
        YT["YouTubeAgent (stub)"]
    end

    subgraph L2["LAYER 2: TREND BROKER"]
        BRK["TrendBroker\nasyncio.Queue + TrendAggregator\ndedup + boost multi-fonte"]
    end

    subgraph L3["LAYER 3: CURATOR AGENT"]
        CUR["CuratorAgent\nGemini API -> WorkOrders\ntema -> situacao_key + humor_angle"]
    end

    subgraph L4["LAYER 4: GERACAO (paralelo)"]
        PW["PhraseWorker\nGemini API"]
        subgraph IMGGEN["Background Generation (cascata)"]
            GI["1. Gemini Image API"]
            CI["2. ComfyUI Local\n(Flux + LoRA)"]
            SI["3. Static Backgrounds"]
        end
        CMP["Composer\nPillow 1080x1350"]
    end

    subgraph L5["LAYER 5: POS-PRODUCAO (paralelo)"]
        CAP["CaptionWorker\nlegenda IG + CTA"]
        HSH["HashtagWorker\n20 hashtags"]
        QUA["QualityWorker\nvalidacao imagem"]
    end

    subgraph L6["OUTPUT"]
        PKG["ContentPackage\nimagem + frase + legenda\nhashtags + quality_score"]
        DRV["Drive Browser API\n/drive/images"]
    end

    EP1 & EP2 & EP3 & EP4 --> NANO
    EP5 & EP6 -->|"AI gera temas"| NANO
    EP7 --> L1
    EP8 --> PW
    EP9 --> GT & RD & RSS
    EP10 --> DRV

    GT & RD & RSS & TK & IG & TW & FB & YT -->|"list[TrendEvent]"| BRK
    BRK -->|"ranked events"| CUR
    CUR -->|"list[WorkOrder]"| PW & IMGGEN
    GI -->|"fallback"| CI
    CI -->|"fallback"| SI
    PW & IMGGEN --> CMP
    CMP -->|"list[ContentPackage]"| CAP & HSH & QUA
    CAP & HSH & QUA --> PKG
    PKG --> DRV

    style EP1 fill:#0d9488,color:#fff
    style EP2 fill:#0d9488,color:#fff
    style EP3 fill:#0d9488,color:#fff
    style EP4 fill:#0d9488,color:#fff
    style EP5 fill:#0d9488,color:#fff
    style EP6 fill:#0d9488,color:#fff
    style EP7 fill:#0d9488,color:#fff
    style EP8 fill:#0d9488,color:#fff
    style EP9 fill:#0d9488,color:#fff
    style EP10 fill:#0d9488,color:#fff
    style GEN fill:#059669,color:#fff
    style REF fill:#047857,color:#fff
    style FINAL fill:#065f46,color:#fff
    style GT fill:#2d6a4f,color:#fff
    style RD fill:#2d6a4f,color:#fff
    style RSS fill:#2d6a4f,color:#fff
    style TK fill:#495057,color:#adb5bd
    style IG fill:#495057,color:#adb5bd
    style TW fill:#495057,color:#adb5bd
    style FB fill:#495057,color:#adb5bd
    style YT fill:#495057,color:#adb5bd
    style BRK fill:#1a535c,color:#fff
    style CUR fill:#6a040f,color:#fff
    style PW fill:#7b2cbf,color:#fff
    style GI fill:#059669,color:#fff
    style CI fill:#7b2cbf,color:#fff
    style SI fill:#495057,color:#adb5bd
    style CMP fill:#7b2cbf,color:#fff
    style CAP fill:#e85d04,color:#fff
    style HSH fill:#e85d04,color:#fff
    style QUA fill:#e85d04,color:#fff
    style PKG fill:#023e8a,color:#fff
    style DRV fill:#023e8a,color:#fff
