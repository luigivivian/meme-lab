"use client";

import { useState } from "react";
import { Loader2, RefreshCw, Check, Recycle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { approveStep, regenerateStep, regenerateSingleImage, reelFileUrl, type StepState } from "@/lib/api";

export function StepImages({ jobId, stepState, mutate }: { jobId: string; stepState: StepState; mutate?: () => void }) {
  const images = stepState.images;
  const isGenerating = images?.status === "generating";
  const paths = images?.paths ?? [];
  const reuseInfo = images?.reuse_info ?? {};
  const [loading, setLoading] = useState(false);
  const [regeneratingIdx, setRegeneratingIdx] = useState<number | null>(null);

  async function handleApprove() {
    setLoading(true);
    try {
      await approveStep(jobId, "images");
    } catch {
      setLoading(false);
    }
  }

  async function handleRegenAll() {
    setLoading(true);
    try {
      await regenerateStep(jobId, "images");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenSingle(index: number) {
    setRegeneratingIdx(index);
    try {
      await regenerateSingleImage(jobId, index);
      mutate?.();
    } finally {
      setRegeneratingIdx(null);
    }
  }

  if (isGenerating) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Imagens do Reel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[4/5] rounded-lg" />
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Gerando imagens...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Imagens do Reel</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {paths.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {paths.map((path, i) => {
              const info = reuseInfo[String(i)];
              const isReused = info?.reused === true;
              const isThisRegenerating = regeneratingIdx === i;

              return (
                <div key={i} className="relative group rounded-lg overflow-hidden border">
                  {isThisRegenerating ? (
                    <div className="w-full aspect-[4/5] flex items-center justify-center bg-secondary">
                      <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
                    </div>
                  ) : (
                    <img
                      src={reelFileUrl(jobId, path)}
                      alt={`Imagem ${i + 1}`}
                      className="w-full aspect-[4/5] object-cover"
                    />
                  )}

                  {isReused && !isThisRegenerating && (
                    <Badge
                      variant="outline"
                      className="absolute top-2 left-2 bg-amber-500/20 text-amber-400 border-amber-500/30 text-[10px]"
                    >
                      <Recycle className="mr-1 h-2.5 w-2.5" />
                      Reaproveitado
                    </Badge>
                  )}

                  <button
                    className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 disabled:opacity-50"
                    title="Gerar Nova"
                    onClick={() => handleRegenSingle(i)}
                    disabled={isThisRegenerating || loading}
                  >
                    <RefreshCw className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhuma imagem gerada ainda.
          </p>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={handleRegenAll} disabled={loading || isGenerating}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Regenerar Todas
          </Button>
          <Button onClick={handleApprove} disabled={loading || paths.length === 0}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            Aprovar e Gerar Narracao
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
