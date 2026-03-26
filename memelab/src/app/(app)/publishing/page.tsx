"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Send,
  Calendar,
  Clock,
  ListFilter,
  ChevronLeft,
  ChevronRight,
  Plus,
  X as XIcon,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Ban,
  Zap,
  ExternalLink,
  Link as LinkIcon,
  Wifi,
  WifiOff,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { StatsCard } from "@/components/panels/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  usePublishingQueue,
  useQueueSummary,
  usePublishingCalendar,
  useBestTimes,
  useContentPackages,
  useInstagramStatus,
} from "@/hooks/use-api";
import {
  schedulePost,
  cancelScheduledPost,
  retryScheduledPost,
  imageUrl,
  type ScheduledPost,
  type CalendarDay,
} from "@/lib/api";
import { PUBLISH_STATUS_COLORS, PLATFORM_COLORS } from "@/lib/constants";

// -- Helpers -----------------------------------------------------------------

function extractFilename(path: string) {
  return path.split("/").pop()?.split("\\").pop() ?? path;
}

function formatDateBR(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDateTimeBR(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getWeekRange(offset: number) {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diffToMonday + offset * 7);
  monday.setHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);
  return { start: monday, end: sunday };
}

function getMonthRange(offset: number) {
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1);
  const last = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0);
  last.setHours(23, 59, 59, 999);
  return { start: first, end: last };
}

function toISODate(d: Date) {
  return d.toISOString().split("T")[0];
}

const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];
const DAY_KEYS_EN: Record<string, string> = {
  monday: "Seg",
  tuesday: "Ter",
  wednesday: "Qua",
  thursday: "Qui",
  friday: "Sex",
  saturday: "Sab",
  sunday: "Dom",
};

const STATUS_ICON: Record<string, typeof Clock> = {
  queued: Clock,
  publishing: Loader2,
  published: CheckCircle2,
  failed: AlertCircle,
  cancelled: Ban,
};

const STATUS_DOT_COLOR: Record<string, string> = {
  queued: "bg-amber-400",
  publishing: "bg-blue-400",
  published: "bg-emerald-400",
  failed: "bg-red-400",
  cancelled: "bg-zinc-400",
};

// -- Tab button --------------------------------------------------------------

function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:text-foreground hover:bg-secondary"
      }`}
    >
      {label}
    </button>
  );
}

// -- Status Badge ------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const colors = PUBLISH_STATUS_COLORS[status] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${colors}`}
    >
      {status}
    </span>
  );
}

function PlatformBadge({ platform }: { platform: string }) {
  const colors = PLATFORM_COLORS[platform] ?? "bg-zinc-500/20 text-zinc-400";
  return (
    <span
      className={`inline-flex items-center rounded-full border-transparent px-2 py-0.5 text-[10px] font-semibold ${colors}`}
    >
      {platform}
    </span>
  );
}

// -- Instagram Connection Banner ---------------------------------------------

function InstagramStatusBanner() {
  const { data: igStatus, isLoading } = useInstagramStatus();

  if (isLoading) return null;

  if (!igStatus?.connected) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
        <WifiOff className="h-4 w-4 text-amber-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-amber-300">
            Instagram nao conectado
          </p>
          <p className="text-xs text-amber-400/70">
            Conecte sua conta para publicar automaticamente
          </p>
        </div>
        <a
          href="/settings"
          className="shrink-0 rounded-lg bg-amber-500/20 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-amber-500/30 transition-colors"
        >
          Configuracoes
        </a>
      </div>
    );
  }

  return null;
}

function InstagramConnectedIndicator() {
  const { data: igStatus } = useInstagramStatus();

  if (!igStatus?.connected) return null;

  return (
    <div className="flex items-center gap-1.5">
      <div className="h-2 w-2 rounded-full bg-emerald-400" />
      <span className="text-xs text-emerald-400">
        @{igStatus.ig_username ?? "conectado"}
      </span>
    </div>
  );
}

// -- Queue Tab ---------------------------------------------------------------

