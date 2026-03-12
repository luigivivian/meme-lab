"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Check,
  X,
  Upload,
  Sparkles,
  ImageIcon,
  Trash2,
  RotateCcw,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useCharacterRefs, useRefsGenerateStatus } from "@/hooks/use-api";
import * as api from "@/lib/api";
import type { RefInfo } from "@/lib/api";
import { mutate } from "swr";
import { staggerContainer, staggerItem } from "@/lib/animations";

type TabKey = "pending" | "approved" | "rejected";

const TABS: { key: TabKey; label: string; color: string }[] = [
  { key: "pending", label: "Pendentes", color: "text-amber-400" },
  { key: "approved", label: "Aprovadas", color: "text-emerald-400" },
  { key: "rejected", label: "Rejeitadas", color: "text-red-400" },
];

export default function RefsPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;

  const { data, isLoading } = useCharacterRefs(slug);
  const [activeTab, setActiveTab] = useState<TabKey>("pending");
  const [generating, setGenerating] = useState(false);
  const [focusIndex, setFocusIndex] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Poll generation status when generating
  const { data: genStatus } = useRefsGenerateStatus(slug, generating);

  // Auto-detect if generation is running
  useEffect(() => {
    if (genStatus && genStatus.status === "running") {
      setGenerating(true);
    }
    if (genStatus && genStatus.status === "completed" && generating) {
      setGenerating(false);
      revalidate();
    }
  }, [genStatus?.status]);

  const revalidate = useCallback(() => {
    mutate(`character-refs-${slug}`);
    mutate(`character-${slug}`);
    mutate("characters");
  }, [slug]);

  const filteredRefs = (data?.refs ?? []).filter((r) => r.status === activeTab);
  const stats = data?.stats;

  // Keyboard shortcuts
  useEffect(() => {
    if (focusIndex === null) return;
    const ref = filteredRefs[focusIndex];
    if (!ref) return;

    function handleKey(e: KeyboardEvent) {
      if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        handleApprove(ref.filename);
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        handleReject(ref.filename);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setFocusIndex((prev) =>
          prev !== null && prev < filteredRefs.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setFocusIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : prev));
      } else if (e.key === "Escape") {
        setFocusIndex(null);
      }
    }

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [focusIndex, filteredRefs]);

  async function handleApprove(filename: string) {
    setActionLoading(filename);
    try {
      await api.approveRef(slug, filename);
      revalidate();
    } catch (e) {
      console.error("Approve failed:", e);
    }
    setActionLoading(null);
    // Advance focus
    if (focusIndex !== null && focusIndex >= filteredRefs.length - 1) {
      setFocusIndex(filteredRefs.length > 1 ? focusIndex - 1 : null);
    }
  }

  async function handleReject(filename: string) {
    setActionLoading(filename);
    try {
      await api.rejectRef(slug, filename);
      revalidate();
    } catch (e) {
      console.error("Reject failed:", e);
    }
    setActionLoading(null);
    if (focusIndex !== null && focusIndex >= filteredRefs.length - 1) {
      setFocusIndex(filteredRefs.length > 1 ? focusIndex - 1 : null);
    }
  }

  async function handleDelete(filename: string) {
    setActionLoading(filename);
    try {
      await api.deleteRef(slug, filename);
      revalidate();
    } catch (e) {
      console.error("Delete failed:", e);
    }
    setActionLoading(null);
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      await api.generateCharacterRefs(slug, 15);
      // Switch to pending tab to see results
      setActiveTab("pending");
    } catch (e) {
      console.error("Generate failed:", e);
      setGenerating(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;

    const formData = new FormData();
    for (const file of Array.from(files)) {
      formData.append("files", file);
    }

    try {
      const res = await fetch(`/api/characters/${slug}/refs/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        revalidate();
        setActiveTab("pending");
      }
    } catch (e) {
      console.error("Upload failed:", e);
    }
    // Reset input
    e.target.value = "";
  }

  const approvedCount = stats?.approved ?? 0;
  const idealCount = stats?.ideal ?? 15;
  const minRequired = stats?.min_required ?? 5;
  const progressPercent = Math.min(100, (approvedCount / idealCount) * 100);
  const isReady = approvedCount >= minRequired;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/characters/${slug}`}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary hover:bg-secondary/80 transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Referencias</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie imagens de referencia para consistencia visual
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-secondary px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary/80">
            <Upload className="h-4 w-4" />
            Upload
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleUpload}
            />
          </label>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {generating ? "Gerando..." : "Gerar 15 Refs"}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="rounded-2xl border bg-card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">Referencias Aprovadas</span>
            {isReady && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/30">
                <Check className="h-3 w-3" />
                Pronto
              </span>
            )}
          </div>
          <span className="text-sm font-semibold">
            {approvedCount}/{idealCount}
            <span className="text-muted-foreground font-normal ml-1">
              (min: {minRequired})
            </span>
          </span>
        </div>
        <div className="h-3 rounded-full bg-secondary overflow-hidden">
          <motion.div
            className={cn(
              "h-full rounded-full",
              isReady ? "bg-emerald-500" : "bg-primary"
            )}
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </div>

        {/* Generation status */}
        {generating && genStatus && genStatus.status !== "none" && (
          <div className="mt-3 flex items-center gap-3 text-sm">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-muted-foreground">
              Gerando: {genStatus.done}/{genStatus.total} concluidas
              {genStatus.failed > 0 && (
                <span className="text-red-400 ml-1">
                  ({genStatus.failed} falhas)
                </span>
              )}
            </span>
          </div>
        )}

        {/* Stats row */}
        <div className="mt-3 grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold text-amber-400">
              {stats?.pending ?? 0}
            </p>
            <p className="text-[11px] text-muted-foreground">Pendentes</p>
          </div>
          <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold text-emerald-400">
              {stats?.approved ?? 0}
            </p>
            <p className="text-[11px] text-muted-foreground">Aprovadas</p>
          </div>
          <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold text-red-400">
              {stats?.rejected ?? 0}
            </p>
            <p className="text-[11px] text-muted-foreground">Rejeitadas</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 rounded-xl bg-secondary/50 p-1">
        {TABS.map((tab) => {
          const count = (data?.refs ?? []).filter(
            (r) => r.status === tab.key
          ).length;
          return (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                setFocusIndex(null);
              }}
              className={cn(
                "flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200",
                activeTab === tab.key
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}{" "}
              <span className={cn("ml-1", activeTab === tab.key && tab.color)}>
                ({count})
              </span>
            </button>
          );
        })}
      </div>

      {/* Focus mode */}
      <AnimatePresence>
        {focusIndex !== null && filteredRefs[focusIndex] && (
          <FocusView
            ref_={filteredRefs[focusIndex]}
            slug={slug}
            index={focusIndex}
            total={filteredRefs.length}
            tab={activeTab}
            loading={actionLoading === filteredRefs[focusIndex].filename}
            onApprove={() => handleApprove(filteredRefs[focusIndex].filename)}
            onReject={() => handleReject(filteredRefs[focusIndex].filename)}
            onPrev={() =>
              setFocusIndex((p) => (p !== null && p > 0 ? p - 1 : p))
            }
            onNext={() =>
              setFocusIndex((p) =>
                p !== null && p < filteredRefs.length - 1 ? p + 1 : p
              )
            }
            onClose={() => setFocusIndex(null)}
          />
        )}
      </AnimatePresence>

      {/* Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="aspect-[4/5] rounded-2xl bg-secondary animate-pulse"
            />
          ))}
        </div>
      ) : filteredRefs.length === 0 ? (
        <EmptyState tab={activeTab} onGenerate={handleGenerate} generating={generating} />
      ) : (
        <motion.div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {filteredRefs.map((ref, i) => (
            <motion.div key={ref.filename} variants={staggerItem}>
              <RefCard
                ref_={ref}
                slug={slug}
                tab={activeTab}
                focused={focusIndex === i}
                loading={actionLoading === ref.filename}
                onFocus={() => setFocusIndex(i)}
                onApprove={() => handleApprove(ref.filename)}
                onReject={() => handleReject(ref.filename)}
                onDelete={() => handleDelete(ref.filename)}
              />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Keyboard hints */}
      {filteredRefs.length > 0 && (
        <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
          <span>Clique para focar</span>
          <span className="flex items-center gap-1">
            <kbd className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-mono">
              A
            </kbd>{" "}
            Aprovar
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-mono">
              R
            </kbd>{" "}
            Rejeitar
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-mono">
              &larr; &rarr;
            </kbd>{" "}
            Navegar
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-mono">
              Esc
            </kbd>{" "}
            Fechar
          </span>
        </div>
      )}
    </div>
  );
}

