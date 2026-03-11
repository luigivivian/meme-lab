"use client";

import { Image, Bot, Workflow, TrendingUp, Play, HardDrive, Palette, Loader2, CheckCircle2 } from "lucide-react";
import { StatsCard } from "@/components/panels/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { IndeterminateProgress } from "@/components/ui/progress";
import { useStatus, useAgents, useLatestImages, usePipelineRuns, useDriveHealth, useJobs } from "@/hooks/use-api";
import { usePipeline } from "@/hooks/use-pipeline";
import { imageUrl } from "@/lib/api";

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useStatus();
  const { data: agents } = useAgents();
  const { data: latestData } = useLatestImages(4);
  const { data: runs } = usePipelineRuns();
  const { data: driveHealth } = useDriveHealth();
  const { data: jobsData } = useJobs();
  const pipeline = usePipeline();

  const activeAgents = agents ? agents.filter((a) => a.available).length : 0;
  const totalImages = status?.total_images_generated ?? 0;
  const runCount = runs ? Object.keys(runs).length : 0;
  const latestImages = latestData?.images ?? [];
  const jobsRunning = jobsData?.jobs.filter((j) => j.status === "running").length ?? 0;

  const handleQuickRun = () => {
    pipeline.run({ count: 5, use_gemini_image: true, use_phrase_context: true });
  };

  return (
    <div className="space-y-6 animate-page-in">
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
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {latestImages.map((img, idx) => (
                <div
                  key={img.filename}
                  className="stagger-item group relative aspect-[4/5] overflow-hidden rounded-xl border bg-secondary"
                  style={{ animationDelay: `${idx * 60}ms` }}
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
                </div>
              ))}
            </div>
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