function QueueTab() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [platformFilter, setPlatformFilter] = useState<string>("");
  const { data, isLoading, mutate } = usePublishingQueue({
    status: statusFilter || undefined,
    platform: platformFilter || undefined,
    limit: 50,
  });
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const posts = data?.items ?? [];

  const handleCancel = async (postId: number) => {
    setActionLoading(postId);
    try {
      await cancelScheduledPost(postId);
      mutate();
    } catch {
      // silent
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetry = async (postId: number) => {
    setActionLoading(postId);
    try {
      await retryScheduledPost(postId);
      mutate();
    } catch {
      // silent
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <ListFilter className="h-4 w-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 rounded-lg border bg-secondary px-3 text-xs text-foreground outline-none"
          >
            <option value="">Todos os status</option>
            <option value="queued">Agendado</option>
            <option value="publishing">Publicando</option>
            <option value="published">Publicado</option>
            <option value="failed">Falha</option>
            <option value="cancelled">Cancelado</option>
          </select>
        </div>
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value)}
          className="h-8 rounded-lg border bg-secondary px-3 text-xs text-foreground outline-none"
        >
          <option value="">Todas as plataformas</option>
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
        </select>
        <Button variant="ghost" size="sm" onClick={() => mutate()} className="gap-1 ml-auto">
          <RefreshCw className="h-3.5 w-3.5" />
          Atualizar
        </Button>
      </div>

      {/* Post List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : posts.length > 0 ? (
        <motion.div
          className="space-y-3"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {posts.map((post) => {
            const summary = post.content_summary;
            const filename = summary ? extractFilename(summary.image_path) : null;
            const Icon = STATUS_ICON[post.status] ?? Clock;
            const permalink = post.status === "published" && post.publish_result
              ? (post.publish_result as Record<string, unknown>)?.permalink as string | undefined
              : undefined;
            return (
              <motion.div
                key={post.id}
                className="flex items-center gap-4 rounded-xl bg-secondary/50 p-3 transition-colors duration-200 hover:bg-secondary/70"
                variants={staggerItem}
              >
                {/* Thumbnail */}
                {filename && (
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-secondary">
                    <img
                      src={imageUrl(filename)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  </div>
                )}

                {/* Info */}
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-sm line-clamp-1">
                    {summary?.phrase ?? `Post #${post.id}`}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <StatusBadge status={post.status} />
                    <PlatformBadge platform={post.platform} />
                    {post.character_name && (
                      <Badge variant="secondary" className="text-[10px]">
                        {post.character_name}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <Icon
                      className={`h-3 w-3 ${
                        post.status === "publishing" ? "animate-spin" : ""
                      }`}
                    />
                    <span>Agendado: {formatDateTimeBR(post.scheduled_at)}</span>
                    {post.published_at && (
                      <span>| Publicado: {formatDateTimeBR(post.published_at)}</span>
                    )}
                  </div>
                  {/* Permalink for published posts */}
                  {permalink && (
                    <a
                      href={permalink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] text-primary hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="truncate max-w-[200px]">Ver no Instagram</span>
                    </a>
                  )}
                  {post.error_message && (
                    <p className="text-[10px] text-destructive line-clamp-1">
                      {post.error_message}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex shrink-0 gap-2">
                  {post.status === "queued" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-destructive hover:text-destructive"
                      disabled={actionLoading === post.id}
                      onClick={() => handleCancel(post.id)}
                    >
                      {actionLoading === post.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <XIcon className="h-3.5 w-3.5" />
                      )}
                      Cancelar
                    </Button>
                  )}
                  {post.status === "failed" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-amber-400 hover:text-amber-300"
                      disabled={actionLoading === post.id}
                      onClick={() => handleRetry(post.id)}
                    >
                      {actionLoading === post.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3.5 w-3.5" />
                      )}
                      Retry
                    </Button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Send className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">Nenhum post na fila</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// -- Calendar Tab ------------------------------------------------------------

function CalendarTab() {
  const [viewMode, setViewMode] = useState<"week" | "month">("week");
  const [weekOffset, setWeekOffset] = useState(0);
  const [monthOffset, setMonthOffset] = useState(0);

  // Compute date range based on view mode
  const range = useMemo(() => {
    if (viewMode === "week") {
      return getWeekRange(weekOffset);
    }
    return getMonthRange(monthOffset);
  }, [viewMode, weekOffset, monthOffset]);

  const { data, isLoading } = usePublishingCalendar(toISODate(range.start), toISODate(range.end));

  // Build week view days
  const weekDays = useMemo(() => {
    if (viewMode !== "week") return [];
    const calPosts = data?.dates ?? {};
    const arr: { date: Date; key: string; label: string; posts: CalendarDay[] }[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(range.start);
      d.setDate(range.start.getDate() + i);
      const key = toISODate(d);
      arr.push({
        date: d,
        key,
        label: DAY_LABELS[i],
        posts: calPosts[key] ?? [],
      });
    }
    return arr;
  }, [data, range, viewMode]);

  // Build month view grid
  const monthGrid = useMemo(() => {
    if (viewMode !== "month") return [];
    const calPosts = data?.dates ?? {};
    const first = new Date(range.start);
    const year = first.getFullYear();
    const month = first.getMonth();

    // Day of week for first day (0=Sun, adjust so Mon=0)
    let firstDow = first.getDay() - 1;
    if (firstDow < 0) firstDow = 6;

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const totalCells = Math.ceil((firstDow + daysInMonth) / 7) * 7;

    const cells: { date: Date; key: string; dayNum: number; inMonth: boolean; posts: CalendarDay[] }[] = [];
    for (let i = 0; i < totalCells; i++) {
      const d = new Date(year, month, 1 - firstDow + i);
      const key = toISODate(d);
      const inMonth = d.getMonth() === month;
      cells.push({
        date: d,
        key,
        dayNum: d.getDate(),
        inMonth,
        posts: calPosts[key] ?? [],
      });
    }
    return cells;
  }, [data, range, viewMode]);

  const weekLabel = viewMode === "week"
    ? `${formatDateBR(range.start.toISOString())} - ${formatDateBR(range.end.toISOString())}`
    : range.start.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  const handlePrev = () => {
    if (viewMode === "week") setWeekOffset((w) => w - 1);
    else setMonthOffset((m) => m - 1);
  };

  const handleNext = () => {
    if (viewMode === "week") setWeekOffset((w) => w + 1);
    else setMonthOffset((m) => m + 1);
  };

  const handleReset = () => {
    if (viewMode === "week") setWeekOffset(0);
    else setMonthOffset(0);
  };

  const isOffsetZero = viewMode === "week" ? weekOffset === 0 : monthOffset === 0;

  return (
    <div className="space-y-4">
      {/* Navigation + View Toggle */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={handlePrev}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="text-center flex flex-col items-center gap-1">
          <p className="text-sm font-medium capitalize">{weekLabel}</p>
          {!isOffsetZero && (
            <button
              type="button"
              onClick={handleReset}
              className="text-[10px] text-primary hover:underline"
            >
              {viewMode === "week" ? "Voltar para esta semana" : "Voltar para este mes"}
            </button>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={handleNext}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* View mode toggle */}
      <div className="flex items-center gap-1 rounded-lg bg-secondary/50 p-0.5 w-fit mx-auto">
        <button
          type="button"
          onClick={() => setViewMode("week")}
          className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
            viewMode === "week"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Semana
        </button>
        <button
          type="button"
          onClick={() => setViewMode("month")}
          className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
            viewMode === "month"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Mes
        </button>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: viewMode === "week" ? 7 : 35 }).map((_, i) => (
            <Skeleton key={i} className={`${viewMode === "week" ? "h-32" : "h-20"} rounded-xl`} />
          ))}
        </div>
      ) : viewMode === "week" ? (
        /* Week view */
        <div className="grid grid-cols-7 gap-2">
          {weekDays.map((day) => {
            const isToday = toISODate(new Date()) === day.key;
            return (
              <div
                key={day.key}
                className={`min-h-[120px] rounded-xl border p-2 space-y-1.5 transition-colors ${
                  isToday
                    ? "border-primary/50 bg-primary/5"
                    : "bg-secondary/30 hover:bg-secondary/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    {day.label}
                  </span>
                  <span
                    className={`text-[11px] font-bold ${
                      isToday ? "text-primary" : "text-foreground"
                    }`}
                  >
                    {day.date.getDate()}
                  </span>
                </div>
                <div className="space-y-1 max-h-24 overflow-auto">
                  {day.posts.map((post) => {
                    const dotColor = STATUS_DOT_COLOR[post.status] ?? "bg-zinc-400";
                    const statusColor = PUBLISH_STATUS_COLORS[post.status] ?? "";
                    return (
                      <div
                        key={post.post_id}
                        className={`flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[9px] font-semibold truncate ${statusColor}`}
                        title={post.content_summary?.phrase ?? `#${post.post_id}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dotColor}`} />
                        {post.time.slice(0, 5)} {post.platform}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Month view */
        <div>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-2 mb-2">
            {DAY_LABELS.map((label) => (
              <div key={label} className="text-center text-[10px] font-medium text-muted-foreground">
                {label}
              </div>
            ))}
          </div>
          {/* Day cells */}
          <div className="grid grid-cols-7 gap-2">
            {monthGrid.map((cell) => {
              const isToday = toISODate(new Date()) === cell.key;
              return (
                <div
                  key={cell.key}
                  className={`min-h-[72px] rounded-lg border p-1.5 transition-colors ${
                    !cell.inMonth
                      ? "opacity-30 bg-secondary/10"
                      : isToday
                      ? "border-primary/50 bg-primary/5"
                      : "bg-secondary/30 hover:bg-secondary/50"
                  }`}
                >
                  <span
                    className={`text-[10px] font-bold block mb-1 ${
                      isToday ? "text-primary" : "text-foreground"
                    }`}
                  >
                    {cell.dayNum}
                  </span>
                  <div className="flex flex-wrap gap-0.5">
                    {cell.posts.map((post) => {
                      const dotColor = STATUS_DOT_COLOR[post.status] ?? "bg-zinc-400";
                      return (
                        <span
                          key={post.post_id}
                          className={`h-2 w-2 rounded-full ${dotColor}`}
                          title={`${post.time.slice(0, 5)} ${post.platform} - ${post.content_summary?.phrase ?? `#${post.post_id}`}`}
                        />
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// -- Best Times Tab ----------------------------------------------------------

function BestTimesTab() {
  const { data, isLoading } = useBestTimes();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-12 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
          <Clock className="h-8 w-8 text-muted-foreground" />
          <p className="text-muted-foreground">Sem dados de horarios</p>
        </CardContent>
      </Card>
    );
  }

  const entries = Object.entries(data) as [string, string[]][];

  return (
    <motion.div
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      variants={staggerContainer}
      initial="initial"
      animate="animate"
    >
      {entries.map(([dayKey, times]) => (
        <motion.div key={dayKey} variants={staggerItem}>
          <Card>
            <CardContent className="p-4 space-y-2">
              <p className="text-sm font-medium">
                {DAY_KEYS_EN[dayKey] ?? dayKey}
              </p>
              {times.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {times.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-medium"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground">Sem horario definido</p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  );
}

// -- Schedule Dialog ---------------------------------------------------------

function ScheduleDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSuccess: () => void;
}) {
  const { data: contentData } = useContentPackages(20);
  const { data: igStatus } = useInstagramStatus();
  const packages = contentData?.packages ?? [];

  const [selectedPkgId, setSelectedPkgId] = useState<number | null>(null);
  const [platform, setPlatform] = useState("instagram");
  const [scheduledAt, setScheduledAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const igNotConnected = platform === "instagram" && !igStatus?.connected;

  const handleSubmit = async () => {
    if (!selectedPkgId || !scheduledAt || igNotConnected) return;
    setSubmitting(true);
    setError(null);
    setSuccess(false);
    try {
      await schedulePost({
        content_package_id: selectedPkgId,
        platform,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
      setSuccess(true);
      onSuccess();
      setTimeout(() => {
        onOpenChange(false);
        setSuccess(false);
        setSelectedPkgId(null);
        setScheduledAt("");
      }, 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao agendar");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-[#1c1c22] border-white/10">
        <DialogHeader>
          <DialogTitle className="text-base">Agendar Publicacao</DialogTitle>
          <DialogDescription className="sr-only">
            Selecione conteudo, plataforma e horario para agendar
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Content Package Selector */}
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Conteudo</label>
            <div className="max-h-48 overflow-auto space-y-1.5 rounded-lg border p-2 bg-background/50">
              {packages.length > 0 ? (
                packages.map((pkg) => {
                  const fname = extractFilename(pkg.image_path);
                  const isSelected = selectedPkgId === pkg.id;
                  return (
                    <button
                      type="button"
                      key={pkg.id}
                      onClick={() => setSelectedPkgId(pkg.id)}
                      className={`flex items-center gap-3 w-full rounded-lg px-2 py-1.5 text-left transition-colors ${
                        isSelected
                          ? "bg-primary/20 border border-primary/40"
                          : "hover:bg-secondary/50"
                      }`}
                    >
                      <div className="h-10 w-10 shrink-0 overflow-hidden rounded-md bg-secondary">
                        <img
                          src={imageUrl(fname)}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs line-clamp-1">{pkg.phrase}</p>
                        <p className="text-[10px] text-muted-foreground">{pkg.topic}</p>
                      </div>
                      {isSelected && (
                        <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                      )}
                    </button>
                  );
                })
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">
                  Nenhum conteudo disponivel
                </p>
              )}
            </div>
          </div>

          {/* Platform */}
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Plataforma</label>
            <div className="flex gap-2">
              {["instagram", "tiktok"].map((p) => (
                <button
                  type="button"
                  key={p}
                  onClick={() => setPlatform(p)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    platform === p
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
            {/* Instagram connection status in dialog */}
            {platform === "instagram" && (
              igStatus?.connected ? (
                <p className="text-[11px] text-emerald-400 flex items-center gap-1">
                  <Wifi className="h-3 w-3" />
                  Conectado como @{igStatus.ig_username ?? "instagram"}
                </p>
              ) : (
                <p className="text-[11px] text-amber-400 flex items-center gap-1">
                  <WifiOff className="h-3 w-3" />
                  Conecte sua conta Instagram em Configuracoes primeiro
                </p>
              )
            )}
          </div>

          {/* Date/Time */}
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Data e Horario</label>
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="bg-secondary"
            />
          </div>

          {/* Error / Success */}
          {error && (
            <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
              <div className="h-2 w-2 rounded-full bg-destructive" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <p className="text-sm text-emerald-400">Agendado com sucesso!</p>
            </div>
          )}

          {/* Submit */}
          <Button
            onClick={handleSubmit}
            disabled={submitting || !selectedPkgId || !scheduledAt || igNotConnected}
            className={`w-full gap-2 ${submitting ? "pulse-glow" : ""}`}
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {submitting ? "Agendando..." : "Agendar Publicacao"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// -- Main Page ---------------------------------------------------------------

export default function PublishingPage() {
  const [activeTab, setActiveTab] = useState<"fila" | "calendario" | "horarios">("fila");
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const { data: summary } = useQueueSummary();
  const { mutate: mutateQueue } = usePublishingQueue();

  const queued = summary?.by_status?.queued ?? 0;
  const publishing = summary?.by_status?.publishing ?? 0;
  const published = summary?.by_status?.published ?? 0;
  const failed = summary?.by_status?.failed ?? 0;

  return (
    <div className="space-y-6">
      {/* Instagram connection warning banner */}
      <InstagramStatusBanner />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Send className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-semibold">Publicacao</h2>
              <InstagramConnectedIndicator />
            </div>
            <p className="text-sm text-muted-foreground">
              {summary?.total ?? 0} posts na fila
            </p>
          </div>
        </div>
        <Button className="gap-2" onClick={() => setScheduleOpen(true)}>
          <Plus className="h-4 w-4" />
          Agendar
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard title="Agendados" value={queued} icon={Clock} />
        <StatsCard title="Publicando" value={publishing} icon={Zap} />
        <StatsCard title="Publicados" value={published} icon={CheckCircle2} />
        <StatsCard title="Falhas" value={failed} icon={AlertCircle} />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 rounded-xl bg-secondary/50 p-1 w-fit">
        <TabButton
          label="Fila"
          active={activeTab === "fila"}
          onClick={() => setActiveTab("fila")}
        />
        <TabButton
          label="Calendario"
          active={activeTab === "calendario"}
          onClick={() => setActiveTab("calendario")}
        />
        <TabButton
          label="Horarios"
          active={activeTab === "horarios"}
          onClick={() => setActiveTab("horarios")}
        />
      </div>

      {/* Tab Content */}
      <Card>
        <CardContent className="p-6">
          {activeTab === "fila" && <QueueTab />}
          {activeTab === "calendario" && <CalendarTab />}
          {activeTab === "horarios" && <BestTimesTab />}
        </CardContent>
      </Card>

      {/* Schedule Dialog */}
      <ScheduleDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        onSuccess={() => mutateQueue()}
      />
    </div>
  );
}
