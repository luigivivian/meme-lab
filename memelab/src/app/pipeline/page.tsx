"use client";

import { useState } from "react";
import { Play, List, Image, Loader2, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PipelineDiagram } from "@/components/panels/pipeline-diagram";
import { Progress } from "@/components/ui/progress";
import { usePipeline } from "@/hooks/use-pipeline";
import { usePipelineRuns } from "@/hooks/use-api";
import { imageUrl } from "@/lib/api";

export default function PipelinePage() {
  const [count, setCount] = useState(5);
  const [phrasesPerTopic, setPhrasesPerTopic] = useState(1);
  const [useGemini, setUseGemini] = useState(true);
  const [useComfyui, setUseComfyui] = useState(false);
  const [usePhraseCtx, setUsePhraseCtx] = useState(true);
  const pipeline = usePipeline();
  const { data: runs } = usePipelineRuns();

  const runEntries = runs ? Object.entries(runs) : [];

  const handleRun = () => {
    pipeline.run({
      count,
      phrases_per_topic: phrasesPerTopic,
      use_gemini_image: useGemini,
      use_comfyui: useComfyui,
      use_phrase_context: usePhraseCtx,
    });
  };

  const content = pipeline.status?.content ?? [];
  const pipelineProgress = pipeline.status
    ? Math.round(((pipeline.status.images_generated + pipeline.status.packages_produced) / (count * 2)) * 100)
    : 0;

  return (
    <div className="space-y-6 animate-page-in">
      {/* ── Diagrama sem Card wrapper — preenche toda a largura ── */}
      <div className="rounded-[14px] overflow-hidden">
        <PipelineDiagram
          layers={pipeline.status?.layers}
          currentLayer={pipeline.status?.current_layer}
          pipelineStatus={pipeline.status}
          isRunning={pipeline.isRunning}
        />
      </div>

      {/* ── Controles + Histórico ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Executar Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Quantidade de memes</label>
                <Input
                  type="number" min={1} max={20} value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Frases por tema</label>
                <Input
                  type="number" min={1} max={5} value={phrasesPerTopic}
                  onChange={(e) => setPhrasesPerTopic(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="space-y-3">
              {[
                [useGemini,    setUseGemini,    "Usar Gemini Image"       ],
                [useComfyui,   setUseComfyui,   "Usar ComfyUI (local GPU)"],
                [usePhraseCtx, setUsePhraseCtx, "Usar contexto da frase"  ],
              ].map(([val, set, label]) => (
                <label key={label as string} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={val as boolean}
                    onChange={(e) => (set as (v: boolean) => void)(e.target.checked)}
                    className="h-4 w-4 rounded accent-primary"
                  />
                  <span className="text-sm">{label as string}</span>
                </label>
              ))}
            </div>
            <Button
              onClick={handleRun}
              disabled={pipeline.isRunning}
              className={`w-full gap-2 ${pipeline.isRunning ? "pulse-glow" : ""}`}
            >
              {pipeline.isRunning
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : <Play className="h-4 w-4" />}
              {pipeline.isRunning ? "Executando..." : "Iniciar Pipeline"}
            </Button>

            {pipeline.error && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                <div className="h-2 w-2 rounded-full bg-destructive" />
                <p className="text-sm text-destructive">{pipeline.error}</p>
              </div>
            )}

            {pipeline.status && (
              <div className="rounded-xl bg-secondary p-3 text-sm space-y-3 animate-fade-in">
                <div className="flex items-center gap-2">
                  {pipeline.status.status === "completed"
                    ? <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    : <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                  <p className="font-medium">Status: {pipeline.status.status}</p>
                </div>
                {pipeline.isRunning && (
                  <div className="space-y-1">
                    <Progress value={Math.min(pipelineProgress, 95)} />
                    <p className="text-[10px] text-muted-foreground text-right">
                      {Math.min(pipelineProgress, 95)}%
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-4 gap-2 text-center">
                  {[
                    ["Trends",  pipeline.status.trends_fetched    ],
                    ["Orders",  pipeline.status.work_orders        ],
                    ["Imgs",    pipeline.status.images_generated   ],
                    ["Pacotes", pipeline.status.packages_produced  ],
                  ].map(([label, value]) => (
                    <div key={label as string} className="rounded-lg bg-background/50 p-1.5">
                      <p className="text-lg font-bold text-primary">{value as number}</p>
                      <p className="text-[10px] text-muted-foreground">{label as string}</p>
                    </div>
                  ))}
                </div>
                {pipeline.status.duration_seconds > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Duração: {pipeline.status.duration_seconds.toFixed(1)}s
                  </p>
                )}
                {pipeline.status.errors.length > 0 && (
                  <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-2 py-1">
                    <div className="h-2 w-2 rounded-full bg-destructive" />
                    <p className="text-xs text-destructive">{pipeline.status.errors[0]}</p>
                  </div>
                )}
                {pipeline.runId && (
                  <p className="text-xs text-muted-foreground">Run ID: {pipeline.runId}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Execuções anteriores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <List className="h-4 w-4" />
              Execuções Anteriores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {runEntries.length > 0 ? (
              <div className="space-y-2 max-h-80 overflow-auto">
                {runEntries.map(([runId, info], idx) => (
                  <div
                    key={runId}
                    className="stagger-item flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 transition-colors duration-200 hover:bg-secondary/70"
                    style={{ animationDelay: `${idx * 30}ms` }}
                  >
                    <div>
                      <span className="text-xs font-mono text-muted-foreground">{runId}</span>
                      <span className="text-xs text-muted-foreground ml-2">({info.packages} pacotes)</span>
                    </div>
                    <Badge variant={info.status === "completed" ? "success" : "secondary"}>
                      {info.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhuma execução registrada</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Conteúdo gerado ── */}
      {content.length > 0 && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Image className="h-4 w-4" />
              Conteúdo Gerado ({content.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {content.map((pkg, i) => {
                const filename = pkg.image_path.split(/[/\\]/).pop() ?? pkg.image_path;
                return (
                  <div
                    key={i}
                    className="stagger-item space-y-2 rounded-xl border p-3 transition-all duration-200 hover:border-primary/30"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <div className="aspect-[4/5] overflow-hidden rounded-lg bg-secondary">
                      <img src={imageUrl(filename)} alt={pkg.topic} className="h-full w-full object-cover" />
                    </div>
                    <p className="text-sm line-clamp-2">{pkg.phrase}</p>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[10px]">{pkg.topic}</Badge>
                      {pkg.quality_score > 0 && (
                        <Badge variant="outline" className="text-[10px]">
                          Q: {(pkg.quality_score * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                    {pkg.caption && (
                      <p className="text-xs text-muted-foreground line-clamp-2">{pkg.caption}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
