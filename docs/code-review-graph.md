# Clip-Flow — Code Review Graph

## 1. Pipeline Architecture (5 Layers)

```mermaid
flowchart TB
    subgraph L1["L1 — MONITORING (Parallel Fetch)"]
        direction LR
        GT["GoogleTrends<br/><small>sync/SyncAdapter</small>"]
        RM["RedditMemes<br/><small>sync/SyncAdapter</small>"]
        RSS["RSSFeeds<br/><small>sync/SyncAdapter</small>"]
        YT["YouTubeRSS<br/><small>async</small>"]
        GWT["GeminiWebTrends<br/><small>async+grounding</small>"]
        BVR["BrazilViralRSS<br/><small>async</small>"]
        BS["BlueSky<br/><small>async</small>"]
        HN["HackerNews<br/><small>async</small>"]
        LM["Lemmy<br/><small>async</small>"]
        STUBS["TikTok / IG / X<br/><small>stubs</small>"]
    end

    subgraph L2["L2 — BROKER (Dedup + Rank)"]
        INGEST["Ingest Events"]
        AGG["TrendAggregator<br/><small>dedup + boost multi-source</small>"]
        QUEUE["asyncio.Queue<br/><small>max=1000</small>"]
        INGEST --> AGG --> QUEUE
    end

    subgraph L3["L3 — CURATOR (Selection)"]
        ANALYZER["ClaudeAnalyzer<br/><small>Gemini selects best</small>"]
        KWMAP["KEYWORD_MAP<br/><small>tema → situacao_key</small>"]
        DEDUP7["Cross-Run Dedup<br/><small>7-day window</small>"]
        WO["WorkOrder[]<br/><small>+layout +carousel</small>"]
        ANALYZER --> KWMAP --> DEDUP7 --> WO
    end

    subgraph L4["L4 — GENERATION (Parallel per WorkOrder)"]
        direction LR
        subgraph PW["PhraseWorker"]
            PHRASE["generate_phrases()<br/><small>Gemini tier=lite</small>"]
            AB["A/B Scoring<br/><small>viralidade+humor+id</small>"]
        end
        subgraph IW["ImageWorker"]
            GEMIMG["GeminiImage<br/><small>sem=5, refs+DNA</small>"]
            COMFY["ComfyUI<br/><small>sem=1, GPU</small>"]
            STATIC["Static BGs"]
            COMPOSE["Pillow Compose<br/><small>overlay→vignette→glow→text→wm</small>"]
            GEMIMG --> COMPOSE
            COMFY --> COMPOSE
            STATIC --> COMPOSE
        end
    end

    subgraph L5["L5 — POST-PRODUCTION (Parallel)"]
        direction LR
        CAP["CaptionWorker<br/><small>Instagram CTA</small>"]
        HASH["HashtagWorker<br/><small>trending+branded</small>"]
        QUAL["QualityWorker<br/><small>scoring</small>"]
    end

    OUT["ContentPackage[]<br/><small>phrase + image + caption + hashtags + score</small>"]
    DB[(MySQL<br/><small>pipeline_runs + content_packages</small>)]

    L1 -->|"~227+ TrendEvents"| L2
    L2 -->|"deduplicated events"| L3
    L3 -->|"WorkOrder[] (count=5)"| L4
    L4 -->|"ContentPackage[]"| L5
    L5 --> OUT --> DB
```

## 2. Module Dependency Graph

