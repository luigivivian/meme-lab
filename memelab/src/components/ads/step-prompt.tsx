"use client";

import { useState, useEffect } from "react";
import { Loader2, Check, RefreshCw, Pencil, Camera, Sun, Paintbrush, Eye, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import type { AdStepData } from "@/lib/api";
import {
  NICHE_CAMERAS,
  NICHE_LIGHTINGS,
  MOODS,
  getPresetsForNiche,
} from "@/components/ads/ad-presets";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  onExecute?: () => void;
  jobId: string;
  niche?: string;
}

function PromptConfig({
  cameras,
  lightings,
  camera, setCamera, lighting, setLighting,
  mood, setMood, background, setBackground,
  videoAction, setVideoAction,
}: {
  cameras: Array<{ value: string; label: string }>;
  lightings: Array<{ value: string; label: string }>;
  camera: string; setCamera: (v: string) => void;
  lighting: string; setLighting: (v: string) => void;
  mood: string; setMood: (v: string) => void;
  background: string; setBackground: (v: string) => void;
  videoAction: string; setVideoAction: (v: string) => void;
}) {
  return (
    <div className="space-y-3">
      {/* Video action — most important field */}
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground font-medium">
          Acao do video (o que acontece)
        </label>
        <Textarea
          value={videoAction}
          onChange={(e) => setVideoAction(e.target.value)}
          placeholder="Ex: Camera gira lentamente ao redor do produto revelando detalhes, zoom suave no logo..."
          rows={2}
          className="resize-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Camera className="h-3 w-3" /> Camera
          </label>
          <Select value={camera} onValueChange={setCamera}>
            <SelectTrigger><SelectValue placeholder="Movimento" /></SelectTrigger>
            <SelectContent>
              {cameras.map((c) => (
                <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Sun className="h-3 w-3" /> Iluminacao
          </label>
          <Select value={lighting} onValueChange={setLighting}>
            <SelectTrigger><SelectValue placeholder="Setup" /></SelectTrigger>
            <SelectContent>
              {lightings.map((l) => (
                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Paintbrush className="h-3 w-3" /> Ambientacao
          </label>
          <Select value={mood} onValueChange={setMood}>
            <SelectTrigger><SelectValue placeholder="Mood" /></SelectTrigger>
            <SelectContent>
              {MOODS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Eye className="h-3 w-3" /> Fundo/Cenario
          </label>
          <Input
            value={background}
            onChange={(e) => setBackground(e.target.value)}
            placeholder="Ex: mesa de marmore, studio escuro..."
          />
        </div>
      </div>
    </div>
  );
}

export function StepPrompt({ stepState, onApprove, onRegenerate, onExecute, niche = "" }: Props) {
  const cameras = getPresetsForNiche(NICHE_CAMERAS, niche);
  const lightings = getPresetsForNiche(NICHE_LIGHTINGS, niche);

  const result = stepState.result as { prompt?: string } | undefined;
  const [text, setText] = useState(result?.prompt ?? "");
  const [editing, setEditing] = useState(false);
  const [showConfig, setShowConfig] = useState(!result?.prompt);
  const [loading, setLoading] = useState(false);

  // Config fields
  const [videoAction, setVideoAction] = useState("");
  const [camera, setCamera] = useState(cameras[0]?.value ?? "orbital");
  const [lighting, setLighting] = useState(lightings[0]?.value ?? "dramatic-rim");
  const [mood, setMood] = useState("premium");
  const [background, setBackground] = useState("");

  // Sync text when result arrives
  useEffect(() => {
    if (result?.prompt && !text) setText(result.prompt);
  }, [result?.prompt]);

  // Pending state — show config before generating
  if (stepState.status === "pending") {
    async function handleGenerate() {
      setLoading(true);
      try { if (onExecute) await onExecute(); } finally { setLoading(false); }
    }

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Configurar Prompt de Video</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Configure como a IA deve filmar seu produto. Esses parametros guiam a geracao do prompt cinematico.
          </p>

          <PromptConfig
            cameras={cameras} lightings={lightings}
            videoAction={videoAction} setVideoAction={setVideoAction}
            camera={camera} setCamera={setCamera}
            lighting={lighting} setLighting={setLighting}
            mood={mood} setMood={setMood}
            background={background} setBackground={setBackground}
          />

          <Button
            className="w-full"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            Gerar Prompt com IA
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando prompt cinematico...</p>
          <p className="text-xs text-muted-foreground/60">A IA esta criando instrucoes de filmagem</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao gerar prompt."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Prompt Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-secondary/50 p-4">
            <p className="text-sm whitespace-pre-wrap">{result?.prompt ?? text}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  async function handleApprove() {
    setLoading(true);
    try { await onApprove(); } finally { setLoading(false); }
  }

  const promptText = result?.prompt ?? text;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Prompt Cinematico</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scene configuration */}
        {showConfig && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Configure os parametros da cena antes de gerar ou edite o prompt diretamente:
            </p>
            <PromptConfig
              cameras={cameras} lightings={lightings}
              videoAction={videoAction} setVideoAction={setVideoAction}
              camera={camera} setCamera={setCamera}
              lighting={lighting} setLighting={setLighting}
              mood={mood} setMood={setMood}
              background={background} setBackground={setBackground}
            />
            {promptText && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowConfig(false)}
              >
                Ver prompt gerado
              </Button>
            )}
          </div>
        )}

        {/* Generated prompt */}
        {!showConfig && (
          <>
            {editing ? (
              <Textarea
                value={text || promptText}
                onChange={(e) => setText(e.target.value)}
                rows={8}
                className="resize-none font-mono text-xs"
              />
            ) : (
              <div className="rounded-lg bg-secondary/50 p-4">
                <p className="text-sm whitespace-pre-wrap">{promptText || "Prompt sera gerado pela IA..."}</p>
              </div>
            )}
          </>
        )}

        <div className="flex gap-2 justify-end flex-wrap">
          {!showConfig && !editing && promptText && (
            <Button variant="outline" size="sm" onClick={() => setShowConfig(true)}>
              <Camera className="mr-2 h-3 w-3" /> Configuracoes
            </Button>
          )}
          {!showConfig && !editing && promptText && (
            <Button variant="outline" size="sm" onClick={() => { setText(promptText); setEditing(true); }}>
              <Pencil className="mr-2 h-3 w-3" /> Editar
            </Button>
          )}
          {editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
          )}
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !promptText}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Prompt
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
