"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Image, Bot, Workflow, TrendingUp, HardDrive, Palette,
  Loader2, CheckCircle2, Clock, Package, Send, Activity, Gauge,
  Video, DollarSign, AlertTriangle, BarChart3,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar, PieChart, Pie, Cell,
} from "recharts";
import { staggerContainer, staggerItem, fastStaggerContainer, fastStaggerItem } from "@/lib/animations";
import { StatsCard } from "@/components/panels/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton, SkeletonCard, SkeletonList } from "@/components/ui/skeleton";
import { Progress, IndeterminateProgress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useStatus, useAgents, useLatestImages, usePipelineRuns,
  useDriveHealth, useJobs, useContentPackages, useQueueSummary, useUsage,
  useVideoBudget, useVideoStatus,
  useDashboardUsageHistory, useDashboardCostBreakdown,
  useDashboardPipelineActivity, useDashboardPublishingStats,
  useVideoCredits, useBusinessMetrics,
} from "@/hooks/use-api";
import { imageUrl, generateVideo, type ContentPackageDB, type UsageResponse, type VideoCreditsResponse } from "@/lib/api";
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

const VIDEO_STATUS_STYLES: Record<string, string> = {
  generating: "bg-amber-500/80 animate-pulse",
  success: "bg-cyan-500/80",
  failed: "bg-rose-500/80",
};

const VIDEO_STATUS_LABELS: Record<string, string> = {
  generating: "Gerando video...",
  success: "Video pronto",
  failed: "Video falhou",
};

const CHART_COLORS = {
  gemini_text: "#3b82f6",    // blue-500
  gemini_image: "#8b5cf6",   // violet-500
  kie_video: "#06b6d4",      // cyan-500
  gemini_web: "#10b981",     // emerald-500
};

