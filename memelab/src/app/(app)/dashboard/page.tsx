"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Image, Bot, Workflow, TrendingUp, Play, HardDrive, Palette,
  Loader2, CheckCircle2, Clock, Package, Send, Activity, Zap, Gauge,
} from "lucide-react";
import { staggerContainer, staggerItem, fadeInUp, fastStaggerContainer, fastStaggerItem } from "@/lib/animations";
import { StatsCard } from "@/components/panels/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton, SkeletonCard, SkeletonList } from "@/components/ui/skeleton";
import { Progress, IndeterminateProgress } from "@/components/ui/progress";
import {
  useStatus, useAgents, useLatestImages, usePipelineRuns,
  useDriveHealth, useJobs, useContentPackages, useQueueSummary, useUsage,
} from "@/hooks/use-api";
import { usePipeline } from "@/hooks/use-pipeline";
import { imageUrl, type ContentPackageDB } from "@/lib/api";
import { SOURCE_COLORS, AGENT_TYPE_COLORS, PUBLISH_STATUS_COLORS } from "@/lib/constants";

const DISTRIBUTION_BAR_COLORS: Record<string, string> = {
  gemini: "bg-blue-500",
  gemini_free: "bg-sky-500",
  gemini_paid: "bg-indigo-500",
  comfyui: "bg-violet-500",
  static: "bg-zinc-600",
};
const DISTRIBUTION_DOT_COLORS: Record<string, string> = {
  gemini: "bg-blue-400",
  gemini_free: "bg-sky-400",
  gemini_paid: "bg-indigo-400",
  comfyui: "bg-violet-400",
  static: "bg-zinc-500",
};

