"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, Pencil } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  jobId: string;
}

export function StepPrompt({ stepState, onApprove, onRegenerate }: Props) {
  const result = stepState.result as { prompt_text?: string } | undefined;
  const [text, setText] = useState(result?.prompt_text ?? "");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando prompt cinematico...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "failed") {
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
            <p className="text-sm whitespace-pre-wrap">{result?.prompt_text ?? text}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  async function handleApprove() {
    setLoading(true);
    try { await onApprove(); } finally { setLoading(false); }
  }

  const promptText = result?.prompt_text ?? text;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Prompt Cinematico</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {editing ? (
          <Textarea
            value={text || promptText}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            className="resize-none"
          />
        ) : (
          <div className="rounded-lg bg-secondary/50 p-4">
            <p className="text-sm whitespace-pre-wrap">{promptText}</p>
          </div>
        )}
        <div className="flex gap-2 justify-end">
          {!editing && promptText && (
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
