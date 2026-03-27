"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Video, ChevronDown, ChevronUp, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useVideoList, useVideoProgress } from "@/hooks/use-api";
import { imageUrl, type VideoListItem } from "@/lib/api";

function ProgressRow({ v }: { v: VideoListItem }) {
  const { data } = useVideoProgress(v.content_package_id, v.video_status === "generating");
  const pct = data?.progress ?? 0;
  const state = data?.state ?? "waiting";

  const stateLabel: Record<string, string> = {
    waiting: "Na fila",
    processing: "Processando",
    running: "Gerando",
    completed: "Finalizando",
    failed: "Falhou",
  };

  return (
    <div className="flex items-center gap-3">
      {v.image_path && (
        <img
          src={imageUrl(v.image_path.split(/[/\\]/).pop() ?? "")}
          alt=""
          className="h-8 w-8 rounded object-cover flex-shrink-0"
        />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground truncate">
            {v.phrase || v.topic || `#${v.content_package_id}`}
          </p>
          <span className="text-[10px] text-muted-foreground/70 ml-2 flex-shrink-0 tabular-nums">
            {pct > 0 ? `${pct}%` : stateLabel[state] || state}
          </span>
        </div>
        <div className="mt-1 h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-violet-400 transition-all duration-700 ease-out"
            style={{ width: `${Math.max(pct, 3)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export function VideoProgressBar() {
  const { data } = useVideoList();
  const [expanded, setExpanded] = useState(false);

  const generating = data?.videos.filter((v) => v.video_status === "generating") ?? [];
  const recentDone = data?.videos.filter(
    (v) => v.video_status === "success" || v.video_status === "failed"
  ).slice(0, 3) ?? [];

  if (generating.length === 0 && recentDone.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        className="fixed bottom-4 right-4 z-50 w-80 rounded-xl border border-white/[0.08] bg-[var(--color-surface-1)]/95 backdrop-blur-xl shadow-2xl shadow-black/40"
      >
        {/* Header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between px-4 py-2.5 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Video className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">
              {generating.length > 0
                ? `Gerando ${generating.length} video${generating.length > 1 ? "s" : ""}...`
                : "Videos recentes"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {generating.length > 0 && (
              <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
            )}
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </button>

        {/* Active generations with real progress */}
        {generating.length > 0 && (
          <div className="px-4 pb-2 space-y-2">
            {generating.map((v) => (
              <ProgressRow key={v.content_package_id} v={v} />
            ))}
          </div>
        )}

        {/* Expanded: recent completed/failed */}
        <AnimatePresence>
          {expanded && recentDone.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-white/[0.06]"
            >
              <div className="px-4 py-2 space-y-1.5">
                {recentDone.map((v) => (
                  <div key={v.content_package_id} className="flex items-center gap-2 text-xs">
                    {v.video_status === "success" ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0" />
                    )}
                    <span className="text-muted-foreground truncate">
                      {v.phrase || v.topic || `#${v.content_package_id}`}
                    </span>
                    <span className={`ml-auto flex-shrink-0 ${v.video_status === "success" ? "text-emerald-400" : "text-rose-400"}`}>
                      {v.video_status === "success" ? "Pronto" : "Falhou"}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </AnimatePresence>
  );
}
