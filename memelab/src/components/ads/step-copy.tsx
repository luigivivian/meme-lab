"use client";

import { useState } from "react";
import { Loader2, Check, RefreshCw, Pencil } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  jobId: string;
}

export function StepCopy({ stepState, onApprove, onRegenerate }: Props) {
  const result = stepState.result as { headline?: string; cta?: string; hashtags?: string[] } | undefined;
  const [editing, setEditing] = useState(false);
  const [headline, setHeadline] = useState(result?.headline ?? "");
  const [cta, setCta] = useState(result?.cta ?? "");
  const [hashtags, setHashtags] = useState(result?.hashtags?.join(" ") ?? "");
  const [loading, setLoading] = useState(false);

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Gerando copy...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro ao gerar copy."}</p>
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
            <Check className="h-5 w-5 text-emerald-400" /> Copy Aprovado
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CopyPreview headline={result?.headline} cta={result?.cta} hashtags={result?.hashtags} />
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
        <CardTitle className="text-lg">Copy do Anuncio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {editing ? (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Headline</label>
              <Input value={headline} onChange={(e) => setHeadline(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">CTA</label>
              <Input value={cta} onChange={(e) => setCta(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Hashtags</label>
              <Textarea value={hashtags} onChange={(e) => setHashtags(e.target.value)} rows={2} className="resize-none" />
            </div>
          </div>
        ) : (
          <CopyPreview headline={result?.headline} cta={result?.cta} hashtags={result?.hashtags} />
        )}
        <div className="flex gap-2 justify-end">
          {!editing && result && (
            <Button variant="outline" size="sm" onClick={() => { setHeadline(result?.headline ?? ""); setCta(result?.cta ?? ""); setHashtags(result?.hashtags?.join(" ") ?? ""); setEditing(true); }}>
              <Pencil className="mr-2 h-3 w-3" /> Editar
            </Button>
          )}
          {editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(false)}>Cancelar</Button>
          )}
          <Button variant="outline" onClick={onRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerar
          </Button>
          <Button onClick={handleApprove} disabled={loading || !result}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
            Aprovar Copy
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CopyPreview({ headline, cta, hashtags }: { headline?: string; cta?: string; hashtags?: string[] }) {
  if (!headline && !cta) {
    return <p className="text-sm text-muted-foreground text-center py-8">Nenhum copy gerado.</p>;
  }
  return (
    <div className="space-y-3">
      {headline && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-1">Headline</p>
          <p className="text-sm font-medium">{headline}</p>
        </div>
      )}
      {cta && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-1">CTA</p>
          <p className="text-sm">{cta}</p>
        </div>
      )}
      {hashtags && hashtags.length > 0 && (
        <div className="rounded-lg bg-secondary/50 p-3">
          <p className="text-xs text-muted-foreground mb-1">Hashtags</p>
          <p className="text-sm">{hashtags.join(" ")}</p>
        </div>
      )}
    </div>
  );
}
