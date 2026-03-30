"use client";

import Link from "next/link";
import {
  Film,
  Plus,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  FileEdit,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAdJobs } from "@/hooks/use-ads";
import type { AdJob } from "@/lib/api";

const STATUS_BADGE: Record<string, { color: string; label: string; icon: typeof Clock }> = {
  draft: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "Rascunho", icon: FileEdit },
  generating: { color: "bg-sky-500/20 text-sky-400 border-sky-500/30", label: "Gerando", icon: Loader2 },
  complete: { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", label: "Completo", icon: CheckCircle2 },
  failed: { color: "bg-red-500/20 text-red-400 border-red-500/30", label: "Falhou", icon: XCircle },
};

const STYLE_LABELS: Record<string, string> = {
  cinematic: "Cinematico",
  narrated: "Narrado",
  lifestyle: "Lifestyle",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  // Use UTC methods to avoid server/client hydration mismatch from timezone differences
  const months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const day = d.getUTCDate();
  const month = months[d.getUTCMonth()];
  const hour = String(d.getUTCHours()).padStart(2, "0");
  const min = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day} de ${month}, ${hour}:${min}`;
}

function formatCost(brl: number | null): string {
  if (brl == null) return "-";
  return `R$ ${brl.toFixed(2).replace(".", ",")}`;
}

export default function AdsPage() {
  const { data: jobs, isLoading } = useAdJobs();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Product Ads</h1>
          <p className="text-muted-foreground">
            Crie video ads profissionais para seus produtos
          </p>
        </div>
        <Link href="/ads/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Criar Video Ad
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Film className="h-5 w-5 text-purple-400" />
            Videos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-lg border bg-card p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="h-4 w-32 rounded bg-secondary animate-pulse" />
                    <div className="h-5 w-16 rounded-full bg-secondary animate-pulse" />
                  </div>
                  <div className="h-5 w-20 rounded-full bg-secondary/50 animate-pulse" />
                  <div className="flex justify-between">
                    <div className="h-3 w-24 rounded bg-secondary/50 animate-pulse" />
                    <div className="h-3 w-16 rounded bg-secondary/50 animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!isLoading && (!jobs || jobs.length === 0) && (
            <p className="text-sm text-muted-foreground text-center py-8">
              Nenhum video ad criado. Comece agora!
            </p>
          )}

          {!isLoading && jobs && jobs.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {jobs.map((job: AdJob) => {
                const badge = STATUS_BADGE[job.status] ?? STATUS_BADGE.draft;
                const Icon = badge.icon;
                return (
                  <Link key={job.job_id} href={`/ads/${job.job_id}`}>
                    <div className="rounded-lg border bg-card p-4 space-y-2 hover:border-purple-500/50 transition-colors cursor-pointer">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium line-clamp-2">{job.product_name}</p>
                        <Badge variant="outline" className={badge.color}>
                          {job.status === "generating" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                          {badge.label}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/30 text-xs">
                          {STYLE_LABELS[job.style] ?? job.style}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{formatDate(job.created_at)}</span>
                        <span>{formatCost(job.cost_brl)}</span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
