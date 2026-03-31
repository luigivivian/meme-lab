"use client";

import { useState, useEffect } from "react";
import {
  Loader2,
  Download,
  RefreshCw,
  ArrowLeft,
  Check,
  AlertTriangle,
  ImageIcon,
  Play,
  Copy,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { regenerateStep, retryScene, reelFileUrl, getPlatformOutputs, type StepState, type SceneStatus, type PlatformOutput } from "@/lib/api";

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  pending: { color: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30", label: "Pendente" },
  uploading: { color: "bg-blue-500/20 text-blue-400 border-blue-500/30", label: "Enviando" },
  generating: { color: "bg-blue-500/20 text-blue-400 border-blue-500/30", label: "Gerando" },
  success: { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", label: "Sucesso" },
  failed: { color: "bg-red-500/20 text-red-400 border-red-500/30", label: "Falhou" },
  static_fallback: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "Imagem Estatica" },
};

function SceneCard({
  scene,
  jobId,
  mutate,
}: {
  scene: SceneStatus;
  jobId: string;
  mutate: () => void;
}) {
  const [retrying, setRetrying] = useState(false);
  const [editPrompt, setEditPrompt] = useState(scene.prompt ?? "");
  const [showPrompt, setShowPrompt] = useState(false);

  const cfg = STATUS_CONFIG[scene.status] ?? STATUS_CONFIG.pending;
  const isRetryable = scene.status === "failed" || scene.status === "static_fallback";
  const imgSrc = scene.img_path ? reelFileUrl(jobId, scene.img_path) : "";

  async function handleRetry() {
    setRetrying(true);
    try {
      await retryScene(jobId, scene.index, editPrompt || undefined);
      mutate();
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Cena {scene.index + 1}</span>
        <Badge variant="outline" className={cfg.color}>
          {scene.status === "generating" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          {cfg.label}
        </Badge>
      </div>

      {/* Thumbnail */}
      <div className="aspect-[9/16] rounded-md overflow-hidden bg-secondary relative">
        {imgSrc ? (
          <img src={imgSrc} alt={`Cena ${scene.index + 1}`} className="w-full h-full object-cover" />
        ) : (
          <div className="flex items-center justify-center h-full">
            <ImageIcon className="h-8 w-8 text-muted-foreground" />
          </div>
        )}
        {scene.status === "generating" && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-white" />
          </div>
        )}
        {scene.status === "success" && (
          <div className="absolute top-2 right-2">
            <div className="rounded-full bg-emerald-500 p-1">
              <Check className="h-3 w-3 text-white" />
            </div>
          </div>
        )}
      </div>

      {/* Duration */}
      {scene.duration && (
        <p className="text-xs text-muted-foreground">{scene.duration}s</p>
      )}

      {/* Error */}
      {scene.error && (
        <div className="rounded bg-red-500/10 border border-red-500/20 p-2">
          <p className="text-xs text-red-400 line-clamp-3">{scene.error}</p>
        </div>
      )}

      {/* Retry controls */}
      {isRetryable && (
        <div className="space-y-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setShowPrompt(!showPrompt)}
          >
            {showPrompt ? "Ocultar prompt" : "Editar prompt"}
          </button>

          {showPrompt && (
            <Textarea
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              rows={3}
              className="text-xs"
              placeholder="Prompt de movimento para a cena..."
            />
          )}

          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={handleRetry}
            disabled={retrying}
          >
            {retrying ? (
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-3 w-3" />
            )}
            Tentar Novamente
          </Button>
        </div>
      )}
    </div>
  );
}

export function StepVideo({
  jobId,
  stepData,
  mutate,
}: {
  jobId: string;
  stepData: StepState["video"];
  mutate: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [platformOutputs, setPlatformOutputs] = useState<Record<string, PlatformOutput>>({});
  const [activePlatform, setActivePlatform] = useState("instagram");
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    if (stepData?.path) {
      getPlatformOutputs(jobId).then((res) => {
        setPlatformOutputs(res.platform_outputs ?? {});
      }).catch(() => {});
    }
  }, [jobId, stepData?.path]);

  function handleCopy(text: string, field: string) {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }

  const isGenerating = stepData?.status === "generating";
  const hasError = stepData?.status === "error";
  const errorMsg = (stepData as Record<string, unknown>)?.error as string | undefined;
  const videoPath = stepData?.path ?? "";
  const videoUrl = videoPath ? reelFileUrl(jobId, videoPath) : "";
  const scenes = stepData?.scenes ?? [];
  const hasScenes = scenes.length > 0;

  async function handleRegenerate() {
    setLoading(true);
    try {
      await regenerateStep(jobId, "video");
      mutate();
    } finally {
      setLoading(false);
    }
  }

  // Generating state without scenes: show simple spinner
  if (isGenerating && !hasScenes) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando video com Kie.ai...</p>
          <p className="text-xs text-muted-foreground">Isso pode levar alguns minutos por cena</p>
        </CardContent>
      </Card>
    );
  }

  if (hasError && !hasScenes) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Video Final</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-400">Erro na geracao do video</p>
                <p className="text-xs text-red-400/80 mt-1">{errorMsg || "Erro desconhecido"}</p>
                {errorMsg?.includes("Credits insufficient") && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Recarregue seus creditos em kie.ai e clique em &quot;Regenerar Video&quot; para continuar.
                    Os passos anteriores (imagens, audio, legendas) estao salvos.
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-2 justify-between">
            <Link href="/reels">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-3 w-3" />
                Voltar para Reels
              </Button>
            </Link>
            <Button onClick={handleRegenerate} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
              Regenerar Video
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Play className="h-4 w-4 text-purple-400" />
          Video Final
          {isGenerating && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Per-scene grid */}
        {hasScenes && (
          <div>
            <p className="text-sm text-muted-foreground mb-2">
              {scenes.filter((s) => s.status === "success").length}/{scenes.length} cenas prontas
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {scenes.map((scene) => (
                <SceneCard key={scene.index} scene={scene} jobId={jobId} mutate={mutate} />
              ))}
            </div>
          </div>
        )}

        {/* Final assembled video */}
        {videoUrl ? (
          <>
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-2">
              <div className="flex items-center gap-2 mb-2 px-2">
                <Check className="h-4 w-4 text-emerald-400" />
                <span className="text-sm text-emerald-400 font-medium">Reel pronto!</span>
              </div>
              <video
                src={videoUrl}
                controls
                className="w-full max-w-md mx-auto rounded-lg"
              />
            </div>

            <div className="flex gap-2 justify-center">
              <a href={videoUrl} download>
                <Button variant="outline" size="sm">
                  <Download className="mr-2 h-3 w-3" />
                  Download
                </Button>
              </a>
              <Button variant="outline" size="sm" disabled title="Em breve">
                Publicar no Instagram
              </Button>
            </div>
          </>
        ) : (
          !hasScenes && (
            <div className="rounded-lg border border-dashed p-6 text-center">
              <p className="text-sm text-muted-foreground">Nenhum video gerado ainda.</p>
            </div>
          )
        )}

        {/* Platform outputs */}
        {Object.keys(platformOutputs).length > 0 && (
          <div className="space-y-3 border rounded-lg p-4">
            <p className="text-sm font-medium">Conteudo por Plataforma</p>
            <div className="flex gap-1">
              {Object.keys(platformOutputs).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setActivePlatform(p)}
                  className={`px-3 py-1 text-xs rounded-full transition-all ${
                    activePlatform === p
                      ? "bg-purple-500 text-white"
                      : "bg-secondary text-muted-foreground hover:bg-secondary/80"
                  }`}
                >
                  {p === "youtube_shorts" ? "Shorts" : p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
            {platformOutputs[activePlatform] && (
              <div className="space-y-2">
                {platformOutputs[activePlatform].title && (
                  <div>
                    <label className="text-xs text-muted-foreground">Titulo</label>
                    <div className="flex items-start gap-2">
                      <p className="text-sm flex-1">{platformOutputs[activePlatform].title}</p>
                      <button type="button" onClick={() => handleCopy(platformOutputs[activePlatform].title!, `${activePlatform}-title`)} className="shrink-0">
                        {copiedField === `${activePlatform}-title` ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />}
                      </button>
                    </div>
                  </div>
                )}
                {platformOutputs[activePlatform].caption && (
                  <div>
                    <label className="text-xs text-muted-foreground">Caption</label>
                    <div className="flex items-start gap-2">
                      <p className="text-sm flex-1 whitespace-pre-wrap">{platformOutputs[activePlatform].caption}</p>
                      <button type="button" onClick={() => handleCopy(platformOutputs[activePlatform].caption!, `${activePlatform}-caption`)} className="shrink-0">
                        {copiedField === `${activePlatform}-caption` ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />}
                      </button>
                    </div>
                  </div>
                )}
                {platformOutputs[activePlatform].hashtags && platformOutputs[activePlatform].hashtags!.length > 0 && (
                  <div>
                    <label className="text-xs text-muted-foreground">Hashtags</label>
                    <div className="flex items-start gap-2">
                      <p className="text-sm flex-1 text-purple-300">{platformOutputs[activePlatform].hashtags!.join(" ")}</p>
                      <button type="button" onClick={() => handleCopy(platformOutputs[activePlatform].hashtags!.join(" "), `${activePlatform}-hashtags`)} className="shrink-0">
                        {copiedField === `${activePlatform}-hashtags` ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 justify-between">
          <Link href="/reels">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-3 w-3" />
              Voltar para Reels
            </Button>
          </Link>
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
            Regenerar Video
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