```mermaid
flowchart LR
    subgraph API["src/api/"]
        APP["app.py"]
        DEPS["deps.py"]
        MODELS_API["models.py"]
        SER["serializers.py"]
        subgraph ROUTES["routes/"]
            R_PIPE["pipeline.py"]
            R_GEN["generation.py"]
            R_THEME["themes.py"]
            R_CHAR["characters.py"]
            R_CONT["content.py"]
            R_AGENT["agents.py"]
            R_DRIVE["drive.py"]
            R_JOBS["jobs.py"]
            R_PUB["publishing.py"]
        end
    end

    subgraph PIPE["src/pipeline/"]
        ORCH["async_orchestrator.py"]
        MON["monitoring.py"]
        BROKER["broker.py"]
        CURATOR["curator.py"]
        M_V2["models_v2.py"]
        subgraph AGENTS["agents/"]
            ABASE["async_base.py"]
            A_GT["google_trends"]
            A_RD["reddit_memes"]
            A_RSS["rss_feeds"]
            A_YT["youtube_rss"]
            A_GEM["gemini_web"]
            A_BVR["brazil_viral"]
            A_BS["bluesky"]
            A_HN["hackernews"]
            A_LM["lemmy"]
        end
        subgraph PROC["processors/"]
            P_AGG["aggregator"]
            P_ANA["analyzer"]
            P_GEN["generator"]
        end
        subgraph WORK["workers/"]
            W_PHR["phrase_worker"]
            W_IMG["image_worker"]
            W_CAP["caption_worker"]
            W_HSH["hashtag_worker"]
            W_QUA["quality_worker"]
            W_GENL["generation_layer"]
            W_POST["post_production"]
        end
    end

    subgraph IMGEN["src/image_gen/"]
        GCLI["gemini_client.py"]
        PBLD["prompt_builder.py"]
        CCLI["comfyui_client.py"]
    end

    subgraph DBASE["src/database/"]
        SESS["session.py"]
        DB_MOD["models.py"]
        CONV["converters.py"]
        SEED["seed.py"]
        subgraph REPO["repositories/"]
            RP_CHAR["character_repo"]
            RP_THEME["theme_repo"]
            RP_PIPE["pipeline_repo"]
            RP_CONT["content_repo"]
            RP_JOB["job_repo"]
            RP_SCHED["schedule_repo"]
        end
    end

    subgraph CORE["src/ (core)"]
        LLM["llm_client.py"]
        PHR["phrases.py"]
        IMGM["image_maker.py"]
        CHARS["characters.py"]
        CFG["config.py"]
    end

    subgraph SVC["src/services/"]
        PUB["publisher.py"]
        IG_CLI["instagram_client.py"]
        INSIGHTS["insights_collector.py"]
        SCHED_W["scheduler_worker.py"]
    end

    %% API dependencies
    APP --> ROUTES
    APP --> SESS
    APP --> SCHED_W
    R_PIPE --> ORCH
    R_PIPE --> RP_PIPE
    R_PIPE --> RP_CONT
    R_PIPE --> RP_CHAR
    R_PIPE --> CONV
    R_PIPE --> CHARS
    R_GEN --> GCLI
    R_GEN --> IMGM
    R_THEME --> RP_THEME
    R_CHAR --> RP_CHAR
    R_CONT --> RP_CONT
    R_PUB --> RP_SCHED
    R_JOBS --> RP_JOB

    %% Pipeline core
    ORCH --> MON
    ORCH --> BROKER
    ORCH --> CURATOR
    ORCH --> W_GENL
    ORCH --> W_POST
    ORCH --> ABASE
    ORCH --> M_V2

    MON --> ABASE
    BROKER --> P_AGG
    BROKER --> M_V2
    CURATOR --> P_ANA
    CURATOR --> PBLD
    CURATOR --> GCLI

    %% Workers
    W_GENL --> W_PHR
    W_GENL --> W_IMG
    W_POST --> W_CAP
    W_POST --> W_HSH
    W_POST --> W_QUA
    W_PHR --> LLM
    W_IMG --> GCLI
    W_IMG --> IMGM
    W_IMG --> P_GEN
    W_CAP --> LLM

    %% Image gen
    GCLI --> PBLD
    GCLI --> LLM

    %% Core
    PHR --> LLM
    LLM --> CFG

    %% Database
    REPO --> DB_MOD
    DB_MOD --> SESS

    %% Services
    PUB --> RP_SCHED
    PUB --> RP_CONT
```

