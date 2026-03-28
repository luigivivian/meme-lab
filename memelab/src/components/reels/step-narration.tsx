"use client";

import { useRef, useState } from "react";
import { Loader2, Play, Pause, RefreshCw, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { approveStep, regenerateStep, executeStep, reelFileUrl, type StepState } from "@/lib/api";

export function StepNarration({
  jobId,
  stepData,
  onApprove,
  onRegenerate,
  mutate,
}: {
  jobId: string;
  stepData: StepState["tts"];
  onApprove: (step: string) => Promise<void>;
  onRegenerate: (step: string) => Promise<void>;
  mutate: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);

  const isGenerating = stepData?.status === "generating";
  const filename = stepData?.path ? stepData.path.split("/").pop() ?? "" : "";
  const audioUrl = filename ? reelFileUrl(jobId, filename) : "";

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play();
    }
    setPlaying(!playing);
  }

  async function handleApprove() {
    setLoading(true);
    try {
      await onApprove("tts");
      await executeStep(jobId, "srt");
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    setLoading(true);
    try {
      await onRegenerate("tts");
      setPlaying(false);
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
          <p className="text-sm text-muted-foreground">Gerando narracao...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Narracao (TTS)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {audioUrl && (
          <div className="flex items-center gap-4 rounded-lg bg-secondary/50 p-4">
            <Button variant="outline" size="icon" onClick={togglePlay} className="shrink-0">
              {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => setPlaying(false)}
              onPause={() => setPlaying(false)}
              onPlay={() => setPlaying(true)}
            />
            <p className="text-sm text-muted-foreground truncate">{filename}</p>
          </div>
        )}

        {!audioUrl && !isGenerating && (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Nenhum audio gerado ainda.</p>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-3 w-3" />
            Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !audioUrl}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="mr-2 h-4 w-4" />
            )}
            Aprovar Narracao
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
