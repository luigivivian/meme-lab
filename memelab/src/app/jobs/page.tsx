"use client";

import { useState } from "react";
import { Layers, Play, RefreshCw, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { IndeterminateProgress, Progress } from "@/components/ui/progress";
import { useJobs, useThemes } from "@/hooks/use-api";
import {
  createBatchJob,
  createBatchFromConfig,
  getJobStatus,
  imageUrl,
  type JobStatus,
} from "@/lib/api";

const STATUS_ICON: Record<string, typeof Clock> = {
  queued: Clock,
  running: RefreshCw,
  completed: CheckCircle,
};

export default function JobsPage() {
  const { data: jobsData, isLoading, mutate } = useJobs();
  const { data: themesData } = useThemes();
  const jobs = jobsData?.jobs ?? [];
  const themeKeys = themesData?.themes.map((t) => t.key) ?? [];

  const [launching, setLaunching] = useState(false);
  const [launchSuccess, setLaunchSuccess] = useState<string | null>(null);

  const [showCustom, setShowCustom] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState<string[]>([]);
  const [batchRefine, setBatchRefine] = useState(false);
  const [batchPasses, setBatchPasses] = useState(1);
  const [batchPausa, setBatchPausa] = useState(15);

  const [detailJob, setDetailJob] = useState<JobStatus | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const handleBatchFromConfig = async () => {
    setLaunching(true);
    setLaunchSuccess(null);
    try {
      const result = await createBatchFromConfig(false, 1);
      setLaunchSuccess(`Job ${result.job_id} criado com ${result.total_themes} temas`);
      mutate();
    } catch {
      // silent
    } finally {
      setLaunching(false);
    }
  };

  const handleBatchCustom = async () => {
    if (selectedThemes.length === 0) return;
    setLaunching(true);
    setLaunchSuccess(null);
    try {
      const result = await createBatchJob({
        themes: selectedThemes,
        pausa: batchPausa,
        auto_refine: batchRefine,
        refinement_passes: batchPasses,
      });
      setLaunchSuccess(`Job ${result.job_id} criado`);
      mutate();
      setShowCustom(false);
      setSelectedThemes([]);
    } catch {
      // silent
    } finally {
      setLaunching(false);
    }
  };

  const handleViewJob = async (jobId: string) => {
    setLoadingDetail(true);
    try {
      const status = await getJobStatus(jobId);
      setDetailJob(status);
    } catch {
      // silent
    } finally {
      setLoadingDetail(false);
    }
  };

  const toggleTheme = (key: string) => {
    setSelectedThemes((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  return (
    <div className="space-y-6 animate-page-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Batch Jobs</h2>
          <p className="text-sm text-muted-foreground">
            {jobsData?.total ?? 0} jobs registrados
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => mutate()} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Atualizar
        </Button>
      </div>

      {/* Launch Controls */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Batch do themes.yaml</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Gera imagens para todos os temas configurados no themes.yaml
            </p>
            <Button
              onClick={handleBatchFromConfig}
              disabled={launching}
              className={`w-full gap-2 ${launching ? "pulse-glow" : ""}`}
            >
              {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {launching ? "Iniciando..." : "Iniciar Batch"}
            </Button>
            {launching && <IndeterminateProgress />}
            {launchSuccess && (
              <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                <CheckCircle className="h-4 w-4 text-emerald-400" />
                <p className="text-sm text-emerald-400">{launchSuccess}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Batch Personalizado</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Escolha temas especificos para gerar em lote
            </p>
            <Button variant="outline" onClick={() => setShowCustom(true)} className="w-full gap-2">
              <Layers className="h-4 w-4" />
              Configurar Batch
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Jobs List */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : jobs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Historico de Jobs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 max-h-[500px] overflow-auto">
            {jobs.map((job, idx) => {
              const Icon = STATUS_ICON[job.status] ?? AlertCircle;
              const jobProgress = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
              return (
                <div
                  key={job.job_id}
                  className="stagger-item rounded-xl bg-secondary/50 px-4 py-3 cursor-pointer hover:bg-secondary/80 transition-all duration-200"
                  style={{ animationDelay: `${idx * 30}ms` }}
                  onClick={() => handleViewJob(job.job_id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`h-4 w-4 ${
                          job.status === "completed"
                            ? "text-emerald-400"
                            : job.status === "running"
                            ? "text-amber-400 animate-spin"
                            : "text-muted-foreground"
                        }`}
                      />
                      <div>
                        <span className="text-sm font-mono">{job.job_id}</span>
                        <p className="text-xs text-muted-foreground">
                          {job.done}/{job.total} concluidos
                          {job.failed > 0 && ` | ${job.failed} falhas`}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        job.status === "completed" ? "success"
                          : job.status === "running" ? "secondary"
                          : "outline"
                      }
                    >
                      {job.status}
                    </Badge>
                  </div>
                  {job.status === "running" && (
                    <Progress value={jobProgress} className="h-1.5" />
                  )}
                  {job.status === "completed" && (
                    <Progress value={100} className="h-1.5" indicatorClassName="bg-emerald-500" />
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Layers className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">Nenhum job encontrado</p>
          </CardContent>
        </Card>
      )}

      {/* Custom Batch Dialog */}
      <Dialog open={showCustom} onOpenChange={setShowCustom}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Batch Personalizado</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                Selecione os temas ({selectedThemes.length} selecionados)
              </p>
              <div className="flex flex-wrap gap-2 max-h-48 overflow-auto">
                {themeKeys.map((key) => (
                  <Badge
                    key={key}
                    variant={selectedThemes.includes(key) ? "default" : "outline"}
                    className="cursor-pointer transition-all duration-200 hover:scale-105"
                    onClick={() => toggleTheme(key)}
                  >
                    {key}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Pausa (seg)</label>
                <Input type="number" min={0} max={60} value={batchPausa} onChange={(e) => setBatchPausa(Number(e.target.value))} />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Passes refinamento</label>
                <Input type="number" min={1} max={3} value={batchPasses} onChange={(e) => setBatchPasses(Number(e.target.value))} />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer pb-2">
                  <input type="checkbox" checked={batchRefine} onChange={(e) => setBatchRefine(e.target.checked)} className="h-4 w-4 rounded accent-primary" />
                  <span className="text-sm">Auto refine</span>
                </label>
              </div>
            </div>
            <Button
              onClick={handleBatchCustom}
              disabled={launching || selectedThemes.length === 0}
              className={`w-full gap-2 ${launching ? "pulse-glow" : ""}`}
            >
              {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {launching ? "Iniciando..." : `Iniciar Batch (${selectedThemes.length} temas)`}
            </Button>
            {launching && <IndeterminateProgress />}
          </div>
        </DialogContent>
      </Dialog>

      {/* Job Detail Dialog */}
      <Dialog open={!!detailJob} onOpenChange={() => setDetailJob(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Job: {detailJob?.job_id}
              {detailJob && (
                <Badge variant={detailJob.status === "completed" ? "success" : detailJob.status === "running" ? "secondary" : "outline"}>
                  {detailJob.status}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>
          {loadingDetail ? (
            <div className="space-y-3 py-8">
              <Skeleton className="h-8 w-full" />
              <IndeterminateProgress />
              <p className="text-sm text-muted-foreground text-center">Carregando detalhes...</p>
            </div>
          ) : detailJob ? (
            <div className="space-y-4 animate-fade-in">
              {detailJob.status === "running" && (
                <Progress value={detailJob.total > 0 ? Math.round((detailJob.done / detailJob.total) * 100) : 0} />
              )}
              <div className="grid gap-2 sm:grid-cols-4 text-sm">
                <div className="rounded-lg bg-secondary/50 p-2 text-center">
                  <p className="text-xs text-muted-foreground">Total</p>
                  <p className="font-medium">{detailJob.total}</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-2 text-center">
                  <p className="text-xs text-muted-foreground">Concluidos</p>
                  <p className="font-medium text-emerald-400">{detailJob.done}</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-2 text-center">
                  <p className="text-xs text-muted-foreground">Falhas</p>
                  <p className="font-medium text-destructive">{detailJob.failed}</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-2 text-center">
                  <p className="text-xs text-muted-foreground">Refinamento</p>
                  <p className="font-medium">{detailJob.auto_refine ? `${detailJob.refinement_passes}x` : "Off"}</p>
                </div>
              </div>

              {detailJob.results.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Resultados</p>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {detailJob.results.map((r, i) => (
                      <div
                        key={i}
                        className="stagger-item group relative aspect-[4/5] overflow-hidden rounded-xl border bg-secondary"
                        style={{ animationDelay: `${i * 50}ms` }}
                      >
                        <img src={imageUrl(r.file)} alt={r.theme} className="h-full w-full object-cover" />
                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                          <p className="text-xs text-white/80 truncate">{r.theme}</p>
                          <p className="text-[10px] text-white/50 truncate">{r.file}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {detailJob.errors.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-destructive mb-2">Erros</p>
                  {detailJob.errors.map((err, i) => (
                    <p key={i} className="text-xs text-destructive/80 bg-destructive/10 rounded-lg p-2 mb-1">
                      {err}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
