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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { regenerateStep, reassembleVideo, reelFileUrl, getPlatformOutputs, type StepState, type PlatformOutput } from "@/lib/api";

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
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
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

            <div className="flex gap-2 justify-center flex-wrap">
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
          <Button variant="outline" size="sm" onClick={handleReassemble} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
            Remontar Video
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
