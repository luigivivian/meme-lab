"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import type { AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  onUpdate?: (updates: Record<string, unknown>) => void;
  jobId: string;
}

export function StepAnalysis({ stepState, onApprove, onRegenerate, onUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const result = stepState.result as Record<string, unknown> | undefined;

  const [description, setDescription] = useState(
    (result?.product_description as string) ?? ""
  );
  const [suggestions, setSuggestions] = useState<string[]>(
    Array.isArray(result?.scene_suggestions)
      ? (result.scene_suggestions as string[])
      : []
  );

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Analisando produto...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro na analise."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Analise Aprovada
          </CardTitle>
        </CardHeader>
        <CardContent>
          {result && <ReadOnlyFields data={result} />}
        </CardContent>
      </Card>
    );
  }

  function removeSuggestion(index: number) {
    setSuggestions((prev) => prev.filter((_, i) => i !== index));
  }

  function updateSuggestion(index: number, value: string) {
    setSuggestions((prev) => prev.map((s, i) => (i === index ? value : s)));
  }

  function addSuggestion() {
    setSuggestions((prev) => [...prev, ""]);
  }

  async function handleApprove() {
    setLoading(true);
    try {
      if (onUpdate) {
        onUpdate({
          product_description: description,
          scene_suggestions: suggestions.filter((s) => s.trim()),
        });
      }
      await onApprove();
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Analise do Produto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {result ? (
          <div className="grid gap-3">
            {/* Read-only fields */}
            {[
              { key: "niche", label: "Nicho" },
              { key: "tone", label: "Tom" },
              { key: "audience", label: "Publico-alvo" },
            ].map(({ key, label }) => {
              const value = result[key];
              if (!value) return null;
              return (
                <div key={key} className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-xs text-muted-foreground mb-1">{label}</p>
                  <p className="text-sm">{String(value)}</p>
                </div>
              );
            })}

            {/* Editable: product_description */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Descricao do Produto</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>

            {/* Editable: scene_suggestions */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">Sugestoes de Cena</label>
              {suggestions.map((s, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input
                    value={s}
                    onChange={(e) => updateSuggestion(i, e.target.value)}
                    className="flex-1"
                  />
                  <button
                    type="button"
                    onClick={() => removeSuggestion(i)}
                    className="p-1.5 rounded-md hover:bg-red-500/20 text-red-400 transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={addSuggestion}
                className="w-full border-dashed"
              >
                <Plus className="mr-2 h-3 w-3" /> Adicionar sugestao
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Nenhuma analise disponivel.</p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !result}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Confirmar Analise
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ReadOnlyFields({ data }: { data: Record<string, unknown> }) {
  const fields = [
    { key: "niche", label: "Nicho" },
    { key: "tone", label: "Tom" },
    { key: "audience", label: "Publico-alvo" },
    { key: "product_description", label: "Descricao do Produto" },
    { key: "scene_suggestions", label: "Sugestoes de Cena" },
  ];

  return (
    <div className="grid gap-3">
      {fields.map(({ key, label }) => {
        const value = data[key];
        if (!value) return null;
        return (
          <div key={key} className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground mb-1">{label}</p>
            <p className="text-sm">
              {Array.isArray(value) ? value.join(", ") : String(value)}
            </p>
          </div>
        );
      })}
    </div>
  );
}
