"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, ZoomIn } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  jobId: string;
  niche?: string;
}

export function StepScene({ stepState, onApprove, onRegenerate, jobId, niche = "" }: Props) {
  const backgrounds = getPresetsForNiche(NICHE_BACKGROUNDS, niche);
  const sceneLights = getPresetsForNiche(NICHE_SCENE_LIGHTS, niche);

  const defaultBg = backgrounds.find((b) => b.value !== "custom")?.value ?? "";
  const defaultLight = sceneLights[0]?.value ?? "";

  const [loading, setLoading] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const [background, setBackground] = useState(defaultBg);
  const [customBg, setCustomBg] = useState("");
  const [sceneLight, setSceneLight] = useState(defaultLight);
  const [composition, setComposition] = useState(COMPOSITIONS[0]?.value ?? "centered");

  const result = stepState.result as { image_path?: string } | undefined;
  const imageUrl = result?.image_path ? adFileUrl(jobId, result.image_path) : "";

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Compondo cenario...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "failed") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao compor cenario."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Cenario Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          {imageUrl && <img src={imageUrl} alt="Cenario" className="w-full max-w-lg mx-auto rounded-lg" />}
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
        <CardTitle className="text-lg">Cenario do Produto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
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
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Fundo</label>
              <Select value={background} onValueChange={setBackground}>
                <SelectTrigger><SelectValue placeholder="Selecionar fundo" /></SelectTrigger>
                <SelectContent>
                  {backgrounds.map((b) => (
                    <SelectItem key={b.value} value={b.value}>{b.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {background === "custom" && (
                <Input
                  placeholder="Descreva o fundo personalizado"
                  value={customBg}
                  onChange={(e) => setCustomBg(e.target.value)}
                  className="mt-1"
                />
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Iluminacao</label>
              <Select value={sceneLight} onValueChange={setSceneLight}>
                <SelectTrigger><SelectValue placeholder="Selecionar luz" /></SelectTrigger>
                <SelectContent>
                  {sceneLights.map((l) => (
                    <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs text-muted-foreground">Composicao</label>
              <Select value={composition} onValueChange={setComposition}>
                <SelectTrigger><SelectValue placeholder="Selecionar composicao" /></SelectTrigger>
                <SelectContent>
                  {COMPOSITIONS.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || (!imageUrl && !background)}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Cenario
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
