"use client";

import { useState, useEffect } from "react";
import {
  Loader2,
  Play,
  RefreshCw,
  ImageIcon,
  Check,
  AlertTriangle,
  Film,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  approveStep,
  regenerateStep,
  regenerateSceneVideo,
  setSceneStatic,
  initScenes,
  reelFileUrl,
  getClipSuggestions,
  useClip,
  type StepState,
  type SceneStatus,
  type ClipSuggestion,
} from "@/lib/api";

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
  const [settingStatic, setSettingStatic] = useState(false);
  const [editPrompt, setEditPrompt] = useState(scene.prompt ?? "");
  const [showPrompt, setShowPrompt] = useState(false);
  const [suggestions, setSuggestions] = useState<ClipSuggestion[]>([]);
  const [usingClip, setUsingClip] = useState(false);

  const cfg = STATUS_CONFIG[scene.status] ?? STATUS_CONFIG.pending;
  const isReused = scene.reused === true;
  const isPending = scene.status === "pending";
  const isGenerating = scene.status === "generating" || scene.status === "uploading";
  const isStatic = scene.status === "static_fallback";
  const isDone = scene.status === "success";
  const isFailed = scene.status === "failed";
  const canRegenerate = !isGenerating && !isPending;
  const imgSrc = scene.img_path ? reelFileUrl(jobId, scene.img_path) : "";

  useEffect(() => {
    if (isPending) {
      getClipSuggestions(jobId, scene.index)
        .then((r) => setSuggestions(r.suggestions))
        .catch(() => {});
    }
  }, [jobId, scene.index, isPending]);

  async function handleUseClip(assetId: number) {
    setUsingClip(true);
    try {
      await useClip(jobId, scene.index, assetId);
      mutate();
    } finally {
      setUsingClip(false);
    }
  }

  async function handleGenerate() {
    setRetrying(true);
    try {
      await regenerateSceneVideo(jobId, scene.index, editPrompt || undefined);
      mutate();
      // Keep retrying=true — SWR will update scene status to "generating",
      // hiding the button. Resetting here creates a double-click window.
    } catch {
      setRetrying(false);
    }
  }

  async function handleSetStatic() {
    setSettingStatic(true);
    try {
      await setSceneStatic(jobId, scene.index);
      mutate();
      // Keep settingStatic=true — SWR will update status to "static_fallback"
    } catch {
      setSettingStatic(false);
    }
  }

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Cena {scene.index + 1}</span>
        <Badge variant="outline" className={cfg.color}>
          {isGenerating && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
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
        {isGenerating && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-white" />
          </div>
        )}
        {isDone && !isReused && (
          <div className="absolute top-2 right-2">
            <div className="rounded-full bg-emerald-500 p-1">
              <Check className="h-3 w-3 text-white" />
            </div>
          </div>
        )}
        {isReused && isDone && (
          <div className="absolute top-2 left-2">
            <Badge variant="outline" className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-[10px]">
              Reaproveitado
            </Badge>
          </div>
        )}
        {isStatic && (
          <div className="absolute top-2 right-2">
            <Badge variant="outline" className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30 text-[10px]">
              Estatica
            </Badge>
          </div>
        )}
      </div>

      {/* Clip video preview */}
      {(isDone || isStatic) && scene.clip_path && (
        <video
          src={reelFileUrl(jobId, scene.clip_path)}
          controls
          className="w-full rounded-md"
          style={{ maxHeight: "200px" }}
        />
      )}

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

      {/* Clip suggestions */}
      {isPending && suggestions.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">Clips similares encontrados:</p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {suggestions.map((s) => (
              <button
                key={s.asset_id}
                type="button"
                onClick={() => handleUseClip(s.asset_id)}
                disabled={usingClip}
                className="shrink-0 rounded-md border bg-secondary/50 hover:border-purple-500 transition-colors overflow-hidden w-20"
              >
                <div className="aspect-9/16 relative">
                  <img src={`/api/reels/asset-thumb/${s.asset_id}`} alt="" className="w-full h-full object-cover" />
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5">
                    <span className="text-[9px] text-emerald-400 font-medium">{Math.round(s.score * 100)}%</span>
                  </div>
                </div>
                <p className="text-[9px] text-muted-foreground p-1 line-clamp-2">{s.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Pending: prompt editor + generate or keep static */}
      {isPending && (
        <div className="space-y-1.5">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setShowPrompt(!showPrompt)}
          >
            {showPrompt ? "Ocultar prompt" : "Editar prompt do clip"}
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
            className="w-full bg-purple-600 hover:bg-purple-700 text-white"
            onClick={handleGenerate}
            disabled={retrying || settingStatic}
          >
            {retrying ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Play className="mr-2 h-3 w-3" />}
            {retrying ? "Gerando..." : "Gerar Clip"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={handleSetStatic}
            disabled={settingStatic || retrying}
          >
            {settingStatic ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <ImageIcon className="mr-2 h-3 w-3" />}
            Manter Estatica
          </Button>
        </div>
      )}

      {/* Completed/failed/static: regenerate controls */}
      {canRegenerate && (
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

          <div className="flex gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={handleGenerate}
              disabled={retrying}
            >
              {retrying ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-1 h-3 w-3" />}
              {isFailed ? "Tentar" : "Regenerar"}
            </Button>
            {!isStatic && (
              <Button
                size="sm"
                variant="ghost"
                className="text-xs px-2"
                onClick={handleSetStatic}
                disabled={settingStatic}
                title="Usar imagem estatica"
              >
                {settingStatic ? <Loader2 className="h-3 w-3 animate-spin" /> : <ImageIcon className="h-3 w-3" />}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function StepClips({
  jobId,
  stepData,
  stepState,
  mutate,
}: {
  jobId: string;
  stepData: StepState["clips"];
  stepState: StepState;
  mutate: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [initializing, setInitializing] = useState(false);

  const isGenerating = stepData?.status === "generating";
  const hasError = stepData?.status === "error";
  const errorMsg = (stepData as Record<string, unknown> | undefined)?.error as string | undefined;
  const scenes = stepData?.scenes ?? [];
  const hasScenes = scenes.length > 0;

  // Auto-initialize scenes from approved images when clips step has no scenes
  useEffect(() => {
    if (!hasScenes && !isGenerating && !hasError && !initializing) {
      setInitializing(true);
      initScenes(jobId)
        .then(() => mutate())
        .catch((err) => {
          console.error("initScenes failed:", err);
        })
        .finally(() => setInitializing(false));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, hasScenes, isGenerating, hasError]);

  const pendingScenes = scenes.filter((s) => s.status === "pending");
  const readyScenes = scenes.filter((s) => s.status === "success" || s.status === "static_fallback");
  const allScenesReady = hasScenes && readyScenes.length === scenes.length;
  const hasPending = pendingScenes.length > 0;

  async function handleGenerateAllPending() {
    if (!confirm(`Gerar ${pendingScenes.length} clips via Kie.ai? Isso consome creditos.`)) return;
    setGeneratingAll(true);
    try {
      for (const scene of pendingScenes) {
        await regenerateSceneVideo(jobId, scene.index);
      }
      mutate();
      // Keep generatingAll=true — SWR will update scenes to "generating"
    } catch {
      setGeneratingAll(false);
    }
  }

  async function handleSetAllStatic() {
    if (!confirm(`Marcar ${pendingScenes.length} cenas como imagem estatica?`)) return;
    setLoading(true);
    try {
      for (const scene of pendingScenes) {
        await setSceneStatic(jobId, scene.index);
      }
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveClips() {
    setLoading(true);
    try {
      await approveStep(jobId, "clips");
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenAll() {
    if (!confirm("Isso vai re-gerar TODOS os clips via Kie.ai (consome creditos). Continuar?")) return;
    setLoading(true);
    try {
      await regenerateStep(jobId, "clips");
      mutate();
    } finally {
      setLoading(false);
    }
  }

  // Show image thumbnails with loading overlay while clips are being generated
  const imagePaths = stepState.images?.paths ?? [];
  if (isGenerating && !hasScenes && imagePaths.length > 0) {
    const generatingCount = imagePaths.length;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Film className="h-4 w-4 text-purple-400" />
            Clips
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Gerando {generatingCount} clips com Kie.ai... Isso pode levar alguns minutos por cena.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {imagePaths.map((path, i) => (
              <div key={i} className="rounded-lg border bg-card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Cena {i + 1}</span>
                  <Badge variant="outline" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    Gerando
                  </Badge>
                </div>
                <div className="aspect-[9/16] rounded-md overflow-hidden bg-secondary relative">
                  <img
                    src={reelFileUrl(jobId, path)}
                    alt={`Cena ${i + 1}`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center gap-2">
                    <Loader2 className="h-6 w-6 animate-spin text-white" />
                    <span className="text-xs text-white/80">Gerando clip...</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isGenerating && !hasScenes) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando clips com Kie.ai...</p>
          <p className="text-xs text-muted-foreground">Isso pode levar alguns minutos por cena</p>
        </CardContent>
      </Card>
    );
  }

  if (hasError && !hasScenes) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Clips</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-400">Erro na geracao dos clips</p>
                <p className="text-xs text-red-400/80 mt-1">{errorMsg || "Erro desconhecido"}</p>
                {errorMsg?.includes("Credits insufficient") && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Recarregue seus creditos em kie.ai e clique em &quot;Regenerar Tudo&quot; para continuar.
                  </p>
                )}
              </div>
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={handleRegenAll} disabled={loading} variant="destructive">
              {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
              Regenerar Tudo (Kie.ai)
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
          <Film className="h-4 w-4 text-purple-400" />
          Clips por Cena
          {isGenerating && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasScenes && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {readyScenes.length}/{scenes.length} cenas prontas
              </p>
              <div className="flex gap-2">
                {hasPending && (
                  <>
                    <Button
                      size="sm"
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                      onClick={handleGenerateAllPending}
                      disabled={generatingAll || loading}
                    >
                      {generatingAll ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Play className="mr-2 h-3 w-3" />}
                      Gerar Todos Clips ({pendingScenes.length})
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleSetAllStatic}
                      disabled={loading}
                    >
                      <ImageIcon className="mr-2 h-3 w-3" />
                      Todas Estaticas
                    </Button>
                  </>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {scenes.map((scene) => (
                <SceneCard key={scene.index} scene={scene} jobId={jobId} mutate={mutate} />
              ))}
            </div>
          </div>
        )}

        {!hasScenes && (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Nenhuma cena disponivel ainda.</p>
          </div>
        )}

        {/* Approve and assemble */}
        {allScenesReady && (
          <div className="flex justify-end">
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={handleApproveClips}
              disabled={loading}
            >
              {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Film className="mr-2 h-3 w-3" />}
              Aprovar e Montar Video
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
