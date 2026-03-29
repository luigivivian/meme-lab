"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { adFileUrl, type AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  jobId: string;
}

export function StepVideo({ stepState, onApprove, onRegenerate, jobId }: Props) {
  const [loading, setLoading] = useState(false);
  const result = stepState.result as { video_paths?: string[] } | undefined;
  const videoPaths = result?.video_paths ?? [];

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando video...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "failed") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao gerar video."}</p>
          </div>
          <div className="flex justify-center">
            <Button variant="outline" onClick={onRegenerate}>
              <RefreshCw className="mr-2 h-4 w-4" /> Tentar Novamente
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "approved") {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Check className="h-5 w-5 text-emerald-400" /> Video Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`grid gap-3 ${videoPaths.length > 1 ? "grid-cols-2" : ""}`}>
            {videoPaths.map((path, i) => (
              <video key={i} src={adFileUrl(jobId, path)} controls className="w-full rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  async function handleApprove() {
    setLoading(true);
    try { await onApprove(); } finally { setLoading(false); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Video do Produto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {videoPaths.length > 0 ? (
          <div className={`grid gap-3 ${videoPaths.length > 1 ? "grid-cols-2" : ""}`}>
            {videoPaths.map((path, i) => (
              <video key={i} src={adFileUrl(jobId, path)} controls className="w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Nenhum video gerado.</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || videoPaths.length === 0}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Video
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