function RefCard({
  ref_,
  slug,
  tab,
  focused,
  loading,
  onFocus,
  onApprove,
  onReject,
  onDelete,
}: {
  ref_: RefInfo;
  slug: string;
  tab: TabKey;
  focused: boolean;
  loading: boolean;
  onFocus: () => void;
  onApprove: () => void;
  onReject: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onFocus}
      className={cn(
        "group relative cursor-pointer rounded-2xl border bg-card overflow-hidden transition-all duration-200",
        focused
          ? "border-primary ring-2 ring-primary/20"
          : "hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
      )}
    >
      {/* Image */}
      <div className="relative aspect-[4/5] bg-secondary">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={api.refImageUrl(slug, ref_.filename)}
          alt={ref_.filename}
          className="h-full w-full object-cover"
          loading="lazy"
        />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <Loader2 className="h-8 w-8 animate-spin text-white" />
          </div>
        )}
      </div>

      {/* Info + actions */}
      <div className="p-3">
        <p className="text-xs text-muted-foreground truncate mb-2">
          {ref_.filename}
        </p>
        <div className="flex items-center gap-2">
          {tab === "pending" && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove();
                }}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" />
                Aprovar
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReject();
                }}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
                Rejeitar
              </button>
            </>
          )}
          {tab === "approved" && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReject();
                }}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
                Remover
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-lg bg-secondary px-2 py-1.5 text-xs text-muted-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          {tab === "rejected" && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove();
                }}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Restaurar
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-lg bg-secondary px-2 py-1.5 text-xs text-muted-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function FocusView({
  ref_,
  slug,
  index,
  total,
  tab,
  loading,
  onApprove,
  onReject,
  onPrev,
  onNext,
  onClose,
}: {
  ref_: RefInfo;
  slug: string;
  index: number;
  total: number;
  tab: TabKey;
  loading: boolean;
  onApprove: () => void;
  onReject: () => void;
  onPrev: () => void;
  onNext: () => void;
  onClose: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="relative flex flex-col items-center gap-4 p-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Counter */}
        <div className="text-sm text-white/60">
          {index + 1} de {total}
        </div>

        {/* Image */}
        <div className="relative max-h-[70vh] max-w-[500px] overflow-hidden rounded-2xl">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={api.refImageUrl(slug, ref_.filename)}
            alt={ref_.filename}
            className="h-full w-full object-contain"
          />
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50">
              <Loader2 className="h-10 w-10 animate-spin text-white" />
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-4">
          <button
            onClick={onPrev}
            disabled={index === 0}
            className="rounded-full bg-white/10 p-2 text-white hover:bg-white/20 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>

          {tab === "pending" && (
            <>
              <button
                onClick={onReject}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl bg-red-500/20 border border-red-500/30 px-6 py-3 text-sm font-medium text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                <X className="h-5 w-5" />
                Rejeitar (R)
              </button>
              <button
                onClick={onApprove}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 px-6 py-3 text-sm font-medium text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                <Check className="h-5 w-5" />
                Aprovar (A)
              </button>
            </>
          )}
          {tab === "approved" && (
            <button
              onClick={onReject}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-red-500/20 border border-red-500/30 px-6 py-3 text-sm font-medium text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
            >
              <X className="h-5 w-5" />
              Remover
            </button>
          )}
          {tab === "rejected" && (
            <button
              onClick={onApprove}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 px-6 py-3 text-sm font-medium text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
            >
              <RotateCcw className="h-5 w-5" />
              Restaurar
            </button>
          )}

          <button
            onClick={onNext}
            disabled={index === total - 1}
            className="rounded-full bg-white/10 p-2 text-white hover:bg-white/20 disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {/* Close hint */}
        <p className="text-xs text-white/40">
          Esc para fechar
        </p>
      </motion.div>
    </motion.div>
  );
}

function EmptyState({
  tab,
  onGenerate,
  generating,
}: {
  tab: TabKey;
  onGenerate: () => void;
  generating: boolean;
}) {
  const messages: Record<TabKey, { title: string; desc: string }> = {
    pending: {
      title: "Nenhuma ref pendente",
      desc: "Gere novas referencias ou faca upload de imagens.",
    },
    approved: {
      title: "Nenhuma ref aprovada",
      desc: "Aprove referencias pendentes para usar no pipeline.",
    },
    rejected: {
      title: "Nenhuma ref rejeitada",
      desc: "Referencias rejeitadas aparecem aqui.",
    },
  };

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
        <ImageIcon className="h-8 w-8 text-primary" />
      </div>
      <h3 className="text-lg font-semibold mb-2">{messages[tab].title}</h3>
      <p className="text-sm text-muted-foreground max-w-md mb-4">
        {messages[tab].desc}
      </p>
      {tab === "pending" && (
        <button
          onClick={onGenerate}
          disabled={generating}
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {generating ? "Gerando..." : "Gerar 15 Referencias"}
        </button>
      )}
    </div>
  );
}
