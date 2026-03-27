"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Film,
  Download,
  ThumbsUp,
  Trash2,
  Loader2,
  Play,
  X,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useVideoGallery, useVideoModels } from "@/hooks/use-api";
import {
  videoFileUrl,
  imageUrl,
  deleteVideo,
  approveVideo,
  type VideoListItem,
} from "@/lib/api";

/* ── Helpers ─────────────────────────────────────────────────────────── */

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/* ── VideoCard (inline component) ────────────────────────────────────── */

function VideoCard({
  video,
  expanded,
  onToggleExpand,
  onApprove,
  approvingId,
  onDelete,
}: {
  video: VideoListItem;
  expanded: boolean;
  onToggleExpand: () => void;
  onApprove: (id: number) => void;
  approvingId: number | null;
  onDelete: (id: number) => void;
}) {
  const filename = (video.image_path ?? "").split(/[/\\]/).pop() ?? "";
  const model = video.video_metadata?.model as string | undefined;
  const duration = video.video_metadata?.duration as number | undefined;
  const costUsd = video.video_metadata?.cost_usd as number | undefined;
  const approved = video.video_metadata?.approved === true;

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.04] bg-card transition-all hover:border-white/[0.08]">
      {/* Thumbnail / Player area */}
      <div
        className="relative aspect-video cursor-pointer bg-secondary"
        onClick={onToggleExpand}
      >
        {expanded && video.video_status === "success" ? (
          <div className="relative">
            <video
              src={videoFileUrl(video.content_package_id)}
              controls
              autoPlay
              className="w-full aspect-video rounded-t-xl bg-black"
            />
            <button
              className="absolute top-2 right-2 rounded-full bg-black/60 p-1 hover:bg-black/80 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand();
              }}
            >
              <X className="h-4 w-4 text-white" />
            </button>
          </div>
        ) : (
          <>
            <img
              src={imageUrl(filename)}
              alt=""
              className="h-full w-full object-cover"
            />
            {/* Play overlay */}
            {video.video_status === "success" && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="flex items-center justify-center h-12 w-12 rounded-full bg-primary/80 backdrop-blur-sm">
                  <Play className="h-5 w-5 text-white ml-0.5" />
                </div>
              </div>
            )}
          </>
        )}

        {/* Status badge — top-left */}
        {!expanded && (
          <div className="absolute top-2 left-2">
            {video.video_status === "success" ? (
              <Badge
                variant="secondary"
                className="gap-1 bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
              >
                <CheckCircle className="h-3 w-3" />
                Concluido
              </Badge>
            ) : video.video_status === "failed" ? (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" />
                Falhou
              </Badge>
            ) : video.video_status === "generating" ? (
              <Badge
                variant="secondary"
                className="gap-1 bg-amber-500/20 text-amber-400 border-amber-500/30"
              >
                <Loader2 className="h-3 w-3 animate-spin" />
                Gerando
              </Badge>
            ) : null}
          </div>
        )}

        {/* Model badge — top-right */}
        {!expanded && model && (
          <div className="absolute top-2 right-2">
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold backdrop-blur-sm bg-blue-500/20 text-blue-400 border border-blue-500/30">
              {model.split("/").pop()}
            </span>
          </div>
        )}

        {/* Duration — bottom-left */}
        {!expanded && duration != null && (
          <span className="absolute bottom-2 left-2 inline-flex items-center rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
            {duration}s
          </span>
        )}

        {/* BRL cost — bottom-right */}
        {!expanded && costUsd != null && (
          <span className="absolute bottom-2 right-2 inline-flex items-center rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
            R$ {(costUsd * 5.5).toFixed(2)}
          </span>
        )}
      </div>

      {/* Card body */}
      <div className="p-3 space-y-2">
        <p className="text-xs line-clamp-2 leading-snug">{video.phrase}</p>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          {video.topic && <span>{video.topic}</span>}
          {video.created_at && <span>{formatDate(video.created_at)}</span>}
        </div>

        {/* Aprovado badge */}
        {approved && (
          <Badge
            variant="secondary"
            className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px]"
          >
            Aprovado
          </Badge>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-1.5 pt-1">
          {video.video_status === "success" && (
            <a
              href={videoFileUrl(video.content_package_id)}
              download
              onClick={(e) => e.stopPropagation()}
              className="flex-1"
            >
              <Button
                size="sm"
                variant="outline"
                className="w-full gap-1 h-7 text-xs"
              >
                <Download className="h-3 w-3" />
                Baixar
              </Button>
            </a>
          )}
          {video.video_status === "success" && (
            <Button
              size="sm"
              variant="outline"
              className={`flex-1 gap-1 h-7 text-xs ${
                approved
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : ""
              }`}
              onClick={() => onApprove(video.content_package_id)}
              disabled={approvingId === video.content_package_id}
            >
              {approvingId === video.content_package_id ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <ThumbsUp className="h-3 w-3" />
              )}
              {approved ? "Aprovado" : "Aprovar"}
            </Button>
          )}
          {video.video_status != null && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 w-7 p-0 text-rose-400 border-rose-500/20 hover:bg-rose-500/10"
              onClick={() => onDelete(video.content_package_id)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────────── */

export default function VideosPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [modelFilter, setModelFilter] = useState<string>("");
  const [expandedVideoId, setExpandedVideoId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  const { data, isLoading, mutate } = useVideoGallery({
    status: statusFilter || undefined,
    model: modelFilter || undefined,
    sort: "newest",
    limit: 50,
  });
  const { data: modelsData } = useVideoModels();
  const videos = data?.videos ?? [];

  /* ── Handlers ────────────────────────────────────────────────────── */

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteVideo(deleteTarget);
      mutate();
    } catch {
      // handled by SWR revalidation
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleApprove = async (id: number) => {
    setApprovingId(id);
    try {
      await approveVideo(id);
      mutate();
    } catch {
      // handled by SWR revalidation
    } finally {
      setApprovingId(null);
    }
  };

  /* ── Filter tabs ─────────────────────────────────────────────────── */

  const filterTabs = [
    { key: "", label: "Todos" },
    { key: "success", label: "Concluidos" },
    { key: "failed", label: "Falhados" },
  ];

  const modelList = modelsData?.models ?? [];

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Film className="h-5 w-5 text-primary" />
        <div>
          <h2 className="text-xl font-semibold">Videos Gerados</h2>
          <p className="text-sm text-muted-foreground">
            {data?.total ?? 0} videos
          </p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status tabs */}
        <div className="flex items-center gap-1.5 rounded-xl bg-secondary/30 p-1">
          {filterTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                statusFilter === tab.key
                  ? "bg-primary text-white shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/[0.04]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Model dropdown */}
        <Select
          value={modelFilter || "_all"}
          onValueChange={(v) => setModelFilter(v === "_all" ? "" : v)}
        >
          <SelectTrigger className="w-[200px] h-8 text-xs">
            <SelectValue placeholder="Todos os modelos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">Todos os modelos</SelectItem>
            {modelList.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.name || m.id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Video grid */}
      {isLoading ? (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video rounded-xl" />
          ))}
        </div>
      ) : videos.length > 0 ? (
        <motion.div
          className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {videos.map((v) => (
            <motion.div key={v.content_package_id} variants={staggerItem}>
              <VideoCard
                video={v}
                expanded={expandedVideoId === v.content_package_id}
                onToggleExpand={() =>
                  setExpandedVideoId((prev) =>
                    prev === v.content_package_id ? null : v.content_package_id
                  )
                }
                onApprove={handleApprove}
                approvingId={approvingId}
                onDelete={(id) => setDeleteTarget(id)}
              />
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
            <Film className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">
              Nenhum video gerado ainda. Gere videos a partir da pagina Gallery.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deletar Video</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Tem certeza que deseja deletar o video? Esta acao nao pode ser
            desfeita.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteTarget(null)}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
              className="gap-1"
            >
              {deleting && <Loader2 className="h-3 w-3 animate-spin" />}
              Deletar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