## 3. Database ER Diagram

```mermaid
erDiagram
    Character ||--o{ CharacterRef : "has refs"
    Character ||--o{ Theme : "has themes"
    Character ||--o{ PipelineRun : "runs"
    Character ||--o{ ContentPackage : "produces"
    Character ||--o{ GeneratedImage : "generates"
    Character ||--o{ BatchJob : "batches"
    Character ||--o{ ScheduledPost : "schedules"

    PipelineRun ||--o{ WorkOrder : "emits"
    PipelineRun ||--o{ ContentPackage : "produces"
    PipelineRun ||--o{ AgentStats : "tracks"

    TrendEventDB ||--o{ WorkOrder : "sourced by"
    ContentPackage ||--o| GeneratedImage : "has image"
    ContentPackage ||--o{ ScheduledPost : "scheduled as"

    Character {
        int id PK
        string slug UK
        string name
        string handle
        string watermark
        enum status "draft|refining|ready"
        text system_prompt
        text character_dna
        text negative_traits
        json rendering
        json style
        int refs_min_approved
    }

    CharacterRef {
        int id PK
        int character_id FK
        string filename
        enum status "pending|approved|rejected"
        string file_path
        enum source "generated|uploaded"
    }

    Theme {
        int id PK
        int character_id FK
        string key
        string label
        string acao
        string cenario
        bool is_builtin
    }

    PipelineRun {
        int id PK
        int character_id FK
        datetime started_at
        enum status "running|completed|failed"
        int trends_fetched
        int work_orders
        int images_generated
    }

    TrendEventDB {
        int id PK
        string title
        string source
        float score
        string dedup_hash UK
        datetime fetched_at
    }

    WorkOrder {
        int id PK
        int pipeline_run_id FK
        int trend_event_id FK
        string gandalf_topic
        string humor_angle
        string situacao_key
        float relevance_score
    }

    ContentPackage {
        int id PK
        int character_id FK
        int pipeline_run_id FK
        text phrase
        string image_path
        text caption
        json hashtags
        float quality_score
        string background_source
    }

    GeneratedImage {
        int id PK
        int character_id FK
        int content_package_id FK
        string filename
        string background_source
        int generation_time_ms
    }

    BatchJob {
        int id PK
        int character_id FK
        enum status "queued|running|completed|failed"
        int total_items
        int completed_items
    }

    ScheduledPost {
        int id PK
        int content_package_id FK
        int character_id FK
        enum platform "instagram|tiktok|twitter"
        datetime scheduled_at
        enum status "queued|published|failed"
        int retry_count
    }

    AgentStats {
        int id PK
        int pipeline_run_id FK
        string agent_name
        int events_fetched
        int execution_time_ms
        enum status "success|error"
    }
```

## 4. API Route Map

```mermaid
flowchart LR
    subgraph FastAPI["FastAPI :8000"]
        direction TB
        subgraph GEN["/generate"]
            G1["POST /single"]
            G2["POST /refine"]
            G3["POST /batch"]
            G4["GET /backgrounds"]
        end
        subgraph JOBS["/jobs"]
            J1["GET /"]
            J2["GET /{id}"]
            J3["DELETE /{id}"]
        end
        subgraph THEMES["/themes"]
            T1["GET /"]
            T2["POST /generate"]
            T3["POST /enhance"]
            T4["POST /save"]
        end
        subgraph PIPELINE["/pipeline"]
            P1["POST /run"]
            P2["GET /runs"]
            P3["GET /runs/{id}"]
            P4["GET /layers/{id}<br/><small>WebSocket</small>"]
        end
        subgraph CONTENT["/content"]
            C1["GET /content"]
            C2["GET /images"]
            C3["POST /phrases/generate"]
        end
        subgraph AGENTS["/agents"]
            A1["GET /agents"]
            A2["GET /agents/{name}"]
            A3["GET /trends"]
        end
        subgraph DRIVE["/drive"]
            D1["GET /drive"]
            D2["GET /drive/{path}"]
            D3["GET /drive/image/{fn}"]
            D4["GET /status"]
        end
        subgraph CHARS["/characters"]
            CH1["GET /"]
            CH2["POST /"]
            CH3["GET /{slug}"]
            CH4["PATCH /{slug}"]
            CH5["DELETE /{slug}"]
            CH6["GET /{slug}/refs"]
            CH7["POST /{slug}/refs/generate"]
            CH8["PATCH /{slug}/refs/{id}"]
        end
        subgraph PUB["/publishing"]
            PB1["POST /schedule"]
            PB2["GET /queue"]
            PB3["PATCH /{id}/status"]
            PB4["DELETE /{id}"]
        end
    end
```

