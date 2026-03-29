"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  jobId: string;
}

export function StepAnalysis({ stepState, onApprove, onRegenerate }: Props) {
  const [loading, setLoading] = useState(false);
  const result = stepState.result as Record<string, unknown> | undefined;

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

  if (stepState.status === "failed") {
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
          {result && <AnalysisResult data={result} />}
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
        <CardTitle className="text-lg">Analise do Produto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {result ? <AnalysisResult data={result} /> : (
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

function AnalysisResult({ data }: { data: Record<string, unknown> }) {
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
