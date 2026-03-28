"use client";

import { useState } from "react";
import { Loader2, RefreshCw, Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { approveStep, regenerateStep, reelFileUrl, type StepState } from "@/lib/api";

export function StepImages({ jobId, stepState }: { jobId: string; stepState: StepState }) {
  const images = stepState.images;
  const isGenerating = images?.status === "generating";
  const paths = images?.paths ?? [];
  const [loading, setLoading] = useState(false);

  async function handleApprove() {
    setLoading(true);
    try {
      await approveStep(jobId, "images");
    } finally {
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
            {paths.map((path, i) => (
              <div key={i} className="relative group rounded-lg overflow-hidden border">
                <img
                  src={reelFileUrl(jobId, path)}
                  alt={`Imagem ${i + 1}`}
                  className="w-full aspect-[4/5] object-cover"
                />
                <button
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80"
                  title="Regenerar imagem"
                  onClick={() => regenerateStep(jobId, "images")}
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              </div>
            ))}
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
