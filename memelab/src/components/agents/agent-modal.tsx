"use client";

import { useRef } from "react";
import { motion, AnimatePresence, type TargetAndTransition } from "framer-motion";
import { X, ExternalLink, TrendingUp, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAgentPersona, type AgentPersona } from "./agent-config";
import type { FetchResult, TrendItem } from "@/lib/api";

// ── Animated icon per agent type ──────────────────────────────────────────────

function AnimatedAgentIcon({ persona }: { persona: AgentPersona }) {
  const Icon = persona.icon;

  const variants: Record<string, TargetAndTransition> = {
    pulse: {
      scale: [1, 1.15, 1],
      opacity: [0.8, 1, 0.8],
      transition: { duration: 2, repeat: Infinity, ease: "easeInOut" },
    },
    orbit: {
      rotate: [0, 360],
      transition: { duration: 8, repeat: Infinity, ease: "linear" },
    },
    wave: {
      y: [0, -4, 0, 4, 0],
      transition: { duration: 2.5, repeat: Infinity, ease: "easeInOut" },
    },
    bounce: {
      y: [0, -8, 0],
      transition: { duration: 1.2, repeat: Infinity, ease: "easeOut" },
    },
    sparkle: {
      scale: [1, 1.2, 0.95, 1.1, 1],
      rotate: [0, 5, -5, 3, 0],
      transition: { duration: 2.5, repeat: Infinity, ease: "easeInOut" },
    },
    flame: {
      y: [0, -3, 0, -5, 0],
      scale: [1, 1.05, 1, 1.08, 1],
      transition: { duration: 1.8, repeat: Infinity, ease: "easeInOut" },
    },
  };

  return (
    <motion.div
      animate={variants[persona.animationType]}
      className="relative"
    >
      <Icon className="h-8 w-8" style={{ color: persona.accentHex }} />
      {/* Glow ring behind icon */}
      <motion.div
        className="absolute inset-0 rounded-full blur-xl"
        style={{ backgroundColor: persona.accentHex }}
        animate={{ opacity: [0.15, 0.35, 0.15] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      />
    </motion.div>
  );
}

// ── Floating particles (background decoration) ───────────────────────────────

function FloatingParticles({ color }: { color: string }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 6 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full"
          style={{ backgroundColor: color }}
          initial={{
            x: `${20 + Math.random() * 60}%`,
            y: `${20 + Math.random() * 60}%`,
            opacity: 0,
          }}
          animate={{
            y: [`${30 + Math.random() * 40}%`, `${10 + Math.random() * 30}%`],
            opacity: [0, 0.6, 0],
            scale: [0.5, 1.2, 0.5],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            repeat: Infinity,
            delay: i * 0.5,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// ── Result item row ──────────────────────────────────────────────────────────

function ResultItem({
  item,
  index,
  persona,
}: {
  item: TrendItem;
  index: number;
  persona: AgentPersona;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={{ delay: 0.15 + index * 0.05, type: "spring", stiffness: 200, damping: 20 }}
      whileHover={{ scale: 1.01, x: 4 }}
      className="group flex items-center justify-between rounded-xl bg-secondary/40 px-4 py-3 transition-colors hover:bg-secondary/60 border border-transparent hover:border-white/5"
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <motion.div
          className="h-1.5 w-1.5 rounded-full shrink-0"
          style={{ backgroundColor: persona.accentHex }}
          animate={{ scale: [1, 1.5, 1] }}
          transition={{ duration: 2, repeat: Infinity, delay: index * 0.2 }}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{item.title}</p>
          <p className="text-[11px] text-muted-foreground">{item.source}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-3">
        {item.score > 0 && (
          <Badge variant="outline" className={`text-[10px] ${persona.badgeClass}`}>
            {item.score}
          </Badge>
        )}
        {item.traffic && Number(item.traffic) > 0 && (
          <span className="text-[10px] text-emerald-400 flex items-center gap-0.5">
            <TrendingUp className="h-2.5 w-2.5" />
            {Number(item.traffic) > 1000
              ? `${(Number(item.traffic) / 1000).toFixed(0)}K`
              : item.traffic}
          </span>
        )}
        {item.url && (
          <motion.a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-0 group-hover:opacity-100 transition-opacity"
            whileHover={{ scale: 1.2 }}
            whileTap={{ scale: 0.9 }}
          >
            <ExternalLink className="h-3.5 w-3.5" style={{ color: persona.accentHex }} />
          </motion.a>
        )}
      </div>
    </motion.div>
  );
}

// ── Loading skeleton inside modal ─────────────────────────────────────────────

function FetchingAnimation({ persona }: { persona: AgentPersona }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-6">
      <div className="relative">
        <AnimatedAgentIcon persona={persona} />
        {/* Spinning ring */}
        <motion.div
          className="absolute -inset-4 rounded-full border-2 border-transparent"
          style={{ borderTopColor: persona.accentHex, borderRightColor: `${persona.accentHex}40` }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
        <motion.div
          className="absolute -inset-7 rounded-full border border-transparent"
          style={{ borderTopColor: `${persona.accentHex}30` }}
          animate={{ rotate: -360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />
      </div>
      <div className="text-center space-y-1">
        <motion.p
          className="text-sm font-medium"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          Buscando dados...
        </motion.p>
        <p className="text-xs text-muted-foreground">{persona.description}</p>
      </div>
      {/* Fake progress dots */}
      <div className="flex gap-1.5">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: persona.accentHex }}
            animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.2, 0.8] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Main modal ────────────────────────────────────────────────────────────────

interface AgentModalProps {
  agentName: string | null;
  fetchResult: { agent: string; data: FetchResult | { error: string } } | null;
  isFetching: boolean;
  onClose: () => void;
}

export function AgentModal({ agentName, fetchResult, isFetching, onClose }: AgentModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const name = agentName ?? fetchResult?.agent ?? "";
  const persona = getAgentPersona(name);
  const isOpen = isFetching || !!fetchResult;

  const fetchData = fetchResult?.data && "items" in fetchResult.data ? fetchResult.data : null;
  const fetchError = fetchResult?.data && "error" in fetchResult.data ? fetchResult.data.error : null;

  const Icon = persona.icon;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => {
            if (e.target === overlayRef.current) onClose();
          }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Modal */}
          <motion.div
            className="relative z-10 w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border bg-card overflow-hidden"
            initial={{ opacity: 0, scale: 0.9, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            style={{
              boxShadow: `0 0 60px ${persona.glowColor}, 0 0 120px ${persona.glowColor.replace("0.3", "0.1")}`,
            }}
          >
            {/* ── Header with gradient ──────────────────────────────────── */}
            <div className={`relative p-6 bg-gradient-to-b ${persona.bgGradient}`}>
              <FloatingParticles color={persona.accentHex} />

              {/* Close button */}
              <motion.button
                className="absolute right-4 top-4 p-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                onClick={onClose}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X className="h-4 w-4" />
              </motion.button>

              {/* Agent identity */}
              <div className="flex items-center gap-4 relative z-10">
                <motion.div
                  className={`flex h-14 w-14 items-center justify-center rounded-2xl ${persona.iconBg}`}
                  initial={{ scale: 0, rotate: -20 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.1 }}
                >
                  {isFetching ? (
                    <AnimatedAgentIcon persona={persona} />
                  ) : (
                    <Icon className="h-7 w-7" style={{ color: persona.accentHex }} />
                  )}
                </motion.div>

                <div>
                  <motion.h2
                    className="text-lg font-semibold"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 }}
                  >
                    {persona.label}
                  </motion.h2>
                  <motion.p
                    className="text-sm text-muted-foreground"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    {persona.description}
                  </motion.p>
                </div>

                {fetchData && (
                  <motion.div
                    className="ml-auto"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3, type: "spring" }}
                  >
                    <Badge className={`text-sm px-3 py-1 ${persona.badgeClass}`}>
                      {fetchData.count} items
                    </Badge>
                  </motion.div>
                )}
              </div>
            </div>

            {/* ── Body ──────────────────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto p-4">
              <AnimatePresence mode="wait">
                {isFetching && !fetchResult ? (
                  <motion.div
                    key="fetching"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, y: -10 }}
                  >
                    <FetchingAnimation persona={persona} />
                  </motion.div>
                ) : fetchError ? (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center justify-center py-10 gap-4"
                  >
                    <motion.div
                      className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 ring-1 ring-destructive/30"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 300 }}
                    >
                      <AlertCircle className="h-7 w-7 text-destructive" />
                    </motion.div>
                    <div className="text-center space-y-1">
                      <p className="text-sm font-medium text-destructive">Erro ao buscar dados</p>
                      <p className="text-xs text-muted-foreground max-w-md">{fetchError}</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={onClose}>
                      Fechar
                    </Button>
                  </motion.div>
                ) : fetchData ? (
                  <motion.div
                    key="results"
                    className="space-y-2"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    {fetchData.items.map((item, i) => (
                      <ResultItem
                        key={`${item.title}-${i}`}
                        item={item}
                        index={i}
                        persona={persona}
                      />
                    ))}

                    {fetchData.items.length === 0 && (
                      <motion.div
                        className="flex flex-col items-center py-10 gap-3"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      >
                        <Icon className="h-10 w-10 text-muted-foreground/30" />
                        <p className="text-sm text-muted-foreground">Nenhum item encontrado</p>
                      </motion.div>
                    )}
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>

            {/* ── Bottom accent line ────────────────────────────────────── */}
            <motion.div
              className="h-0.5"
              style={{ backgroundColor: persona.accentHex }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.3, duration: 0.5, ease: "easeOut" }}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
