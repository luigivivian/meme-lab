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

export function StepAudio({ stepState, onApprove, onRegenerate, jobId }: Props) {
  const [loading, setLoading] = useState(false);
  const result = stepState.result as { music_path?: string; tts_path?: string; mixed_path?: string } | undefined;

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando audio...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "failed") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao gerar audio."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Audio Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AudioPlayers result={result} jobId={jobId} />
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
        <CardTitle className="text-lg">Audio do Anuncio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <AudioPlayers result={result} jobId={jobId} />
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !result}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Audio
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function AudioPlayers({ result, jobId }: { result?: { music_path?: string; tts_path?: string; mixed_path?: string }; jobId: string }) {
  if (!result) return <p className="text-sm text-muted-foreground text-center py-8">Nenhum audio gerado.</p>;

  return (
    <div className="space-y-3">
      {result.music_path && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-2">Musica</p>
          <audio src={adFileUrl(jobId, result.music_path)} controls className="w-full" />
        </div>
      )}
      {result.tts_path && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-2">Narracao</p>
          <audio src={adFileUrl(jobId, result.tts_path)} controls className="w-full" />
        </div>
      )}
      {result.mixed_path && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-2">Mix Final</p>
          <audio src={adFileUrl(jobId, result.mixed_path)} controls className="w-full" />
        </div>
      )}
    </div>
  );
}
