"use client";

import { motion } from "framer-motion";
import { Image, Bot, Workflow, TrendingUp, Play, HardDrive, Palette, Loader2, CheckCircle2, Clock, Package } from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { StatsCard } from "@/components/panels/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { IndeterminateProgress } from "@/components/ui/progress";
import { useStatus, useAgents, useLatestImages, usePipelineRuns, useDriveHealth, useJobs, useContentPackages } from "@/hooks/use-api";
import { usePipeline } from "@/hooks/use-pipeline";
import { imageUrl } from "@/lib/api";
import { SOURCE_COLORS } from "@/lib/constants";

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useStatus();
  const { data: agents } = useAgents();
  const { data: latestData } = useLatestImages(4);
  const { data: runs } = usePipelineRuns();
  const { data: driveHealth } = useDriveHealth();
  const { data: jobsData } = useJobs();
  const { data: contentData } = useContentPackages(6);
  const pipeline = usePipeline();

  const activeAgents = agents ? agents.filter((a) => a.available).length : 0;
  const totalImages = status?.total_images_generated ?? 0;
  const runCount = runs?.total ?? 0;
  const latestImages = latestData?.images ?? [];
  const jobsRunning = jobsData?.jobs.filter((j) => j.status === "running").length ?? 0;

  const handleQuickRun = () => {
    pipeline.run({ count: 5, use_gemini_image: true, use_phrase_context: true });
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard title="Imagens Geradas" value={totalImages} icon={Image} />
        <StatsCard title="Agentes Ativos" value={`${activeAgents}/${agents?.length ?? 0}`} icon={Bot} />
        <StatsCard title="Pipeline Runs" value={runCount} icon={Workflow} />
        <StatsCard title="Backgrounds" value={status?.total_backgrounds ?? 0} icon={TrendingUp} />
      </div>

      {/* Quick Actions + Status */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Acoes Rapidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={handleQuickRun}
              disabled={pipeline.isRunning}
              className={`w-full gap-2 ${pipeline.isRunning ? "pulse-glow" : ""}`}
            >
              {pipeline.isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {pipeline.isRunning ? "Executando..." : "Executar Pipeline"}
            </Button>
            {pipeline.isRunning && (
              <div className="space-y-2 animate-fade-in">
                <IndeterminateProgress />
                <p className="text-xs text-muted-foreground text-center">Pipeline em execucao...</p>
              </div>
            )}
            {pipeline.error && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                <div className="h-2 w-2 rounded-full bg-destructive" />
                <p className="text-sm text-destructive">{pipeline.error}</p>
              </div>
            )}
            {pipeline.status && (
              <div className="rounded-xl bg-secondary p-3 text-sm space-y-2 animate-fade-in">
                <div className="flex items-center gap-2">
                  {pipeline.status.status === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  )}
                  <p className="font-medium">Status: {pipeline.status.status}</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  {pipeline.status.images_generated} imgs | {pipeline.status.packages_produced} pacotes
                </p>
                {pipeline.status.duration_seconds > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Duracao: {pipeline.status.duration_seconds.toFixed(1)}s
                  </p>
                )}
                {pipeline.runId && (
                  <p className="text-xs text-muted-foreground">ID: {pipeline.runId}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Status do Servico</CardTitle>
          </CardHeader>
          <CardContent>
            {statusLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : status ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <StatusItem label="API Key" value={status.api_key_ok ? "OK" : "Faltando"} />
                <StatusItem label="Refs Carregadas" value={String(status.refs_loaded)} />
                <StatusItem label="Total Imagens" value={String(status.total_images_generated)} />
                <StatusItem label="Total Backgrounds" value={String(status.total_backgrounds)} />
                <StatusItem label="Jobs Rodando" value={`${status.jobs_running}/${status.jobs_total}`} />
                <StatusItem label="Pipeline Runs" value={String(status.pipeline_runs)} />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">API offline</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Conteudo Recente + Agentes + Ultimas Execucoes */}
      <motion.div className="grid gap-4 lg:grid-cols-3" variants={staggerContainer} initial="initial" animate="animate">
        {/* Conteudo Recente */}
        <motion.div className="lg:col-span-2" variants={staggerItem}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Package className="h-4 w-4" />
                Conteudo Recente
              </CardTitle>
            </CardHeader>
            <CardContent>
              {contentData && contentData.packages.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {contentData.packages.map((pkg) => {
                    const filename = pkg.image_path.split(/[/\\]/).pop() ?? "";
                    const score = pkg.quality_score;
                    const barColor = score < 0.4 ? "bg-red-500" : score < 0.7 ? "bg-yellow-500" : "bg-emerald-500";
                    return (
                      <div
                        key={pkg.id}
                        className="group overflow-hidden rounded-xl border bg-secondary/30 transition-colors hover:bg-secondary/50"
                      >
                        <div className="relative aspect-[4/5] overflow-hidden">
                          <img
                            src={imageUrl(filename)}
                            alt={pkg.phrase}
                            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                          />
                          <div className="absolute top-2 right-2 flex items-center gap-1">
                            {pkg.is_published && (
                              <span className="inline-flex items-center rounded-full bg-emerald-500/80 px-1.5 py-0.5 text-[9px] font-bold text-white">
                                Publicado
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="space-y-1.5 p-2">
                          <p className="line-clamp-2 text-sm leading-snug">{pkg.phrase}</p>
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${SOURCE_COLORS[pkg.background_source] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"}`}
                            >
                              {pkg.background_source}
                            </span>
                            <span className="text-[10px] text-muted-foreground">{pkg.topic}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="h-1 flex-1 overflow-hidden rounded-full bg-secondary">
                              <div
                                className={`h-full rounded-full ${barColor}`}
                                style={{ width: `${Math.round(score * 100)}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-muted-foreground">{(score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Nenhum conteudo gerado ainda</p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Agentes + Ultimas Execucoes stacked */}
        <motion.div className="space-y-4" variants={staggerItem}>
          {/* Agentes */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-4 w-4" />
                Agentes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {agents && agents.length > 0 ? (
                <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                  {agents.map((agent) => (
                    <div key={agent.name} className="flex items-center gap-1.5">
                      <div
                        className={`h-2 w-2 shrink-0 rounded-full ${agent.available ? "bg-emerald-500" : "bg-red-500"}`}
                      />
                      <span className="truncate text-xs text-muted-foreground">{agent.name}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <Skeleton className="h-16 w-full" />
              )}
            </CardContent>
          </Card>

          {/* Ultimas Execucoes */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4" />
                Ultimas Execucoes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runs && runs.runs.length > 0 ? (
                <div className="space-y-2">
                  {runs.runs.slice(0, 5).map((run) => (
                    <div
                      key={run.run_id}
                      className="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 transition-colors hover:bg-secondary/70"
                    >
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="truncate font-mono text-xs">{run.run_id.slice(0, 12)}</p>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="secondary"
                            className={`text-[10px] ${
                              run.status === "completed"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : run.status === "running"
                                ? "bg-amber-500/20 text-amber-400"
                                : run.status === "error"
                                ? "bg-red-500/20 text-red-400"
                                : ""
                            }`}
                          >
                            {run.status}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">{run.packages_produced} pacotes</span>
                        </div>
                      </div>
                      {run.duration_seconds != null && (
                        <span className="ml-2 shrink-0 text-[10px] text-muted-foreground">
                          {run.duration_seconds.toFixed(1)}s
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Nenhuma execucao registrada</p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Drive Health + Jobs */}
      <div className="grid gap-4 lg:grid-cols-2">
        {driveHealth && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <HardDrive className="h-4 w-4" />
                Storage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                <StatusItem label="Output" value={driveHealth.output_exists ? `${driveHealth.total_images} imgs` : "Nao existe"} />
                <StatusItem label="Refs" value={driveHealth.refs_exists ? "OK" : "Faltando"} />
              </div>
            </CardContent>
          </Card>
        )}
        {jobsData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Palette className="h-4 w-4" />
                Batch Jobs
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                <StatusItem label="Total Jobs" value={String(jobsData.total)} />
                <StatusItem label="Rodando" value={String(jobsRunning)} />
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Latest Images */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ultimas Imagens</CardTitle>
        </CardHeader>
        <CardContent>
          {latestImages.length > 0 ? (
            <motion.div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" variants={staggerContainer} initial="initial" animate="animate">
              {latestImages.map((img) => (
                <motion.div
                  key={img.filename}
                  className="group relative aspect-[4/5] overflow-hidden rounded-xl border bg-secondary"
                  variants={staggerItem}
                >
                  <img
                    src={imageUrl(img.filename)}
                    alt={img.filename}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                    <p className="truncate text-xs text-white/80">{img.filename}</p>
                    <p className="text-[10px] text-white/50">{img.theme} | {img.size_kb.toFixed(0)}kb</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          ) : (
            <p className="text-sm text-muted-foreground">Nenhuma imagem encontrada</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 transition-colors duration-200 hover:bg-secondary/70">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Badge variant="secondary" className="text-xs">{value}</Badge>
    </div>
  );
}