function getSourceLabel(pkg: ContentPackageDB): string {
  if (pkg.background_source === "gemini") {
    const tier = pkg.image_metadata?.tier;
    if (tier === "gemini_paid") return "gemini_paid";
    if (tier === "gemini_free") return "gemini_free";
    return "gemini"; // legacy entries without tier metadata — backward compatible
  }
  return pkg.background_source || "static";
}

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useStatus();
  const { data: agents } = useAgents();
  const { data: latestData } = useLatestImages(4);
  const { data: runs } = usePipelineRuns();
  const { data: driveHealth } = useDriveHealth();
  const { data: jobsData } = useJobs();
  const { data: contentData } = useContentPackages(6);
  const { data: queueSummary } = useQueueSummary();
  const { data: usageData, isLoading: usageLoading } = useUsage();
  const pipeline = usePipeline();

  const activeAgents = agents ? agents.filter((a) => a.available).length : 0;
  const totalImages = status?.total_images_generated ?? 0;
  const runCount = runs?.total ?? 0;
  const latestImages = latestData?.images ?? [];
  const jobsRunning = jobsData?.jobs.filter((j) => j.status === "running").length ?? 0;

  const sourceDistribution = useMemo(() => {
    if (!contentData?.packages.length) return null;
    const counts: Record<string, number> = {};
    for (const pkg of contentData.packages) {
      const src = getSourceLabel(pkg);
      counts[src] = (counts[src] || 0) + 1;
    }
    const total = contentData.packages.length;
    return { counts, total };
  }, [contentData]);

  const handleQuickRun = () => {
    pipeline.run({ count: 5, use_gemini_image: true, use_phrase_context: true });
  };

  return (
    <div className="space-y-6">
      {/* Welcome + Quick Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-sm text-muted-foreground/70 mt-1">
            Visao geral do pipeline de memes
          </p>
        </div>
        <Button
          onClick={handleQuickRun}
          disabled={pipeline.isRunning}
          size="lg"
          className={pipeline.isRunning ? "pulse-glow" : ""}
        >
          {pipeline.isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {pipeline.isRunning ? "Executando..." : "Quick Run"}
        </Button>
      </div>

      {/* Pipeline status banners */}
      <AnimatePresence mode="wait">
        {pipeline.isRunning && (
          <motion.div
            key="running"
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            exit="exit"
            className="rounded-xl bg-primary/[0.04] border border-primary/15 p-4 space-y-3"
          >
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <p className="text-sm font-medium">Pipeline em execucao...</p>
            </div>
            <IndeterminateProgress />
          </motion.div>
        )}
        {pipeline.error && !pipeline.isRunning && (
          <motion.div
            key="error"
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            exit="exit"
            className="flex items-center gap-2 rounded-xl bg-rose-500/[0.06] border border-rose-500/15 px-4 py-3"
          >
            <div className="h-2 w-2 rounded-full bg-rose-500" />
            <p className="text-sm text-rose-400">{pipeline.error}</p>
          </motion.div>
        )}
        {pipeline.status && !pipeline.isRunning && !pipeline.error && (
          <motion.div
            key="done"
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            exit="exit"
            className="rounded-xl bg-emerald-500/[0.04] border border-emerald-500/15 p-4"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <p className="text-sm font-medium">
                Pipeline concluido — {pipeline.status.images_generated} imgs, {pipeline.status.packages_produced} pacotes
                {pipeline.status.duration_seconds > 0 && ` em ${pipeline.status.duration_seconds.toFixed(1)}s`}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats Grid */}
      {statusLoading ? (
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <motion.div
          className="grid gap-4 grid-cols-2 lg:grid-cols-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <motion.div variants={staggerItem}>
            <StatsCard title="Imagens" value={totalImages} icon={Image} />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard title="Agentes" value={`${activeAgents}/${agents?.length ?? 0}`} icon={Bot} />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard title="Runs" value={runCount} icon={Workflow} />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard title="Backgrounds" value={status?.total_backgrounds ?? 0} icon={TrendingUp} />
          </motion.div>
        </motion.div>
      )}

      {/* Main content: 2/3 + 1/3 layout */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Left: Conteudo Recente */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Package className="h-4 w-4 text-primary" />
                  Conteudo Recente
                </CardTitle>
                {sourceDistribution && (
                  <div className="flex items-center gap-2">
                    {Object.entries(sourceDistribution.counts).map(([src, count]) => (
                      <span key={src} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${DISTRIBUTION_DOT_COLORS[src] ?? "bg-zinc-500"}`}
                        />
                        {src.replace("_", " ")} ({count})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {/* Source Distribution Bar */}
              {sourceDistribution && (
                <div className="flex h-1 w-full overflow-hidden rounded-full bg-white/[0.04] mb-4">
                  {Object.entries(sourceDistribution.counts).map(([src, count]) => (
                    <div
                      key={src}
                      className={`h-full transition-all duration-500 ${DISTRIBUTION_BAR_COLORS[src] ?? "bg-zinc-600"}`}
                      style={{ width: `${(count / sourceDistribution.total) * 100}%` }}
                    />
                  ))}
                </div>
              )}

              {contentData && contentData.packages.length > 0 ? (
                <motion.div
                  className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                >
                  {contentData.packages.map((pkg) => {
                    const filename = pkg.image_path.split(/[/\\]/).pop() ?? "";
                    const score = pkg.quality_score;
                    const barColor = score < 0.4 ? "bg-rose-500" : score < 0.7 ? "bg-amber-500" : "bg-emerald-500";
                    const themeKey = pkg.image_metadata?.theme_key;
                    const sourceLabel = getSourceLabel(pkg);
                    return (
                      <motion.div
                        key={pkg.id}
                        variants={staggerItem}
                        className="group overflow-hidden rounded-xl border border-white/[0.04] bg-[var(--color-surface-2)]/50 transition-all duration-300 hover:bg-[var(--color-surface-2)] hover:border-white/[0.08] hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)] cursor-pointer"
                      >
                        <div className="relative aspect-[4/5] overflow-hidden">
                          <img
                            src={imageUrl(filename)}
                            alt={pkg.phrase}
                            className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03]"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                          <div className="absolute top-2 right-2 flex items-center gap-1">
                            {themeKey && (
                              <span className="inline-flex items-center rounded-full bg-violet-500/80 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-sm">
                                {themeKey}
                              </span>
                            )}
                            {pkg.is_published && (
                              <span className="inline-flex items-center rounded-full bg-emerald-500/80 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-sm">
                                Publicado
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="space-y-1.5 p-2.5">
                          <p className="line-clamp-2 text-sm leading-snug">{pkg.phrase}</p>
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${SOURCE_COLORS[sourceLabel] ?? "bg-zinc-500/15 text-zinc-400 border-zinc-500/20"}`}
                            >
                              {sourceLabel.replace("_", " ")}
                            </span>
                            <span className="text-[10px] text-muted-foreground">{pkg.topic}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.04]">
                              <div
                                className={`h-full rounded-full ${barColor} transition-all duration-500`}
                                style={{ width: `${Math.round(score * 100)}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-muted-foreground tabular-nums">{(score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/[0.03]">
                    <Package className="h-7 w-7 text-muted-foreground/30" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">Nenhum conteudo gerado ainda</p>
                    <p className="text-xs text-muted-foreground/50 mt-1">Execute o pipeline para gerar seus primeiros memes</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleQuickRun} disabled={pipeline.isRunning} className="gap-2 mt-1">
                    <Play className="h-3.5 w-3.5" />
                    Gerar primeiro conteudo
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Latest Images */}
          {latestImages.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Image className="h-4 w-4 text-primary" />
                  Ultimas Imagens
                </CardTitle>
              </CardHeader>
              <CardContent>
                <motion.div className="grid gap-3 grid-cols-2 lg:grid-cols-4" variants={staggerContainer} initial="initial" animate="animate">
                  {latestImages.map((img) => (
                    <motion.div
                      key={img.filename}
                      className="group relative aspect-[4/5] overflow-hidden rounded-xl border border-white/[0.04] bg-[var(--color-surface-2)] cursor-pointer"
                      variants={staggerItem}
                    >
                      <img
                        src={imageUrl(img.filename)}
                        alt={img.filename}
                        className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03]"
                      />
                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-3 pt-8">
                        <p className="truncate text-xs text-white/80">{img.filename}</p>
                        <p className="text-[10px] text-white/40">{img.theme} | {img.size_kb.toFixed(0)}kb</p>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebar cards */}
        <div className="space-y-4">
          {/* Service Status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" />
                Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <SkeletonList rows={5} />
              ) : status ? (
                <motion.div className="space-y-1.5" variants={fastStaggerContainer} initial="initial" animate="animate">
                  <motion.div variants={fastStaggerItem}>
                    <StatusRow label="API Key" value={status.api_key_ok ? "OK" : "Faltando"} ok={status.api_key_ok} />
                  </motion.div>
                  <motion.div variants={fastStaggerItem}>
                    <StatusRow label="Refs" value={String(status.refs_loaded)} ok={status.refs_loaded > 0} />
                  </motion.div>
                  <motion.div variants={fastStaggerItem}>
                    <StatusRow label="Imagens" value={String(status.total_images_generated)} />
                  </motion.div>
                  <motion.div variants={fastStaggerItem}>
                    <StatusRow label="Jobs" value={`${status.jobs_running}/${status.jobs_total}`} />
                  </motion.div>
                  <motion.div variants={fastStaggerItem}>
                    <StatusRow label="Runs" value={String(status.pipeline_runs)} />
                  </motion.div>
                </motion.div>
              ) : (
                <p className="text-sm text-muted-foreground">API offline</p>
              )}
            </CardContent>
          </Card>

          {/* Uso da API */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Gauge className="h-4 w-4 text-primary" />
                Uso da API
              </CardTitle>
            </CardHeader>
            <CardContent>
              {usageLoading ? (
                <SkeletonList rows={3} />
              ) : usageData && usageData.services.length > 0 ? (
                <motion.div className="space-y-3" variants={fastStaggerContainer} initial="initial" animate="animate">
                  {usageData.services.map((svc) => {
                    const isUnlimited = svc.limit === 0;
                    const pct = isUnlimited ? 0 : Math.min(100, Math.round((svc.used / svc.limit) * 100));
                    return (
                      <motion.div key={`${svc.service}-${svc.tier}`} className="space-y-1.5" variants={fastStaggerItem}>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">
                            {svc.service.replace("_", " ")}
                            <span className="ml-1 text-[10px] text-muted-foreground/50">({svc.tier})</span>
                          </span>
                          <span className="text-xs font-medium tabular-nums">
                            {isUnlimited ? "Ilimitado" : `${svc.used} / ${svc.limit} hoje`}
                          </span>
                        </div>
                        {!isUnlimited && (
                          <Progress value={pct} indicatorClassName={usageBarColor(pct)} />
                        )}
                      </motion.div>
                    );
                  })}
                  <div className="flex items-center justify-between pt-1 border-t border-white/[0.04]">
                    <span className="text-[10px] text-muted-foreground/50">Reseta 00:00 PT</span>
                    <span className="text-[10px] text-muted-foreground/50">Free tier</span>
                  </div>
                </motion.div>
              ) : (
                <p className="text-sm text-muted-foreground/60">Sem dados de uso</p>
              )}
            </CardContent>
          </Card>

          {/* Agents */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-4 w-4 text-primary" />
                Agentes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {agents && agents.length > 0 ? (
                <motion.div className="space-y-1" variants={fastStaggerContainer} initial="initial" animate="animate">
                  {agents.map((agent) => (
                    <motion.div
                      key={agent.name}
                      className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 transition-colors duration-150 hover:bg-white/[0.02]"
                      variants={fastStaggerItem}
                    >
                      <span className="relative flex h-2 w-2 shrink-0">
                        <span className={`relative inline-flex h-2 w-2 rounded-full ${agent.available ? "bg-emerald-400" : "bg-zinc-600"}`} />
                      </span>
                      <span className="truncate text-xs text-muted-foreground flex-1">{agent.name}</span>
                      <span
                        className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${AGENT_TYPE_COLORS[agent.type] ?? "bg-zinc-500/15 text-zinc-500"}`}
                      >
                        {agent.type}
                      </span>
                    </motion.div>
                  ))}
                </motion.div>
              ) : (
                <SkeletonList rows={6} />
              )}
            </CardContent>
          </Card>

          {/* Fila de Publicacao */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Send className="h-4 w-4 text-primary" />
                Fila de Publicacao
              </CardTitle>
            </CardHeader>
            <CardContent>
              {queueSummary ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Total na fila</span>
                    <Badge variant="secondary" className="text-xs tabular-nums">{queueSummary.total}</Badge>
                  </div>
                  {Object.keys(queueSummary.by_status ?? {}).length > 0 ? (
                    <div className="space-y-1.5">
                      {Object.entries(queueSummary.by_status).map(([statusKey, count]) => (
                        <div key={statusKey} className="flex items-center justify-between">
                          <span
                            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PUBLISH_STATUS_COLORS[statusKey] ?? "bg-zinc-500/15 text-zinc-400 border-zinc-500/20"}`}
                          >
                            {statusKey}
                          </span>
                          <span className="text-xs text-muted-foreground tabular-nums">{count}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground/60">Nenhum item na fila</p>
                  )}
                </div>
              ) : (
                <SkeletonList rows={3} />
              )}
            </CardContent>
          </Card>

          {/* Ultimas Execucoes */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4 text-primary" />
                Ultimas Execucoes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runs && runs.runs.length > 0 ? (
                <motion.div className="space-y-1.5" variants={fastStaggerContainer} initial="initial" animate="animate">
                  {runs.runs.slice(0, 5).map((run) => (
                    <motion.div
                      key={run.run_id}
                      className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2 transition-all duration-200 hover:bg-white/[0.04]"
                      variants={fastStaggerItem}
                    >
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="truncate font-mono text-xs tabular-nums text-muted-foreground">{run.run_id.slice(0, 12)}</p>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="secondary"
                            className={`text-[10px] ${
                              run.status === "completed"
                                ? "bg-emerald-500/15 text-emerald-400"
                                : run.status === "running"
                                ? "bg-amber-500/15 text-amber-400"
                                : run.status === "error"
                                ? "bg-rose-500/15 text-rose-400"
                                : ""
                            }`}
                          >
                            {run.status}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">{run.packages_produced} pacotes</span>
                        </div>
                      </div>
                      {run.duration_seconds != null && (
                        <span className="ml-2 shrink-0 text-[10px] text-muted-foreground/60 tabular-nums">
                          {run.duration_seconds.toFixed(1)}s
                        </span>
                      )}
                    </motion.div>
                  ))}
                </motion.div>
              ) : (
                <p className="text-sm text-muted-foreground/60">Nenhuma execucao registrada</p>
              )}
            </CardContent>
          </Card>

          {/* Storage + Jobs row */}
          {(driveHealth || jobsData) && (
            <div className="grid gap-4 grid-cols-2">
              {driveHealth && (
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <HardDrive className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs font-medium text-muted-foreground">Storage</span>
                    </div>
                    <p className="text-lg font-bold tabular-nums">
                      {driveHealth.output_exists ? driveHealth.total_images : 0}
                    </p>
                    <p className="text-[10px] text-muted-foreground/50">imagens</p>
                  </CardContent>
                </Card>
              )}
              {jobsData && (
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Palette className="h-3.5 w-3.5 text-muted-foreground/60" />
                      <span className="text-xs font-medium text-muted-foreground">Jobs</span>
                    </div>
                    <p className="text-lg font-bold tabular-nums">{jobsRunning}/{jobsData.total}</p>
                    <p className="text-[10px] text-muted-foreground/50">rodando</p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function usageBarColor(pct: number): string {
  if (pct < 60) return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]";
  if (pct < 85) return "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]";
  return "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.3)]";
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2 transition-all duration-200 hover:bg-white/[0.04]">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1.5">
        {ok !== undefined && (
          <span className="relative flex h-1.5 w-1.5">
            <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-400"}`} />
          </span>
        )}
        <span className="text-xs font-medium tabular-nums">{value}</span>
      </div>
    </div>
  );
}
