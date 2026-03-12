"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, RefreshCw, Zap, Loader2, Activity, Wifi, WifiOff } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgents } from "@/hooks/use-api";
import { fetchAgent, type AgentInfo, type FetchResult } from "@/lib/api";
import { getAgentPersona } from "@/components/agents/agent-config";
import { AgentModal } from "@/components/agents/agent-modal";

// ── Agent card ───────────────────────────────────────────────────────────────

function AgentCard({
  agent,
  index,
  isFetching,
  onFetch,
}: {
  agent: AgentInfo;
  index: number;
  isFetching: boolean;
  onFetch: () => void;
}) {
  const persona = getAgentPersona(agent.name);
  const Icon = persona.icon;
  const isOnline = agent.available;
  const isSource = agent.type === "source";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: index * 0.06,
        type: "spring",
        stiffness: 200,
        damping: 20,
      }}
      whileHover={{ y: -4 }}
    >
      <Card
        className={`
          group relative overflow-hidden transition-all duration-300
          hover:border-white/10
          ${isFetching ? "ring-1" : ""}
        `}
        style={{
          boxShadow: isFetching ? `0 0 30px ${persona.glowColor}` : undefined,
          borderColor: isFetching ? persona.accentHex + "50" : undefined,
        }}
      >
        {/* Gradient accent top */}
        <div
          className={`absolute inset-x-0 top-0 h-0.5 transition-opacity duration-300 ${
            isOnline ? "opacity-100" : "opacity-30"
          }`}
          style={{ backgroundColor: persona.accentHex }}
        />

        {/* Hover glow effect */}
        <div
          className={`absolute inset-0 bg-gradient-to-b ${persona.bgGradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
        />

        <CardContent className="relative p-5 space-y-4">
          {/* ── Top row: icon + name + status ─────────────────────────── */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <motion.div
                className={`flex h-11 w-11 items-center justify-center rounded-xl ${persona.iconBg} transition-all duration-300`}
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
              >
                {isFetching ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Icon className="h-5 w-5" style={{ color: persona.accentHex }} />
                  </motion.div>
                ) : (
                  <Icon className="h-5 w-5" style={{ color: persona.accentHex }} />
                )}
              </motion.div>
              <div>
                <h3 className="text-sm font-semibold">{persona.label}</h3>
                <p className="text-[11px] text-muted-foreground leading-tight mt-0.5">
                  {persona.description}
                </p>
              </div>
            </div>

            {/* Status indicator */}
            <motion.div
              className="flex items-center gap-1.5 shrink-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 + index * 0.06 }}
            >
              {isOnline ? (
                <>
                  <motion.div
                    className="h-2 w-2 rounded-full bg-emerald-500"
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                  <Wifi className="h-3 w-3 text-emerald-500/70" />
                </>
              ) : (
                <>
                  <div className="h-2 w-2 rounded-full bg-zinc-600" />
                  <WifiOff className="h-3 w-3 text-zinc-600" />
                </>
              )}
            </motion.div>
          </div>

          {/* ── Type badge ─────────────────────────────────────────────── */}
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={`text-[10px] ${persona.badgeClass}`}>
              {agent.type}
            </Badge>
            {isOnline && isSource && (
              <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                <Activity className="h-2.5 w-2.5 mr-1" />
                pronto
              </Badge>
            )}
          </div>

          {/* ── Fetch button ───────────────────────────────────────────── */}
          <motion.div whileTap={{ scale: 0.98 }}>
            <Button
              variant="outline"
              size="sm"
              className={`
                w-full gap-2 transition-all duration-300
                ${isFetching ? "" : "hover:border-white/20"}
              `}
              style={{
                borderColor: isFetching ? persona.accentHex + "40" : undefined,
                color: isFetching ? persona.accentHex : undefined,
              }}
              onClick={onFetch}
              disabled={isFetching || !isOnline || !isSource}
            >
              <AnimatePresence mode="wait">
                {isFetching ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    className="flex items-center gap-2"
                  >
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Buscando...</span>
                  </motion.div>
                ) : (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    className="flex items-center gap-2"
                  >
                    <Zap className="h-3.5 w-3.5" />
                    <span>Fetch</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </motion.div>

          {/* Fetching progress bar */}
          <AnimatePresence>
            {isFetching && (
              <motion.div
                className="h-0.5 rounded-full overflow-hidden bg-secondary"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: persona.accentHex }}
                  animate={{ x: ["-100%", "400%"] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const { data: agents, isLoading, mutate } = useAgents();
  const [fetchResult, setFetchResult] = useState<{
    agent: string;
    data: FetchResult | { error: string };
  } | null>(null);
  const [fetching, setFetching] = useState<string | null>(null);

  const handleFetch = useCallback(
    async (name: string) => {
      setFetching(name);
      try {
        const result = await fetchAgent(name);
        setFetchResult({ agent: name, data: result });
        mutate();
      } catch (err) {
        setFetchResult({
          agent: name,
          data: { error: err instanceof Error ? err.message : "Erro desconhecido" },
        });
      } finally {
        setFetching(null);
      }
    },
    [mutate]
  );

  const handleCloseModal = useCallback(() => {
    setFetchResult(null);
  }, []);

  const onlineCount = agents?.filter((a) => a.available).length ?? 0;
  const sourceCount = agents?.filter((a) => a.type === "source").length ?? 0;

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Agentes
          </h2>
          <p className="text-sm text-muted-foreground">
            {agents
              ? `${onlineCount} online de ${agents.length} agentes — ${sourceCount} fontes de dados`
              : "Carregando agentes..."}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => mutate()}
          className="gap-2"
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Atualizar
        </Button>
      </div>

      {/* ── Status summary ──────────────────────────────────────────── */}
      {agents && agents.length > 0 && (
        <motion.div
          className="flex gap-3 flex-wrap"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5">
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-xs text-emerald-400 font-medium">{onlineCount} online</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-secondary/50 border border-border px-3 py-1.5">
            <Activity className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">{sourceCount} fontes</span>
          </div>
          {agents.length - onlineCount > 0 && (
            <div className="flex items-center gap-2 rounded-lg bg-zinc-800/50 border border-zinc-700/50 px-3 py-1.5">
              <WifiOff className="h-3 w-3 text-zinc-500" />
              <span className="text-xs text-zinc-500">{agents.length - onlineCount} offline</span>
            </div>
          )}
        </motion.div>
      )}

      {/* ── Agent grid ──────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 rounded-xl" />
          ))}
        </div>
      ) : agents && agents.length > 0 ? (
        <motion.div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          layout
        >
          {agents.map((agent, idx) => (
            <AgentCard
              key={agent.name}
              agent={agent}
              index={idx}
              isFetching={fetching === agent.name}
              onFetch={() => handleFetch(agent.name)}
            />
          ))}
        </motion.div>
      ) : (
        <motion.div
          className="flex flex-col items-center justify-center py-16 gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Bot className="h-12 w-12 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">Nenhum agente encontrado</p>
          <Button variant="outline" size="sm" onClick={() => mutate()} className="gap-2">
            <RefreshCw className="h-3.5 w-3.5" />
            Tentar novamente
          </Button>
        </motion.div>
      )}

      {/* ── Agent modal (personalized per agent) ───────────────────── */}
      <AgentModal
        agentName={fetching}
        fetchResult={fetchResult}
        isFetching={!!fetching}
        onClose={handleCloseModal}
      />
    </div>
  );
}
