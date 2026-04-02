"use client";

import { useState } from "react";
import { Loader2, RefreshCw, Check, Recycle, ThumbsUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { approveStep, regenerateStep, regenerateSingleImage, reelFileUrl, type StepState } from "@/lib/api";

export function StepImages({ jobId, stepState, mutate }: { jobId: string; stepState: StepState; mutate?: () => void }) {
  const images = stepState.images;
  const isGenerating = images?.status === "generating";
  const paths = images?.paths ?? [];
  const reuseInfo = images?.reuse_info ?? {};
  const cenas = (stepState.script?.json as { cenas?: Array<{ legenda_overlay?: string; narracao?: string }> })?.cenas ?? [];
  const [loading, setLoading] = useState(false);
  const [editPrompts, setEditPrompts] = useState<Record<number, string>>({});
  const [showPrompt, setShowPrompt] = useState<Record<number, boolean>>({});
  const [approved, setApproved] = useState<Record<number, boolean>>({});

  const allApproved = paths.length > 0 && paths.every((_, i) => approved[i]);
  const approvedCount = Object.values(approved).filter(Boolean).length;

  async function handleApprove() {
    setLoading(true);
    try {
      await approveStep(jobId, "images");
      mutate?.();
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenAll() {
    setLoading(true);
    try {
      await regenerateStep(jobId, "images");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenSingle(index: number) {
    const customPrompt = editPrompts[index];
    await regenerateSingleImage(jobId, index, customPrompt || undefined);
    mutate?.();
  }

  function togglePrompt(index: number) {
    setShowPrompt((prev) => {
      const next = { ...prev, [index]: !prev[index] };
      // Initialize prompt text from cena data if not already set
      if (next[index] && editPrompts[index] === undefined) {
        const cena = cenas[index];
        setEditPrompts((p) => ({ ...p, [index]: cena?.legenda_overlay ?? "" }));
      }
      return next;
    });
  }

  if (isGenerating) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Imagens do Reel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[4/5] rounded-lg" />
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Gerando imagens...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Imagens do Reel</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {paths.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {paths.map((path, i) => {
              const info = reuseInfo[String(i)];
              const isReused = info?.reused === true;
              const isThisGenerating = info?.generating === true;
              const version = info?.version;
              const imgUrl = reelFileUrl(jobId, path) + (version ? `?v=${version}` : "");

              return (
                <div key={i} className="rounded-lg overflow-hidden border space-y-2">
                  <div className="relative group">
                    {isThisGenerating ? (
                      <div className="w-full aspect-[4/5] flex items-center justify-center bg-secondary">
                        <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
                      </div>
                    ) : (
                      <img
                        src={imgUrl}
                        alt={`Imagem ${i + 1}`}
                        className="w-full aspect-[4/5] object-cover"
                      />
                    )}

                    {isReused && !isThisGenerating && (
                      <Badge
                        variant="outline"
                        className="absolute top-2 left-2 bg-amber-500/20 text-amber-400 border-amber-500/30 text-[10px]"
                      >
                        <Recycle className="mr-1 h-2.5 w-2.5" />
                        Reaproveitado
                      </Badge>
                    )}

                    {!isThisGenerating && (
                      <button
                        className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 disabled:opacity-50"
                        title="Gerar Nova"
                        onClick={() => handleRegenSingle(i)}
                        disabled={loading}
                      >
                        <RefreshCw className="h-3 w-3" />
                      </button>
                    )}
                  </div>

                  {/* Approve + Prompt editing */}
                  <div className="px-2 pb-2 space-y-1.5">
                    {!isThisGenerating && (
                      <button
                        type="button"
                        onClick={() => {
                          setApproved((prev) => ({ ...prev, [i]: !prev[i] }));
                        }}
                        className={`w-full flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors ${
                          approved[i]
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-secondary text-muted-foreground hover:text-foreground border border-transparent"
                        }`}
                      >
                        {approved[i] ? (
                          <><Check className="h-3 w-3" /> Aprovada</>
                        ) : (
                          <><ThumbsUp className="h-3 w-3" /> Aprovar</>
                        )}
                      </button>
                    )}

                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => togglePrompt(i)}
                    >
                      {showPrompt[i] ? "Ocultar prompt" : "Editar prompt"}
                    </button>

                    {showPrompt[i] && (
                      <>
                        <Textarea
                          value={editPrompts[i] ?? cenas[i]?.legenda_overlay ?? ""}
                          onChange={(e) => setEditPrompts((p) => ({ ...p, [i]: e.target.value }))}
                          rows={3}
                          className="text-xs"
                          placeholder="Descricao da cena para gerar a imagem..."
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          className="w-full"
                          onClick={() => {
                            setApproved((prev) => ({ ...prev, [i]: false }));
                            handleRegenSingle(i);
                          }}
                          disabled={isThisGenerating || loading}
                        >
                          {isThisGenerating ? (
                            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                          ) : (
                            <RefreshCw className="mr-2 h-3 w-3" />
                          )}
                          Gerar com prompt editado
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhuma imagem gerada ainda.
          </p>
        )}

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {approvedCount}/{paths.length} imagens aprovadas
          </p>
          <div className="flex gap-2">
            {!allApproved && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const all: Record<number, boolean> = {};
                  paths.forEach((_, i) => { all[i] = true; });
                  setApproved(all);
                }}
              >
                Aprovar Todas
              </Button>
            )}
            <Button variant="outline" onClick={handleRegenAll} disabled={loading || isGenerating}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Regenerar Todas
            </Button>
            <Button onClick={handleApprove} disabled={loading || approvedCount === 0}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Check className="mr-2 h-4 w-4" />
              )}
              Avancar ({approvedCount})
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
