"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Play, List, Image, Loader2, CheckCircle2, Tags, X, Copy, Check, Info } from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { PipelineDiagram } from "@/components/panels/pipeline-diagram";
import { Progress } from "@/components/ui/progress";
import { usePipeline } from "@/hooks/use-pipeline";
import { usePipelineRuns, useThemeKeys } from "@/hooks/use-api";
import { imageUrl, type ContentPackage } from "@/lib/api";
import { useCharacterContext } from "@/contexts/character-context";
import { SOURCE_COLORS } from "@/lib/constants";

function QualityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score < 0.4 ? "bg-red-500" : score < 0.7 ? "bg-yellow-500" : "bg-emerald-500";
  return (
    <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden" title={`Qualidade: ${pct}%`}>
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function SourceBadge({ source }: { source?: string }) {
  if (!source) return null;
  const colors = SOURCE_COLORS[source] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${colors}`}>
      {source}
    </span>
  );
}

function ContentDetailDialog({
  pkg,
  open,
  onOpenChange,
}: {
  pkg: ContentPackage | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  if (!pkg) return null;

  const filename = pkg.image_path.split(/[/\\]/).pop() ?? pkg.image_path;
  const meta = pkg.image_metadata;
  const fullCaption = [pkg.caption, pkg.hashtags].filter(Boolean).join("\n\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullCaption);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-[#1c1c22] border-white/10">
        <DialogHeader>
          <DialogTitle className="text-base">Detalhes do Conteudo</DialogTitle>
          <DialogDescription className="sr-only">Metadados e preview do conteudo gerado</DialogDescription>
        </DialogHeader>

        {/* Image */}
        <div className="aspect-[4/5] overflow-hidden rounded-lg bg-secondary">
          <img src={imageUrl(filename)} alt={pkg.topic} className="h-full w-full object-cover" />
        </div>

        {/* Phrase */}
        <p className="text-lg font-medium leading-snug">{pkg.phrase}</p>

        {/* Topic + Source badges */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="text-[11px]">{pkg.topic}</Badge>
          <SourceBadge source={pkg.background_source} />
          {meta?.theme_key && (
            <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/20 text-amber-400 px-2 py-0.5 text-[10px] font-semibold">
              {meta.theme_key.replace(/_/g, " ")}
            </span>
          )}
        </div>

        {/* Quality */}
        {pkg.quality_score > 0 && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Qualidade</span>
              <span className="text-xs font-medium">{(pkg.quality_score * 100).toFixed(0)}%</span>
            </div>
            <QualityBar score={pkg.quality_score} />
          </div>
        )}

        {/* Caption */}
        {pkg.caption && (
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground font-medium">Caption</span>
            <div className="rounded-lg bg-secondary/50 p-3 text-sm max-h-32 overflow-y-auto whitespace-pre-wrap">
              {pkg.caption}
            </div>
          </div>
        )}

        {/* Hashtags */}
        {pkg.hashtags && (
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground font-medium">Hashtags</span>
            <div className="flex flex-wrap gap-1.5">
              {pkg.hashtags.split(/\s+/).filter(Boolean).map((tag, i) => (
                <span
                  key={i}
                  className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-medium"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Image Metadata Section */}
        {meta && (
          <div className="space-y-3 rounded-lg border border-white/5 bg-secondary/30 p-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Metadados da Imagem</span>
            </div>

            <div className="grid gap-2 text-sm">
              {meta.pose && (
                <div>
                  <span className="text-xs text-muted-foreground">Pose / Acao</span>
                  <p className="text-[13px]">{meta.pose}</p>
                </div>
              )}
              {meta.scene && (
                <div>
                  <span className="text-xs text-muted-foreground">Cenario</span>
                  <p className="text-[13px]">{meta.scene}</p>
                </div>
              )}
              {meta.theme_key && (
                <div>
                  <span className="text-xs text-muted-foreground">Theme Key</span>
                  <p className="text-[13px]">{meta.theme_key}</p>
                </div>
              )}
              {pkg.background_source && (
                <div>
                  <span className="text-xs text-muted-foreground">Background Source</span>
                  <div className="mt-0.5"><SourceBadge source={pkg.background_source} /></div>
                </div>
              )}
              {meta.rendering_config && Object.keys(meta.rendering_config).length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground">Rendering Config</span>
                  <div className="mt-1 rounded bg-secondary/50 p-2 text-[12px] font-mono space-y-0.5">
                    {Object.entries(meta.rendering_config).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-muted-foreground">{k}:</span>{" "}
                        <span>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {meta.reference_images && meta.reference_images.length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground">Imagens de referencia</span>
                  <p className="text-[13px]">{meta.reference_images.length} imagem(ns)</p>
                </div>
              )}
              <div className="flex flex-wrap gap-2 pt-1">
                {meta.phrase_context_used != null && (
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                    meta.phrase_context_used
                      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                      : "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                  }`}>
                    Contexto frase: {meta.phrase_context_used ? "Sim" : "Nao"}
                  </span>
                )}
                {meta.character_dna_used != null && (
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                    meta.character_dna_used
                      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                      : "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                  }`}>
                    DNA personagem: {meta.character_dna_used ? "Sim" : "Nao"}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Copy button */}
        {fullCaption && (
          <Button variant="outline" className="w-full gap-2" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copiado!" : "Copiar Caption"}
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function PipelinePage() {
  const [count, setCount] = useState(5);
  const [phrasesPerTopic, setPhrasesPerTopic] = useState(1);
  const [useGemini, setUseGemini] = useState(true);
  const [useComfyui, setUseComfyui] = useState(false);
  const [usePhraseCtx, setUsePhraseCtx] = useState(true);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showTagPicker, setShowTagPicker] = useState(false);
  const [selectedPkg, setSelectedPkg] = useState<ContentPackage | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const { activeCharacter } = useCharacterContext();
  const pipeline = usePipeline();
  const { data: runs } = usePipelineRuns();
  const { data: themeKeysData } = useThemeKeys();

  const allKeys = themeKeysData?.keys ?? [];
  const runEntries = runs?.runs ?? [];

  const toggleTag = (key: string) => {
    setSelectedTags((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleRun = () => {
    pipeline.run({
      count,
      phrases_per_topic: phrasesPerTopic,
      use_gemini_image: useGemini,
      use_comfyui: useComfyui,
      use_phrase_context: usePhraseCtx,
      theme_tags: selectedTags.length > 0 ? selectedTags : undefined,
      character_slug: activeCharacter?.slug,
    });
  };

  const handleCardClick = (pkg: ContentPackage) => {
    setSelectedPkg(pkg);
    setDetailOpen(true);
  };

  const content = pipeline.status?.content ?? [];
  const pipelineProgress = pipeline.status
    ? Math.round(((pipeline.status.images_generated + pipeline.status.packages_produced) / (count * 2)) * 100)
    : 0;

  return (
    <div className="space-y-6">
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

            {/* ── Theme Tags ── */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setShowTagPicker(!showTagPicker)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
              >
                <Tags className="h-4 w-4" />
                <span>Temas visuais</span>
                {selectedTags.length > 0 && (
                  <Badge variant="secondary" className="text-[10px] px-1.5">
                    {selectedTags.length}
                  </Badge>
                )}
                <span className="text-[10px] text-muted-foreground ml-auto">
                  {selectedTags.length > 0 ? "custom" : "auto-diversidade"}
                </span>
              </button>

              {selectedTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedTags.map((tag) => (
                    <Badge
                      key={tag}
                      variant="default"
                      className="gap-1 text-[11px] cursor-pointer hover:bg-primary/80"
                      onClick={() => toggleTag(tag)}
                    >
                      {tag.replace(/_/g, " ")}
                      <X className="h-3 w-3" />
                    </Badge>
                  ))}
                  <button
                    type="button"
                    onClick={() => setSelectedTags([])}
                    className="text-[10px] text-muted-foreground hover:text-destructive transition-colors px-1"
                  >
                    limpar
                  </button>
                </div>
              )}

              {showTagPicker && (
                <div className="rounded-lg border bg-background/80 p-3 space-y-2 max-h-48 overflow-auto animate-fade-in">
                  {allKeys.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {allKeys.map((key) => (
                        <Badge
                          key={key}
                          variant={selectedTags.includes(key) ? "default" : "outline"}
                          className="cursor-pointer text-[11px] transition-colors hover:bg-primary/20"
                          onClick={() => toggleTag(key)}
                        >
                          {key.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">Carregando temas...</p>
                  )}
                  <p className="text-[10px] text-muted-foreground">
                    Selecione temas para forcar backgrounds especificos. Vazio = auto-diversidade.
                  </p>
                </div>
              )}
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
                    Duracao: {pipeline.status.duration_seconds.toFixed(1)}s
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

        {/* Execucoes anteriores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <List className="h-4 w-4" />
              Execucoes Anteriores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {runEntries.length > 0 ? (
              <motion.div className="space-y-2 max-h-80 overflow-auto" variants={staggerContainer} initial="initial" animate="animate">
                {runEntries.map((info) => (
                  <motion.div
                    key={info.run_id}
                    className="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 transition-colors duration-200 hover:bg-secondary/70"
                    variants={staggerItem}
                  >
                    <div>
                      <span className="text-xs font-mono text-muted-foreground">{info.run_id}</span>
                      <span className="text-xs text-muted-foreground ml-2">({info.packages_produced} pacotes)</span>
                    </div>
                    <Badge variant={info.status === "completed" ? "success" : "secondary"}>
                      {info.status}
                    </Badge>
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhuma execucao registrada</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Conteudo gerado ── */}
      {content.length > 0 && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Image className="h-4 w-4" />
              Conteudo Gerado ({content.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <motion.div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" variants={staggerContainer} initial="initial" animate="animate">
              {content.map((pkg, i) => {
                const filename = pkg.image_path.split(/[/\\]/).pop() ?? pkg.image_path;
                return (
                  <motion.div
                    key={i}
                    className="space-y-2 rounded-xl border p-3 transition-all duration-200 hover:border-primary/30 cursor-pointer group"
                    variants={staggerItem}
                    onClick={() => handleCardClick(pkg)}
                  >
                    <div className="relative aspect-[4/5] overflow-hidden rounded-lg bg-secondary">
                      <img src={imageUrl(filename)} alt={pkg.topic} className="h-full w-full object-cover group-hover:scale-[1.02] transition-transform duration-300" />
                      {/* Source + theme badges overlay */}
                      <div className="absolute top-2 left-2 flex flex-wrap gap-1">
                        <SourceBadge source={pkg.background_source} />
                        {pkg.image_metadata?.theme_key && (
                          <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/20 text-amber-400 px-2 py-0.5 text-[10px] font-semibold backdrop-blur-sm">
                            {pkg.image_metadata.theme_key.replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                    </div>
                    {/* Quality bar under image */}
                    {pkg.quality_score > 0 && <QualityBar score={pkg.quality_score} />}
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
                  </motion.div>
                );
              })}
            </motion.div>
          </CardContent>
        </Card>
      )}

      {/* Detail Dialog */}
      <ContentDetailDialog
        pkg={selectedPkg}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