## 5. Concurrency & Semaphore Map

```mermaid
flowchart TB
    subgraph SEM["Semaphores"]
        S1["Gemini API<br/>Semaphore(5)"]
        S2["GPU/ComfyUI<br/>Semaphore(1)"]
        S3["Gemini Image<br/>Semaphore(5)"]
    end

    subgraph CONSUMERS["Consumers"]
        PW["PhraseWorker.generate()"]
        CW["CaptionWorker.generate()"]
        IW_G["ImageWorker → GeminiImage"]
        IW_C["ImageWorker → ComfyUI"]
        LLM["llm_client.agenerate()"]
    end

    S1 -.->|"shared"| PW
    S1 -.->|"shared"| CW
    S1 -.->|"shared"| LLM
    S3 -.->|"image gen"| IW_G
    S2 -.->|"GPU exclusive"| IW_C

    subgraph FALLBACK["Image Backend Priority"]
        direction LR
        F1["gemini"] -->|"fail"| F2["comfyui"] -->|"fail"| F3["static"]
    end
```

## 6. Data Flow: Pipeline Run

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Orch as AsyncOrchestrator
    participant L1 as MonitoringLayer
    participant L2 as TrendBroker
    participant L3 as CuratorAgent
    participant L4 as GenerationLayer
    participant L5 as PostProduction
    participant DB as MySQL
    participant Gemini as Gemini API

    Client->>API: POST /pipeline/run
    API->>DB: create PipelineRun (status=running)
    API->>Orch: run() [background task]

    rect rgb(230, 245, 255)
        Note over L1: L1 — Parallel Agent Fetch
        Orch->>L1: fetch_all(9 agents)
        L1-->>Orch: ~227+ TrendEvents
    end

    rect rgb(255, 245, 230)
        Note over L2: L2 — Dedup + Rank
        Orch->>L2: ingest(events)
        L2-->>Orch: queued count
    end

    rect rgb(230, 255, 230)
        Note over L3: L3 — AI Curation
        Orch->>L3: curate(events, count=5)
        L3->>Gemini: analyze best trends
        Gemini-->>L3: selected topics
        L3-->>Orch: WorkOrder[5]
    end

    rect rgb(255, 230, 255)
        Note over L4: L4 — Parallel Generation
        Orch->>L4: process(work_orders)
        par For each WorkOrder
            L4->>Gemini: generate phrases (tier=lite)
            L4->>Gemini: generate background image
        end
        L4-->>Orch: ContentPackage[5]
    end

    rect rgb(255, 255, 230)
        Note over L5: L5 — Parallel Post-Production
        Orch->>L5: enhance(packages)
        par
            L5->>Gemini: generate caption
            L5->>L5: generate hashtags
            L5->>L5: quality score
        end
        L5-->>Orch: enriched ContentPackage[5]
    end

    Orch->>DB: save packages + update run
    Orch-->>API: AgentPipelineResult
    API-->>Client: {run_id, summary}
```
