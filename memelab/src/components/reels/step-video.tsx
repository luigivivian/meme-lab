"use client";

import { useState, useEffect } from "react";
import {
  Loader2,
  Download,
  RefreshCw,
  ArrowLeft,
  Check,
  AlertTriangle,
  Play,
  Copy,
  CheckCircle2,
  ThumbsUp,
  Send,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import {
  regenerateStep,
  reassembleVideo,
  reelFileUrl,
  getPlatformOutputs,
  updateReelFeedback,
  type StepState,
  type PlatformOutput,
} from "@/lib/api";
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/constants";

const FEEDBACK_STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  generated: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "Gerado" },
  approved: { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", label: "Aprovado" },
  posted: { color: "bg-purple-500/20 text-purple-400 border-purple-500/30", label: "Postado" },
};

const ALL_PLATFORMS = ["instagram", "youtube_shorts", "tiktok", "facebook"] as const;

export function StepVideo({
  jobId,
  stepData,
  stepState,
  mutate,
}: {
  jobId: string;
  stepData: StepState["video"];
  stepState: StepState;
  mutate: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [posting, setPosting] = useState(false);
  const [platformOutputs, setPlatformOutputs] = useState<Record<string, PlatformOutput>>({});
  const [activePlatform, setActivePlatform] = useState("instagram");
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);

  const feedbackStatus = stepState.feedback_status;
  const postedPlatforms = stepState.posted_platforms ?? [];

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

  function togglePlatform(platform: string) {
    setSelectedPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform],
    );
  }

  const isGenerating = stepData?.status === "generating";
  const hasError = stepData?.status === "error";
  const errorMsg = (stepData as Record<string, unknown>)?.error as string | undefined;
  const videoPath = stepData?.path ?? "";
  const videoUrl = videoPath ? reelFileUrl(jobId, videoPath) : "";

  const statusKey = feedbackStatus ?? (videoUrl ? "generated" : null);
  const statusCfg = statusKey ? FEEDBACK_STATUS_CONFIG[statusKey] : null;

  async function handleReassemble() {
    setLoading(true);
    try {
      await reassembleVideo(jobId);
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenAll() {
    if (!confirm("Isso vai regenerar tudo desde os clips. Continuar?")) return;
    setLoading(true);
    try {
      await regenerateStep(jobId, "video");
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setApproving(true);
    try {
      await updateReelFeedback(jobId, "approved");
      mutate();
    } catch {
      setApproving(false);
    }
  }

  async function handleMarkPosted() {
    if (selectedPlatforms.length === 0) return;
    setPosting(true);
    try {
      await updateReelFeedback(jobId, "posted", selectedPlatforms);
      mutate();
    } catch {
      setPosting(false);
    }
  }

  if (isGenerating) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Montando video final...</p>
        </CardContent>
      </Card>
    );
  }

  if (hasError) {
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
                <p className="text-sm font-medium text-red-400">Erro na montagem do video</p>
                <p className="text-xs text-red-400/80 mt-1">{errorMsg || "Erro desconhecido"}</p>
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
            <Button onClick={handleRegenAll} disabled={loading} variant="destructive">
              {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
              Regenerar Tudo
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
          {statusCfg && (
            <Badge variant="outline" className={statusCfg.color}>
              {statusKey === "approved" && <Check className="mr-1 h-3 w-3" />}
              {statusKey === "posted" && <Send className="mr-1 h-3 w-3" />}
              {statusCfg.label}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {videoUrl ? (
          <>
            <div className={`rounded-lg border p-2 ${
              feedbackStatus === "approved" || feedbackStatus === "posted"
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-amber-500/30 bg-amber-500/5"
            }`}>
              <video
                src={videoUrl}
                controls
                className="w-full max-w-md mx-auto rounded-lg"
              />
            </div>

            {/* Action buttons row */}
            <div className="flex gap-2 justify-center flex-wrap">
              <a href={videoUrl} download>
                <Button variant="outline" size="sm">
                  <Download className="mr-2 h-3 w-3" />
                  Download
                </Button>
              </a>

              {/* Approve button — shown when not yet approved */}
              {!feedbackStatus && (
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={handleApprove}
                  disabled={approving}
                >
                  {approving ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <ThumbsUp className="mr-2 h-3 w-3" />}
                  Aprovar Video
                </Button>
              )}
            </div>

            {/* Posted platforms badges */}
            {feedbackStatus === "posted" && postedPlatforms.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-muted-foreground">Postado em:</span>
                {postedPlatforms.map((p) => (
                  <Badge key={p} variant="outline" className={PLATFORM_COLORS[p] ?? "bg-zinc-500/20 text-zinc-400"}>
                    {PLATFORM_LABELS[p] ?? p}
                  </Badge>
                ))}
              </div>
            )}

            {/* Platform selection — shown when approved but not yet posted */}
            {feedbackStatus === "approved" && (
              <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-4 space-y-3">
                <p className="text-sm font-medium">Marcar como postado</p>
                <div className="flex gap-2 flex-wrap">
                  {ALL_PLATFORMS.map((p) => {
                    const selected = selectedPlatforms.includes(p);
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => togglePlatform(p)}
                        className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                          selected
                            ? PLATFORM_COLORS[p] + " border-current"
                            : "bg-secondary text-muted-foreground border-transparent hover:bg-secondary/80"
                        }`}
                      >
                        {selected && <Check className="inline mr-1 h-3 w-3" />}
                        {PLATFORM_LABELS[p] ?? p}
                      </button>
                    );
                  })}
                </div>
                <Button
                  size="sm"
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                  onClick={handleMarkPosted}
                  disabled={posting || selectedPlatforms.length === 0}
                >
                  {posting ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Send className="mr-2 h-3 w-3" />}
                  Confirmar Postagem ({selectedPlatforms.length})
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Nenhum video gerado ainda.</p>
          </div>
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
                  {PLATFORM_LABELS[p] ?? p.charAt(0).toUpperCase() + p.slice(1)}
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
          <Button variant="outline" size="sm" onClick={handleReassemble} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
            Remontar Video
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
