"use client";

import { useState } from "react";
import { Loader2, Pencil, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { approveStep, editStep, executeStep, type StepState } from "@/lib/api";

export function StepPrompt({ jobId, stepState }: { jobId: string; stepState: StepState }) {
  const prompt = stepState.prompt;
  const [text, setText] = useState(prompt?.text ?? "");
  const [editing, setEditing] = useState(!prompt?.approved);
  const [loading, setLoading] = useState(false);

  async function handleApproveAndNext() {
    setLoading(true);
    try {
      await approveStep(jobId, "prompt");
      await executeStep(jobId, "images");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveEdit() {
    setLoading(true);
    try {
      await editStep(jobId, "prompt", { text });
      setEditing(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Prompt do Reel</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {editing ? (
          <>
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              placeholder="Descreva o tema do reel..."
              className="resize-none"
            />
            <div className="flex gap-2">
              {prompt?.approved && (
                <Button variant="outline" size="sm" onClick={() => setEditing(false)} disabled={loading}>
                  Cancelar
                </Button>
              )}
              {prompt?.text && text !== prompt.text && (
                <Button variant="outline" size="sm" onClick={handleSaveEdit} disabled={loading}>
                  {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : null}
                  Salvar Edicao
                </Button>
              )}
            </div>
          </>
        ) : (
          <div className="rounded-lg bg-secondary/50 p-4">
            <p className="text-sm whitespace-pre-wrap">{prompt?.text ?? text}</p>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          {prompt?.approved && !editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              <Pencil className="mr-2 h-3 w-3" />
              Editar
            </Button>
          )}
          <Button onClick={handleApproveAndNext} disabled={loading || !text.trim()}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="mr-2 h-4 w-4" />
            )}
            Gerar Imagens
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
