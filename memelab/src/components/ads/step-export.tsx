"use client";

import { Loader2, Check, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { adFileUrl, type AdStepData } from "@/lib/api";

interface Props {
  stepState: AdStepData;
  onApprove: () => void;
  onRegenerate: () => void;
  jobId: string;
}

const FORMAT_LABELS: Record<string, string> = {
  "9:16": "Vertical (9:16)",
  "16:9": "Horizontal (16:9)",
  "1:1": "Quadrado (1:1)",
};

export function StepExport({ stepState, jobId }: Props) {
  const result = stepState.result as { export_paths?: Record<string, string> | string[] } | undefined;
  const raw = result?.export_paths;
  // Normalize: could be dict {format: path} or list of paths
  const files: Array<{ filename: string; format: string }> = [];
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    for (const [format, path] of Object.entries(raw)) {
      files.push({ filename: String(path).split("/").pop()!, format });
    }
  } else if (Array.isArray(raw)) {
    for (const path of raw) {
      const name = String(path).split("/").pop()!;
      files.push({ filename: name, format: name.includes("16x9") ? "16:9" : name.includes("1x1") ? "1:1" : "9:16" });
    }
  }

  if (stepState.status === "generating") {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-muted-foreground">Exportando formatos...</p>
        </CardContent>
      </Card>
    );
  }

  if (stepState.status === "error") {
    return (
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
            <p className="text-red-400 text-sm">{stepState.error ?? "Erro na exportacao."}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Check className="h-5 w-5 text-emerald-400" /> Concluido
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4 text-center">
          <p className="text-emerald-400 font-medium">Video ad exportado com sucesso!</p>
        </div>

        {files.length > 0 ? (
          <div className="grid gap-3">
            {files.map((file) => (
              <div key={file.filename} className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{FORMAT_LABELS[file.format] ?? file.format}</Badge>
                  <span className="text-xs text-muted-foreground">{file.filename}</span>
                </div>
                <a href={adFileUrl(jobId, file.filename)} download>
                  <Button variant="outline" size="sm">
                    <Download className="mr-2 h-3 w-3" /> Download
                  </Button>
                </a>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center">Nenhum arquivo disponivel para download.</p>
        )}
      </CardContent>
    </Card>
  );
}
