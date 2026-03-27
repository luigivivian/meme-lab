"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Layers, Play, RefreshCw, CheckCircle, Clock, AlertCircle, Loader2, Video, XCircle } from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { IndeterminateProgress, Progress } from "@/components/ui/progress";
import { useJobs, useThemes, useVideoList } from "@/hooks/use-api";
import {
  createBatchJob,
  createBatchFromConfig,
  getJobStatus,
  imageUrl,
  videoFileUrl,
  type JobStatus,
  type VideoListItem,
} from "@/lib/api";

const STATUS_ICON: Record<string, typeof Clock> = {
  queued: Clock,
  running: RefreshCw,
  completed: CheckCircle,
};

export default function JobsPage() {
  const { data: jobsData, isLoading, mutate } = useJobs();
  const { data: themesData } = useThemes();
  const { data: videoListData } = useVideoList();
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
  const [statusFilter, setStatusFilter] = useState<string>("all");

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

  const filterTabs = [
    { key: "all", label: "Todos", count: jobs.length },
    { key: "running", label: "Executando", count: jobs.filter((j) => j.status === "running" || j.status === "queued").length },
    { key: "completed", label: "Concluidos", count: jobs.filter((j) => j.status === "completed" && j.failed === 0).length },
    { key: "with_failures", label: "Com falhas", count: jobs.filter((j) => j.failed > 0).length },
  ];

  const filteredJobs = statusFilter === "all" ? jobs
    : statusFilter === "running" ? jobs.filter((j) => j.status === "running" || j.status === "queued")
    : statusFilter === "completed" ? jobs.filter((j) => j.status === "completed" && j.failed === 0)
    : statusFilter === "with_failures" ? jobs.filter((j) => j.failed > 0)
    : jobs;

  return (
    <div className="space-y-6">
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

      {/* Filter Tabs */}
      {!isLoading && (
        <div className="flex items-center gap-1.5 rounded-xl bg-secondary/30 p-1 w-fit">
          {filterTabs.map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                statusFilter === key
                  ? "bg-primary text-white shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/[0.04]"
              }`}
            >
              {label}
              {count > 0 && <span className="ml-1.5 tabular-nums opacity-70">{count}</span>}
            </button>
          ))}
        </div>
      )}

      {/* Jobs List */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : filteredJobs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Historico de Jobs
              {statusFilter !== "all" && <span className="text-muted-foreground font-normal ml-2 text-sm">({filteredJobs.length})</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <motion.div className="space-y-2 max-h-[500px] overflow-auto" variants={staggerContainer} initial="initial" animate="animate">
            {filteredJobs.map((job) => {
              const Icon = STATUS_ICON[job.status] ?? AlertCircle;
              const jobProgress = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
              return (
                <motion.div
                  key={job.job_id}
                  className="rounded-xl bg-secondary/50 px-4 py-3 cursor-pointer hover:bg-secondary/80 transition-all duration-200"
                  variants={staggerItem}
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
                </motion.div>
              );
            })}
            </motion.div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Layers className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">
              {jobs.length === 0 ? "Nenhum job encontrado" : `Nenhum job "${filterTabs.find((t) => t.key === statusFilter)?.label ?? statusFilter}"`}
            </p>
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
                  <motion.div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" variants={staggerContainer} initial="initial" animate="animate">
                    {detailJob.results.map((r, i) => (
                      <motion.div
                        key={i}
                        className="group relative aspect-[4/5] overflow-hidden rounded-xl border bg-secondary"
                        variants={staggerItem}
                      >
                        <img src={imageUrl(r.file)} alt={r.theme} className="h-full w-full object-cover" />
                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                          <p className="text-xs text-white/80 truncate">{r.theme}</p>
                          <p className="text-[10px] text-white/50 truncate">{r.file}</p>
                        </div>
                      </motion.div>
                    ))}
                  </motion.div>
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

      {/* Video Generation Jobs */}
      {videoListData && videoListData.videos.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Video className="h-4 w-4 text-primary" />
                Video Jobs
              </CardTitle>
              <Badge variant="secondary" className="text-xs">
                {videoListData.videos.filter((v) => v.video_status === "generating").length} gerando
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
              {videoListData.videos.map((v) => {
                const filename = (v.image_path ?? "").split(/[/\\]/).pop() ?? "";
                const cost = v.video_metadata?.cost_usd as number | undefined;
                const duration = v.video_metadata?.duration as number | undefined;
                const genTime = v.video_metadata?.generation_time_ms as number | undefined;
                const error = v.video_metadata?.error as string | undefined;
                return (
                  <div
                    key={v.content_package_id}
                    className="flex items-center gap-3 rounded-xl bg-white/[0.02] px-3 py-2.5 transition-all duration-200 hover:bg-white/[0.04]"
                  >
                    {/* Thumbnail */}
                    <div className="w-10 h-10 rounded-lg overflow-hidden bg-secondary shrink-0">
                      <img src={imageUrl(filename)} alt="" className="h-full w-full object-cover" />
                    </div>
                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <p className="text-xs truncate">{v.phrase}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground">{v.topic}</span>
                        {duration && <span className="text-[10px] text-muted-foreground">{duration}s</span>}
                        {cost != null && <span className="text-[10px] text-muted-foreground">${cost.toFixed(3)}</span>}
                        {genTime != null && <span className="text-[10px] text-muted-foreground">{(genTime / 1000).toFixed(0)}s gen</span>}
                      </div>
                    </div>
                    {/* Status */}
                    <div className="shrink-0">
                      {v.video_status === "generating" ? (
                        <div className="flex items-center gap-1 text-amber-400">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span className="text-[10px] font-medium">Gerando</span>
                        </div>
                      ) : v.video_status === "success" ? (
                        <div className="flex items-center gap-1.5">
                          <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                          <a href={videoFileUrl(v.content_package_id)} target="_blank" rel="noopener noreferrer">
                            <Button size="sm" variant="ghost" className="h-6 text-[10px] px-2 gap-1">
                              <Play className="h-3 w-3" /> Ver
                            </Button>
                          </a>
                        </div>
                      ) : v.video_status === "failed" ? (
                        <div className="flex items-center gap-1 text-rose-400" title={error}>
                          <XCircle className="h-3.5 w-3.5" />
                          <span className="text-[10px] font-medium">Falhou</span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
