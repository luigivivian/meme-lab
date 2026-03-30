"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, ZoomIn, Paintbrush, Sun, Layout, ImageIcon } from "lucide-react";
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
import { adFileUrl, type AdStepData } from "@/lib/api";
import {
  NICHE_BACKGROUNDS,
  NICHE_SCENE_LIGHTS,
  COMPOSITIONS,
  getPresetsForNiche,
} from "@/components/ads/ad-presets";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  onExecute?: (params?: Record<string, unknown>) => void;
  jobId: string;
  niche?: string;
}

function SceneConfig({
  backgrounds,
  sceneLights,
  bg, setBg, customBg, setCustomBg,
  light, setLight,
  composition, setComposition,
  extraNotes, setExtraNotes,
}: {
  backgrounds: Array<{ value: string; label: string }>;
  sceneLights: Array<{ value: string; label: string }>;
  bg: string; setBg: (v: string) => void;
  customBg: string; setCustomBg: (v: string) => void;
  light: string; setLight: (v: string) => void;
  composition: string; setComposition: (v: string) => void;
  extraNotes: string; setExtraNotes: (v: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Paintbrush className="h-3 w-3" /> Fundo
          </label>
          <Select value={bg} onValueChange={setBg}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {backgrounds.map((b) => (
                <SelectItem key={b.value} value={b.value}>{b.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {bg === "custom" && (
            <Input
              placeholder="Descreva o fundo..."
              value={customBg}
              onChange={(e) => setCustomBg(e.target.value)}
              className="mt-1"
            />
          )}
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground flex items-center gap-1">
            <Sun className="h-3 w-3" /> Iluminacao
          </label>
          <Select value={light} onValueChange={setLight}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {sceneLights.map((l) => (
                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-xs text-muted-foreground flex items-center gap-1">
          <Layout className="h-3 w-3" /> Composicao
        </label>
        <Select value={composition} onValueChange={setComposition}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {COMPOSITIONS.map((c) => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">Notas extras (opcional)</label>
        <Textarea
          placeholder="Ex: reflexo suave no chao, plantas ao fundo desfocadas..."
          value={extraNotes}
          onChange={(e) => setExtraNotes(e.target.value)}
          rows={2}
          className="resize-none"
        />
      </div>
    </div>
  );
}

const SCENE_MODES = [
  { value: "raw", label: "Imagem original", desc: "Usa a foto do produto como esta, sem processamento" },
  { value: "cutout", label: "Remover fundo", desc: "Remove o fundo e coloca em fundo branco limpo" },
  { value: "compose", label: "Compor cenario (IA)", desc: "Remove fundo e gera cenario com Gemini (pode alterar aparencia)" },
] as const;

export function StepScene({ stepState, onApprove, onRegenerate, onExecute, jobId, niche = "" }: Props) {
  const backgrounds = getPresetsForNiche(NICHE_BACKGROUNDS, niche);
  const sceneLights = getPresetsForNiche(NICHE_SCENE_LIGHTS, niche);

  const [loading, setLoading] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const result = stepState.result as { scene_image_path?: string } | undefined;
  const rawPath = result?.scene_image_path;
  const imageUrl = rawPath ? adFileUrl(jobId, rawPath.split("/").pop()!) : "";

  // Scene config state
  const [sceneMode, setSceneMode] = useState<"raw" | "cutout" | "compose">("cutout");
  const [bg, setBg] = useState(backgrounds.find((b) => b.value !== "custom")?.value ?? "");
  const [customBg, setCustomBg] = useState("");
  const [light, setLight] = useState(sceneLights[0]?.value ?? "");
  const [composition, setComposition] = useState(COMPOSITIONS[0]?.value ?? "centered");
  const [extraNotes, setExtraNotes] = useState("");

  // Pending — show mode selection + config
  if (stepState.status === "pending") {
    async function handleGenerate() {
      setLoading(true);
      try { if (onExecute) await onExecute({ scene_mode: sceneMode }); } finally { setLoading(false); }
    }

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Preparar Imagem</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Mode selection */}
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Modo de preparacao</label>
            <div className="grid grid-cols-1 gap-2">
              {SCENE_MODES.map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => setSceneMode(mode.value)}
                  className={`text-left rounded-lg border p-3 transition-all duration-150 ${
                    sceneMode === mode.value
                      ? "border-purple-500 bg-purple-500/10 shadow-sm shadow-purple-500/20"
                      : "border-border hover:border-purple-500/50"
                  }`}
                >
                  <p className="text-sm font-medium">{mode.label}</p>
                  <p className="text-xs text-muted-foreground">{mode.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Compose config — only when compose mode selected */}
          {sceneMode === "compose" && (
            <SceneConfig
              backgrounds={backgrounds} sceneLights={sceneLights}
              bg={bg} setBg={setBg} customBg={customBg} setCustomBg={setCustomBg}
              light={light} setLight={setLight}
              composition={composition} setComposition={setComposition}
              extraNotes={extraNotes} setExtraNotes={setExtraNotes}
            />
          )}

          <Button className="w-full" onClick={handleGenerate} disabled={loading}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : sceneMode === "raw" ? (
              <ImageIcon className="mr-2 h-4 w-4" />
            ) : (
              <Paintbrush className="mr-2 h-4 w-4" />
            )}
            {sceneMode === "raw" ? "Usar Imagem Original" : sceneMode === "cutout" ? "Remover Fundo" : "Gerar Cenario"}
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
          <p className="text-sm text-muted-foreground">Compondo cenario...</p>
          <p className="text-xs text-muted-foreground/60">Removendo fundo e criando composicao</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao compor cenario."}</p>
          </div>

          <p className="text-xs text-muted-foreground text-center">
            Ajuste os parametros e tente novamente:
          </p>

          <SceneConfig
            backgrounds={backgrounds} sceneLights={sceneLights}
            bg={bg} setBg={setBg} customBg={customBg} setCustomBg={setCustomBg}
            light={light} setLight={setLight}
            composition={composition} setComposition={setComposition}
            extraNotes={extraNotes} setExtraNotes={setExtraNotes}
          />

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
            <Check className="h-5 w-5 text-emerald-400" /> Cenario Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          {imageUrl && <img src={imageUrl} alt="Cenario" className="w-full max-w-lg mx-auto rounded-lg" />}
        </CardContent>
      </Card>
    );
  }

  // complete — show result with approve/regenerate
  async function handleApprove() {
    setLoading(true);
    try { await onApprove(); } finally { setLoading(false); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Cenario do Produto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {showConfig && (
          <SceneConfig
            backgrounds={backgrounds} sceneLights={sceneLights}
            bg={bg} setBg={setBg} customBg={customBg} setCustomBg={setCustomBg}
            light={light} setLight={setLight}
            composition={composition} setComposition={setComposition}
            extraNotes={extraNotes} setExtraNotes={setExtraNotes}
          />
        )}

        {imageUrl ? (
          <div className="relative group">
            <img
              src={imageUrl}
              alt="Cenario"
              className={`w-full rounded-lg cursor-pointer transition-transform ${zoomed ? "max-w-full" : "max-w-lg mx-auto"}`}
              onClick={() => setZoomed(!zoomed)}
            />
            <button
              className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setZoomed(!zoomed)}
            >
              <ZoomIn className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Nenhum cenario gerado.</p>
        )}

        <div className="flex gap-2 justify-end flex-wrap">
          <Button variant="outline" size="sm" onClick={() => setShowConfig(!showConfig)}>
            <Paintbrush className="mr-2 h-3 w-3" /> {showConfig ? "Ocultar config" : "Ajustar config"}
          </Button>
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !imageUrl}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Cenario
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
