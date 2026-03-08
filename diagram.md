graph TD
    subgraph L1["LAYER 1: MONITORAMENTO (paralelo)"]
        GT["GoogleTrendsAgent ✓"]
        RD["RedditMemesAgent ✓"]
        RSS["RSSFeedAgent ✓"]
        TK["TikTokTrendsAgent (stub)"]
        IG["InstagramExploreAgent (stub)"]
        TW["TwitterXAgent (stub)"]
        FB["FacebookViralAgent (stub)"]
        YT["YouTubeShortsAgent (stub)"]
    end

    subgraph L2["LAYER 2: TREND BROKER"]
        BRK["TrendBroker\nasyncio.Queue + TrendAggregator\ndedup + boost multi-fonte"]
    end

    subgraph L3["LAYER 3: CURATOR AGENT"]
        CUR["CuratorAgent\nClaude API → WorkOrders\ntema → situacao_key + humor_angle"]
    end

    subgraph L4["LAYER 4: GERACAO (paralelo)"]
        PW["PhraseWorker\nClaude API"]
        IW["ImageWorker\nGemini/ComfyUI\nSemaphore(1) GPU"]
        CMP["Composer\nPillow 1080x1350"]
    end

    subgraph L5["LAYER 5: POS-PRODUCAO (paralelo)"]
        CAP["CaptionWorker\nlegenda IG + CTA"]
        HSH["HashtagWorker\n20 hashtags"]
        QUA["QualityWorker\nvalidacao imagem"]
    end

    subgraph L6["OUTPUT"]
        PKG["ContentPackage\nimagem + frase + legenda\nhashtags + metadados + quality_score"]
        PUB["PublisherAgent\n(futuro)"]
    end

    GT & RD & RSS & TK & IG & TW & FB & YT -->|"list[TrendEvent]"| BRK
    BRK -->|"ranked events"| CUR
    CUR -->|"list[WorkOrder]"| PW & IW
    PW & IW --> CMP
    CMP -->|"list[ContentPackage]"| CAP & HSH & QUA
    CAP & HSH & QUA --> PKG
    PKG -.-> PUB

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
    style IW fill:#7b2cbf,color:#fff
    style CMP fill:#7b2cbf,color:#fff
    style CAP fill:#e85d04,color:#fff
    style HSH fill:#e85d04,color:#fff
    style QUA fill:#e85d04,color:#fff
    style PKG fill:#023e8a,color:#fff
    style PUB fill:#495057,color:#adb5bd
