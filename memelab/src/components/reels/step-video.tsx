"use client";

import { useState } from "react";
import { Loader2, Download, RefreshCw, ArrowLeft, Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { regenerateStep, reelFileUrl, type StepState } from "@/lib/api";

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

  const isGenerating = stepData?.status === "generating";
  const filename = stepData?.path ? stepData.path.split("/").pop() ?? "" : "";
  const videoUrl = filename ? reelFileUrl(jobId, filename) : "";

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
          <p className="text-sm text-muted-foreground">Montando video...</p>
        </CardContent>
      </Card>
    );
  }

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
