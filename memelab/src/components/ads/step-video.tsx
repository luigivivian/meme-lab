"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, AlertTriangle, Film, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { adFileUrl, type AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: (overrides?: { video_model?: string; target_duration?: string }) => void;
  onRetry?: () => void;
  jobId: string;
}

const VIDEO_MODELS = [
  { value: "wan/2-6-flash-image-to-video", label: "Wan 2.6 Flash (rapido)" },
  { value: "wan/2-6-image-to-video", label: "Wan 2.6 (qualidade)" },
  { value: "kling/v2-1-standard", label: "Kling v2.1" },
  { value: "kling-3.0/video", label: "Kling 3.0 (premium)" },
  { value: "hailuo/2-3-image-to-video-standard", label: "Hailuo 2.3 Standard" },
  { value: "hailuo/2-3-image-to-video-pro", label: "Hailuo 2.3 Pro (1080p)" },
  { value: "bytedance/v1-pro-fast-image-to-video", label: "Seedance Pro Fast" },
  { value: "bytedance/v1-lite-image-to-video", label: "Seedance Lite" },
  { value: "bytedance/seedance-1.5-pro", label: "Seedance 1.5 Pro (cinema)" },
  { value: "grok-imagine/image-to-video", label: "Grok Imagine" },
];

const DURATIONS = [
  { value: "5", label: "5 segundos" },
  { value: "8", label: "8 segundos" },
  { value: "10", label: "10 segundos" },
  { value: "15", label: "15 segundos" },
];

function VideoConfig({
  model, setModel,
  duration, setDuration,
  promptOverride, setPromptOverride,
}: {
  model: string; setModel: (v: string) => void;
  duration: string; setDuration: (v: string) => void;
  promptOverride: string; setPromptOverride: (v: string) => void;
}) {
  return (
    <div className="space-y-3 rounded-lg bg-secondary/30 p-3">
      <p className="text-xs font-medium text-muted-foreground">Parametros de geracao</p>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Modelo</label>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {VIDEO_MODELS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Duracao</label>
          <Select value={duration} onValueChange={setDuration}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {DURATIONS.map((d) => (
                <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">Prompt de video (editar para ajustar)</label>
        <Textarea
          value={promptOverride}
          onChange={(e) => setPromptOverride(e.target.value)}
          rows={4}
          className="resize-none font-mono text-xs"
          placeholder="O prompt do step anterior sera usado. Edite aqui para sobrescrever..."
        />
      </div>
    </div>
  );
}

export function StepVideo({ stepState, onApprove, onRegenerate, onRetry, jobId }: Props) {
  const [loading, setLoading] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const result = stepState.result as { video_path?: string | string[] } | undefined;
  const raw = result?.video_path;
  const videoPaths = Array.isArray(raw) ? raw : raw ? [raw] : [];

  // Config state for retry
  const [model, setModel] = useState("wan/2-6-flash-image-to-video");
  const [duration, setDuration] = useState("10");
  const [promptOverride, setPromptOverride] = useState("");

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <div className="relative">
            <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
            <div className="absolute inset-0 h-8 w-8 rounded-full bg-purple-500/10 animate-ping" />
          </div>
          <p className="text-sm text-muted-foreground">Gerando video...</p>
          <p className="text-xs text-muted-foreground/60">Isso pode levar 1-3 minutos dependendo do modelo</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-red-400 text-sm font-medium">Erro na geracao do video</p>
                <p className="text-red-400/70 text-xs mt-1">{stepState.error ?? "Falha desconhecida"}</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Ajuste os parametros abaixo e tente novamente. Mudar o modelo ou reduzir a duracao pode resolver.
          </p>

          <VideoConfig
            model={model} setModel={setModel}
            duration={duration} setDuration={setDuration}
            promptOverride={promptOverride} setPromptOverride={setPromptOverride}
          />

          <div className="flex gap-2 justify-center">
            <Button
              variant="outline"
              onClick={() => onRegenerate({ video_model: model, target_duration: duration })}
            >
              <RefreshCw className="mr-2 h-4 w-4" /> Regenerar Video
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
              <video key={i} src={adFileUrl(jobId, path.split("/").pop()!)} controls className="w-full rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // complete — show video with config toggle
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
              <video key={i} src={adFileUrl(jobId, path.split("/").pop()!)} controls className="w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Nenhum video gerado.</p>
        )}

        {showConfig && (
          <VideoConfig
            model={model} setModel={setModel}
            duration={duration} setDuration={setDuration}
            promptOverride={promptOverride} setPromptOverride={setPromptOverride}
          />
        )}

        <div className="flex gap-2 justify-end flex-wrap">
          <Button variant="outline" size="sm" onClick={() => setShowConfig(!showConfig)}>
            <Settings className="mr-2 h-3 w-3" /> {showConfig ? "Ocultar" : "Parametros"}
          </Button>
          <Button variant="outline" onClick={() => onRegenerate({ video_model: model, target_duration: duration })} disabled={loading}>
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
