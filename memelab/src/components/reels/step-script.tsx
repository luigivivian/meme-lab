"use client";

import { useState, useEffect } from "react";
import { Loader2, RefreshCw, Check, Save } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { approveStep, regenerateStep, editStep, executeStep, type StepState } from "@/lib/api";

interface Cena {
  narracao: string;
  legenda_overlay: string;
  duracao_segundos: number;
}

interface ScriptJson {
  titulo: string;
  gancho: string;
  cenas: Cena[];
  narracao_completa: string;
  cta: string;
  hashtags: string[];
}

function parseScript(raw: Record<string, unknown> | undefined): ScriptJson {
  if (!raw) return { titulo: "", gancho: "", cenas: [], narracao_completa: "", cta: "", hashtags: [] };
  return {
    titulo: (raw.titulo as string) ?? "",
    gancho: (raw.gancho as string) ?? "",
    cenas: (raw.cenas as Cena[]) ?? [],
    narracao_completa: (raw.narracao_completa as string) ?? "",
    cta: (raw.cta as string) ?? "",
    hashtags: (raw.hashtags as string[]) ?? [],
  };
}

export function StepScript({ jobId, stepState }: { jobId: string; stepState: StepState }) {
  const script = stepState.script;
  const isGenerating = script?.status === "generating";
  const [form, setForm] = useState<ScriptJson>(() => parseScript(script?.json));
  const [loading, setLoading] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (script?.json && !dirty) {
      setForm(parseScript(script.json));
    }
  }, [script?.json, dirty]);

  function updateField<K extends keyof ScriptJson>(key: K, value: ScriptJson[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  }

  function updateCena(index: number, field: keyof Cena, value: string | number) {
    setForm((prev) => {
      const cenas = [...prev.cenas];
      cenas[index] = { ...cenas[index], [field]: value };
      return { ...prev, cenas };
    });
    setDirty(true);
  }

  async function handleSave() {
    setLoading(true);
    try {
      await editStep(jobId, "script", { script_json: form as unknown as Record<string, unknown> });
      setDirty(false);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setLoading(true);
    try {
      if (dirty) {
        await editStep(jobId, "script", { script_json: form as unknown as Record<string, unknown> });
        setDirty(false);
      }
      await approveStep(jobId, "script");
      await executeStep(jobId, "tts");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegen() {
    setLoading(true);
    try {
      await regenerateStep(jobId, "script");
      setDirty(false);
    } finally {
      setLoading(false);
    }
  }

  if (isGenerating) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Roteiro</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-32 w-full" />
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Gerando roteiro...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Roteiro</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Titulo</label>
          <Input value={form.titulo} onChange={(e) => updateField("titulo", e.target.value)} />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Gancho</label>
          <Textarea value={form.gancho} onChange={(e) => updateField("gancho", e.target.value)} rows={2} />
        </div>

        <div className="space-y-3">
          <label className="text-xs text-muted-foreground font-medium">Cenas</label>
          {form.cenas.map((cena, i) => (
            <div key={i} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">Cena {i + 1}</span>
                <div className="flex items-center gap-1">
                  <label className="text-xs text-muted-foreground">Duracao (s):</label>
                  <Input
                    type="number"
                    className="w-16 h-7 text-xs"
                    value={cena.duracao_segundos}
                    onChange={(e) => updateCena(i, "duracao_segundos", parseFloat(e.target.value) || 0)}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground">Narracao</label>
                <Textarea
                  value={cena.narracao}
                  onChange={(e) => updateCena(i, "narracao", e.target.value)}
                  rows={2}
                  className="text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground">Legenda overlay</label>
                <Input
                  value={cena.legenda_overlay}
                  onChange={(e) => updateCena(i, "legenda_overlay", e.target.value)}
                  className="text-sm"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Narracao completa</label>
          <Textarea value={form.narracao_completa} rows={3} readOnly className="text-sm bg-secondary/30" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">CTA</label>
            <Input value={form.cta} onChange={(e) => updateField("cta", e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Hashtags</label>
            <Input
              value={form.hashtags.join(", ")}
              onChange={(e) => updateField("hashtags", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            />
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={handleRegen} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Regenerar
          </Button>
          {dirty && (
            <Button variant="outline" onClick={handleSave} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Salvar Edicoes
            </Button>
          )}
          <Button onClick={handleApprove} disabled={loading}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            Aprovar Roteiro
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
