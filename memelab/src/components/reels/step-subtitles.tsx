"use client";

import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Save, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SrtEditor, type SrtEntry } from "@/components/reels/srt-editor";
import { approveStep, editStep, regenerateStep, reelFileUrl, type StepState } from "@/lib/api";

function parseSrt(text: string): SrtEntry[] {
  return text
    .trim()
    .split(/\n\n+/)
    .map((block) => {
      const lines = block.split("\n");
      if (lines.length < 3) return null;
      const index = parseInt(lines[0]);
      const [start, end] = lines[1].split(" --> ");
      const entryText = lines.slice(2).join("\n");
      return { index, start: start?.trim() ?? "", end: end?.trim() ?? "", text: entryText };
    })
    .filter((e): e is SrtEntry => e !== null && !isNaN(e.index));
}

export function StepSubtitles({
  jobId,
  stepData,
  onApprove,
  onRegenerate,
  mutate,
}: {
  jobId: string;
  stepData: StepState["srt"];
  onApprove: (step: string) => Promise<void>;
  onRegenerate: (step: string) => Promise<void>;
  mutate: () => void;
}) {
  const [entries, setEntries] = useState<SrtEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [dirty, setDirty] = useState(false);

  const isGenerating = stepData?.status === "generating";
  const filename = stepData?.path ? stepData.path.split("/").pop() ?? "" : "";

  useEffect(() => {
    if (!filename || isGenerating) return;
    setFetching(true);
    const url = reelFileUrl(jobId, filename);
    fetch(url)
      .then((r) => r.text())
      .then((text) => {
        setEntries(parseSrt(text));
        setDirty(false);
      })
      .catch(() => {})
      .finally(() => setFetching(false));
  }, [jobId, filename, isGenerating]);

  function handleEntriesChange(updated: SrtEntry[]) {
    setEntries(updated);
    setDirty(true);
  }

  async function handleSaveEdits() {
    setLoading(true);
    try {
      await editStep(jobId, "srt", { srt_entries: entries });
      setDirty(false);
      mutate();
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setLoading(true);
    try {
      if (dirty) {
        await editStep(jobId, "srt", { srt_entries: entries });
      }
      await onApprove("srt");
      mutate();
    } catch {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    setLoading(true);
    try {
      await onRegenerate("srt");
      setEntries([]);
      setDirty(false);
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
          <p className="text-sm text-muted-foreground">Gerando legendas...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Legendas (SRT)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {fetching ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : entries.length > 0 ? (
          <SrtEditor entries={entries} onChange={handleEntriesChange} />
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Nenhuma legenda disponivel.</p>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={loading}>
            <RefreshCw className="mr-2 h-3 w-3" />
            Regenerar
          </Button>
          {dirty && (
            <Button variant="outline" size="sm" onClick={handleSaveEdits} disabled={loading}>
              <Save className="mr-2 h-3 w-3" />
              Salvar Edicoes
            </Button>
          )}
          <Button onClick={handleApprove} disabled={loading || entries.length === 0}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="mr-2 h-4 w-4" />
            )}
            Aprovar Legendas
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