const PIE_COLORS = ["#8b5cf6", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

const VIDEO_USD_TO_BRL = 5.75;

function computePercentChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return Math.round(((current - previous) / previous) * 100);
}

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useStatus();
  const { data: agents } = useAgents();
  const { data: latestData } = useLatestImages(4);
  const { data: runs } = usePipelineRuns();
  const { data: driveHealth } = useDriveHealth();
  const { data: jobsData } = useJobs();
  const { data: contentData, mutate: mutateContent } = useContentPackages(6);
  const { data: queueSummary } = useQueueSummary();
  const { data: usageData, isLoading: usageLoading } = useUsage();

  // Dashboard analytics hooks (Phase 16)
  const { data: usageHistory } = useDashboardUsageHistory();
  const { data: costBreakdown } = useDashboardCostBreakdown();
  const { data: pipelineActivity } = useDashboardPipelineActivity();
  const { data: publishingStats } = useDashboardPublishingStats();

  // Video credits (Phase 20)
  const { data: videoCredits } = useVideoCredits();

  // Business metrics (Phase 21)
  const { data: businessMetrics, isLoading: metricsLoading } = useBusinessMetrics();

  // Video generation state
  const [videoTarget, setVideoTarget] = useState<ContentPackageDB | null>(null);
  const [videoDuration, setVideoDuration] = useState<10 | 15>(10);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoSuccess, setVideoSuccess] = useState(false);
  const { data: budgetData } = useVideoBudget();
  const { data: pollingStatus } = useVideoStatus(
    videoTarget?.id ?? null,
    videoGenerating,
  );

  // Auto-detect when video generation finishes
  if (videoGenerating && pollingStatus?.video_status && pollingStatus.video_status !== "generating") {
    setVideoGenerating(false);
    if (pollingStatus.video_status === "success") {
      setVideoSuccess(true);
      mutateContent();
    } else {
      setVideoError("Geracao de video falhou");
    }
  }

  const handleGenerateVideo = async () => {
    if (!videoTarget) return;
    setVideoGenerating(true);
    setVideoError(null);
    setVideoSuccess(false);
    try {
      await generateVideo({
        content_package_id: videoTarget.id,
        duration: videoDuration,
      });
      // Polling via useVideoStatus will detect completion
    } catch (err) {
      setVideoGenerating(false);
      setVideoError(err instanceof Error ? err.message : "Erro ao gerar video");
    }
  };

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

  const costDataBRL = useMemo(() => {
    if (!costBreakdown?.services) return null;
    return costBreakdown.services.map(s => ({
      ...s,
      cost_brl: s.cost_usd * VIDEO_USD_TO_BRL,
    }));
  }, [costBreakdown]);

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-sm text-muted-foreground/70 mt-1">
          Visao geral do pipeline de memes
        </p>
      </div>

      {/* Stats Grid */}
      {metricsLoading ? (
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
            <StatsCard
              title="Videos Gerados"
              value={businessMetrics?.videos_generated.total ?? 0}
              icon={Video}
              iconClassName="bg-violet-500/10"
              description={`${businessMetrics?.active_packages.current ?? 0} pacotes ativos`}
              trend={businessMetrics ? {
                value: computePercentChange(
                  businessMetrics.videos_generated.current,
                  businessMetrics.videos_generated.previous
                ),
                label: "vs 7d anteriores",
              } : undefined}
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard
              title="Custo Medio/Video"
              value={formatBRL(businessMetrics?.avg_cost_per_video_brl.current ?? 0)}
              icon={DollarSign}
              iconClassName="bg-emerald-500/10"
              trend={businessMetrics ? {
                value: computePercentChange(
                  businessMetrics.avg_cost_per_video_brl.current,
                  businessMetrics.avg_cost_per_video_brl.previous
                ),
                label: "vs 7d anteriores",
              } : undefined}
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard
              title="Creditos Restantes"
              value={formatBRL(businessMetrics?.budget_remaining_brl.daily_remaining ?? 0)}
              icon={Gauge}
              iconClassName="bg-amber-500/10"
              description={`de ${formatBRL(businessMetrics?.budget_remaining_brl.daily_budget ?? 0)}/dia`}
            />
          </motion.div>
          <motion.div variants={staggerItem}>
            <StatsCard
              title="Trends Coletados"
              value={businessMetrics?.trends_collected.total ?? 0}
              icon={TrendingUp}
              iconClassName="bg-blue-500/10"
              trend={businessMetrics ? {
                value: computePercentChange(
                  businessMetrics.trends_collected.current,
                  businessMetrics.trends_collected.previous
                ),
                label: "vs 7d anteriores",
              } : undefined}
            />
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
                            {pkg.video_status && (
                              <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-sm ${VIDEO_STATUS_STYLES[pkg.video_status] ?? "bg-zinc-500/80"}`}>
                                <Video className="h-2.5 w-2.5" />
                                {VIDEO_STATUS_LABELS[pkg.video_status] ?? pkg.video_status}
                              </span>
                            )}
                            {pkg.is_published && (
                              <span className="inline-flex items-center rounded-full bg-emerald-500/80 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-sm">
                                Publicado
                              </span>
                            )}
                          </div>
                          {/* Video generate button on hover */}
                          {!pkg.video_status && (
                            <div className="absolute bottom-2 right-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                              <Button
                                size="sm"
                                variant="secondary"
                                className="h-7 text-[10px] gap-1 backdrop-blur-sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setVideoTarget(pkg);
                                  if (pkg.approval_status !== "approved") {
                                    setVideoError("Aprove o conteudo antes de gerar video");
                                  } else {
                                    setVideoError(null);
                                  }
                                  setVideoSuccess(false);
                                  setVideoDuration(10);
                                }}
                              >
                                <Video className="h-3 w-3" />
                                Gerar Video
                              </Button>
                            </div>
                          )}
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
                  <a href="/pipeline">
                    <Button variant="outline" size="sm" className="gap-2 mt-1">
                      <Workflow className="h-3.5 w-3.5" />
                      Ir para Pipeline
                    </Button>
                  </a>
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

      {/* Quota Alerts — per D-09, D-10, D-11 */}
      <QuotaAlerts usageData={usageData} />

      {/* Charts Section — per D-12, D-13 */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Uso 30 dias — stacked area chart */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4 text-primary" />
              Uso 30 dias
            </CardTitle>
          </CardHeader>
          <CardContent>
            {usageHistory ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={usageHistory.history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#71717a" }}
                    tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "#71717a" }} />
                  <Tooltip
                    contentStyle={{ background: "#1c1c22", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                    labelFormatter={(v) => String(v)}
                  />
                  <Area type="monotone" dataKey="gemini_text" stackId="1" fill={CHART_COLORS.gemini_text} stroke={CHART_COLORS.gemini_text} fillOpacity={0.3} name="Gemini Text" />
                  <Area type="monotone" dataKey="gemini_image" stackId="1" fill={CHART_COLORS.gemini_image} stroke={CHART_COLORS.gemini_image} fillOpacity={0.3} name="Gemini Image" />
                  <Area type="monotone" dataKey="kie_video" stackId="1" fill={CHART_COLORS.kie_video} stroke={CHART_COLORS.kie_video} fillOpacity={0.3} name="Kie Video" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-[250px] w-full" />
            )}
          </CardContent>
        </Card>

        {/* Custos por Servico — donut chart */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <DollarSign className="h-4 w-4 text-primary" />
              Custos por Servico
            </CardTitle>
          </CardHeader>
          <CardContent>
            {costDataBRL && costDataBRL.length > 0 ? (
              <div className="flex items-center justify-center">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={costDataBRL}
                      dataKey="cost_brl"
                      nameKey="service"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      label={({ name, value }: { name?: string; value?: number }) =>
                        `${(name ?? "").replace("_", " ")} ${formatBRL(value ?? 0)}`
                      }
                    >
                      {costDataBRL.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#1c1c22", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                      formatter={(v) => [formatBRL(Number(v)), "Custo"]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : costBreakdown ? (
              <div className="flex flex-col items-center justify-center py-12">
                <DollarSign className="h-8 w-8 text-muted-foreground/20 mb-2" />
                <p className="text-sm text-muted-foreground/60">Sem custos no periodo</p>
              </div>
            ) : (
              <Skeleton className="h-[250px] w-full" />
            )}
            {costBreakdown && (
              <div className="mt-2 text-center">
                <span className="text-xs text-muted-foreground">
                  Total 30 dias: <span className="font-medium text-foreground">{formatBRL(costBreakdown.total_cost_usd * VIDEO_USD_TO_BRL)}</span>
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Atividade do Pipeline — bar chart */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-primary" />
              Atividade do Pipeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pipelineActivity ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={pipelineActivity.activity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#71717a" }}
                    tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "#71717a" }} />
                  <Tooltip
                    contentStyle={{ background: "#1c1c22", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                    labelFormatter={(v) => String(v)}
                  />
                  <Bar dataKey="runs" fill="#7C3AED" radius={[4, 4, 0, 0]} name="Runs" />
                  <Bar dataKey="packages" fill="#a78bfa" radius={[4, 4, 0, 0]} name="Pacotes" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-[250px] w-full" />
            )}
          </CardContent>
        </Card>

        {/* Publicacao stats */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Send className="h-4 w-4 text-primary" />
              Publicacao
            </CardTitle>
          </CardHeader>
          <CardContent>
            {publishingStats ? (
              <div className="space-y-3">
                <div className="text-3xl font-bold tabular-nums">{publishingStats.total}</div>
                <p className="text-xs text-muted-foreground -mt-2">posts totais</p>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  {[
                    { label: "Publicados", value: publishingStats.published, color: "text-emerald-400" },
                    { label: "Na fila", value: publishingStats.queued, color: "text-amber-400" },
                    { label: "Falharam", value: publishingStats.failed, color: "text-rose-400" },
                    { label: "Cancelados", value: publishingStats.cancelled, color: "text-zinc-400" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-lg bg-white/[0.02] px-3 py-2">
                      <p className={`text-lg font-bold tabular-nums ${item.color}`}>{item.value}</p>
                      <p className="text-[10px] text-muted-foreground">{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Skeleton className="h-[200px] w-full" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Video Credits (Phase 20) */}
      {videoCredits && <VideoCreditsCard data={videoCredits} />}

      {/* Video Generation Dialog */}
      <Dialog
        open={!!videoTarget}
        onOpenChange={() => {
          if (!videoGenerating) {
            setVideoTarget(null);
            setVideoError(null);
            setVideoSuccess(false);
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Video className="h-4 w-4 text-primary" />
              Gerar Video
            </DialogTitle>
          </DialogHeader>
          {videoTarget && (
            <div className="space-y-4">
              {/* Preview */}
              <div className="flex gap-3 items-start">
                <div className="w-20 aspect-[4/5] overflow-hidden rounded-lg bg-secondary shrink-0">
                  <img
                    src={imageUrl(videoTarget.image_path.split(/[/\\]/).pop() ?? "")}
                    alt={videoTarget.phrase}
                    className="h-full w-full object-cover"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm line-clamp-2">{videoTarget.phrase}</p>
                  <p className="text-xs text-muted-foreground mt-1">{videoTarget.topic}</p>
                </div>
              </div>

              {/* Budget info */}
              {budgetData && (
                <div className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Orcamento hoje</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-medium tabular-nums">
                      {formatBRL(budgetData.remaining_usd * VIDEO_USD_TO_BRL)} restante
                    </span>
                    <span className="text-[10px] text-muted-foreground ml-1">
                      (~{budgetData.videos_remaining_estimate} videos)
                    </span>
                  </div>
                </div>
              )}

              {/* Duration selection */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Duracao</label>
                <div className="flex gap-2">
                  <Button
                    variant={videoDuration === 10 ? "default" : "outline"}
                    size="sm"
                    className="flex-1"
                    onClick={() => setVideoDuration(10)}
                    disabled={videoGenerating}
                  >
                    10s — R$ 0,86
                  </Button>
                  <Button
                    variant={videoDuration === 15 ? "default" : "outline"}
                    size="sm"
                    className="flex-1"
                    onClick={() => setVideoDuration(15)}
                    disabled={videoGenerating}
                  >
                    15s — R$ 1,32
                  </Button>
                </div>
              </div>

              {/* Generate button */}
              <Button
                onClick={handleGenerateVideo}
                disabled={videoGenerating || videoSuccess}
                className={`w-full gap-2 ${videoGenerating ? "pulse-glow" : ""}`}
              >
                {videoGenerating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : videoSuccess ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <Video className="h-4 w-4" />
                )}
                {videoGenerating
                  ? "Gerando video..."
                  : videoSuccess
                  ? "Video gerado!"
                  : "Gerar Video"}
              </Button>

              {/* Progress */}
              {videoGenerating && (
                <div className="space-y-2 animate-fade-in">
                  <IndeterminateProgress />
                  <p className="text-xs text-muted-foreground text-center">
                    Processando via Kie.ai Sora 2 (30-120s)...
                  </p>
                </div>
              )}

              {/* Success */}
              {videoSuccess && (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-emerald-400">Video gerado com sucesso!</p>
                </div>
              )}

              {/* Error */}
              {videoError && (
                <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                  <div className="h-2 w-2 rounded-full bg-destructive" />
                  <p className="text-sm text-destructive">{videoError}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
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

function QuotaAlerts({ usageData }: { usageData: UsageResponse | undefined }) {
  if (!usageData) return null;
  const alerts: { service: string; pct: number; level: "warning" | "critical" }[] = [];
  for (const svc of usageData.services) {
    if (svc.limit === 0) continue; // unlimited
    const pct = Math.round((svc.used / svc.limit) * 100);
    if (pct >= 95) alerts.push({ service: svc.service, pct, level: "critical" });
    else if (pct >= 80) alerts.push({ service: svc.service, pct, level: "warning" });
  }
  if (alerts.length === 0) return null;
  return (
    <div className="space-y-2">
      {alerts.map((a) => (
        <div
          key={a.service}
          className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm ${
            a.level === "critical"
              ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
              : "bg-amber-500/10 border-amber-500/20 text-amber-400"
          }`}
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            {a.service.replace("_", " ")} — {a.pct}% do limite diario
            {a.level === "critical" ? " (critico!)" : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

function formatBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function VideoCreditsCard({ data }: { data: VideoCreditsResponse }) {
  const [expanded, setExpanded] = useState(false);
  const visibleModels = expanded ? data.models : data.models.slice(0, 5);
  const budgetPct =
    data.daily_budget_brl > 0
      ? Math.round((data.daily_spent_brl / data.daily_budget_brl) * 100)
      : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <DollarSign className="h-4 w-4 text-primary" />
          Video Credits
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary row */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-muted-foreground">Total ({data.days}d)</p>
            <p className="text-lg font-bold font-mono">{formatBRL(data.total_spent_brl)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Videos</p>
            <p className="text-lg font-bold">{data.total_videos}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Media/video</p>
            <p className="text-lg font-bold font-mono">{formatBRL(data.avg_cost_brl)}</p>
          </div>
        </div>

        {/* Daily budget bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Orcamento diario</span>
            <span>
              {formatBRL(data.daily_spent_brl)} / {formatBRL(data.daily_budget_brl)}
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                budgetPct >= 95
                  ? "bg-rose-500"
                  : budgetPct >= 80
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(budgetPct, 100)}%` }}
            />
          </div>
        </div>

        {/* Per-model table */}
        {data.models.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted-foreground text-xs border-b border-border/50">
                <th className="text-left pb-2">Modelo</th>
                <th className="text-right pb-2">Videos</th>
                <th className="text-right pb-2">Total</th>
              </tr>
            </thead>
            <tbody>
              {visibleModels.map((m) => (
                <tr key={m.model_id} className="border-b border-border/20 last:border-0">
                  <td className="py-1.5 text-xs">{m.model_name}</td>
                  <td className="py-1.5 text-right tabular-nums">{m.count}</td>
                  <td className="py-1.5 text-right font-mono text-xs">
                    {formatBRL(m.total_brl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Expand toggle if >5 models */}
        {data.models.length > 5 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary hover:underline w-full text-center"
          >
            {expanded ? "Mostrar menos" : `Ver todos (${data.models.length})`}
          </button>
        )}

        {/* Failed count info */}
        {data.failed_count > 0 && (
          <p className="text-xs text-muted-foreground">
            {data.failed_count} geracoes falharam (custo zero)
          </p>
        )}

        {/* All-time stats */}
        <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t border-border/30">
          <span>Total historico: {formatBRL(data.alltime_spent_brl)}</span>
          <span>{data.alltime_videos} videos</span>
        </div>
      </CardContent>
    </Card>
  );
}
