"use client";

import { useState, useEffect } from "react";
import { Loader2, Download, RefreshCw, ArrowLeft, Check, AlertTriangle, Copy, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { regenerateStep, reelFileUrl, getPlatformOutputs, type StepState, type PlatformOutput } from "@/lib/api";

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  youtube_shorts: "YouTube Shorts",
  tiktok: "TikTok",
  facebook: "Facebook",
};

const PLATFORM_ABBR: Record<string, string> = {
  instagram: "IG",
  youtube_shorts: "YT",
  tiktok: "TT",
  facebook: "FB",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? <CheckCircle2 className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copiado" : "Copiar"}
    </button>
  );
}

function PlatformTab({
  platform,
  data,
  videoUrl,
}: {
  platform: string;
  data: PlatformOutput;
  videoUrl: string;
}) {
  return (
    <div className="space-y-3">
      {data.title && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Titulo</span>
            <CopyButton text={data.title} />
          </div>
          <p className="text-sm bg-secondary rounded p-2">{data.title}</p>
        </div>
      )}

      {data.caption && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Caption</span>
            <CopyButton text={data.caption} />
          </div>
          <p className="text-sm bg-secondary rounded p-2 whitespace-pre-wrap">{data.caption}</p>
        </div>
      )}

      {data.description && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Descricao</span>
            <CopyButton text={data.description} />
          </div>
          <p className="text-sm bg-secondary rounded p-2 whitespace-pre-wrap max-h-32 overflow-y-auto">{data.description}</p>
        </div>
      )}

      {data.hashtags && data.hashtags.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Hashtags</span>
            <CopyButton text={data.hashtags.join(" ")} />
          </div>
          <div className="flex flex-wrap gap-1">
            {data.hashtags.map((h, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">
                {h}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.tags && data.tags.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Tags</span>
            <CopyButton text={data.tags.join(", ")} />
          </div>
          <div className="flex flex-wrap gap-1">
            {data.tags.map((t, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {videoUrl && (
        <a href={videoUrl} download>
          <Button variant="outline" size="sm" className="w-full">
            <Download className="mr-2 h-3 w-3" />
            Download Video
          </Button>
        </a>
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
  const [activeTab, setActiveTab] = useState("instagram");
  const [platformData, setPlatformData] = useState<Record<string, PlatformOutput>>({});
  const [platformList, setPlatformList] = useState<string[]>([]);

  const isGenerating = stepData?.status === "generating";
  const hasError = stepData?.status === "error";
  const errorMsg = (stepData as Record<string, unknown>)?.error as string | undefined;
  const videoPath = stepData?.path ?? "";
  const videoUrl = videoPath ? reelFileUrl(jobId, videoPath) : "";

  useEffect(() => {
    if (!videoPath) return;
    getPlatformOutputs(jobId)
      .then((res) => {
        setPlatformData(res.platform_outputs || {});
        setPlatformList(res.platforms || ["instagram"]);
        if (res.platforms?.length) setActiveTab(res.platforms[0]);
      })
      .catch(() => {});
  }, [jobId, videoPath]);

  async function handleRegenerate() {
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
          <p className="text-sm text-muted-foreground">Gerando video com Hailuo AI...</p>
          <p className="text-xs text-muted-foreground">Isso pode levar alguns minutos por cena</p>
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

  const hasPlatformData = Object.keys(platformData).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Video Final</CardTitle>
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

            {/* Platform output tabs */}
            {hasPlatformData && (
              <div className="space-y-3">
                <div className="flex gap-1 border-b border-border">
                  {platformList.map((p) => (
                    <button
                      key={p}
                      onClick={() => setActiveTab(p)}
                      className={`px-3 py-1.5 text-sm transition-colors border-b-2 -mb-px ${
                        activeTab === p
                          ? "border-purple-500 text-purple-400"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {PLATFORM_LABELS[p] ?? p}
                    </button>
                  ))}
                </div>
                {platformData[activeTab] && (
                  <PlatformTab
                    platform={activeTab}
                    data={platformData[activeTab]}
                    videoUrl={videoUrl}
                  />
                )}
              </div>
            )}

            {!hasPlatformData && (
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
            )}
          </>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Nenhum video gerado ainda.</p>
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
