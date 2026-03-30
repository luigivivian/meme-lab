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

export function StepAssembly({ stepState, onApprove, onRegenerate, jobId }: Props) {
  const [loading, setLoading] = useState(false);
  const result = stepState.result as { assembled_path?: string } | undefined;
  const rawPath = result?.assembled_path;
  const videoUrl = rawPath ? adFileUrl(jobId, rawPath.split("/").pop()!) : "";

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Montando video final...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro na montagem."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Montagem Aprovada
          </CardTitle>
        </CardHeader>
        <CardContent>
          {videoUrl && <video src={videoUrl} controls className="w-full max-w-lg mx-auto rounded-lg" />}
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
        <CardTitle className="text-lg">Montagem Final</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {videoUrl ? (
          <video src={videoUrl} controls className="w-full max-w-lg mx-auto rounded-lg" />
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Nenhuma montagem gerada.</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !videoUrl}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Montagem
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
