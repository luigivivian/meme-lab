"use client";

import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import type { LayerStatus, PipelineRunResult } from "@/lib/api";

// ── Palette ───────────────────────────────────────────────────────────────────
const C = {
  bg:      "#06040f",
  panel:   "#08061a",
  gridSm:  "#0f0d22",
  gridLg:  "#141030",
  border:  "#241b48",
  text:    "#e8e0ff",
  dim:     "#4e4470",
  dimLt:   "#7060a8",
  violet:  "#a78bfa",
  indigo:  "#818cf8",
  blue:    "#60a5fa",
  cobalt:  "#3b82f6",
  lav:     "#c4b5fd",
  pink:    "#e879f9",
  peri:    "#93c5fd",
  idle:    "#3d3360",
  err:     "#f472b6",
  gold:    "#fbbf24",
  emerald: "#34d399",
} as const;

type Status = "idle" | "running" | "done" | "error";

const ST: Record<Status, { color: string; label: string; icon: string }> = {
  done:    { color: C.violet, label: "Done",    icon: "✓" },
  running: { color: C.pink,   label: "Running", icon: "◉" },
  idle:    { color: C.idle,   label: "Idle",    icon: "○" },
  error:   { color: C.err,    label: "Error",   icon: "✕" },
};

// ── Pipeline data ─────────────────────────────────────────────────────────────
interface StepDef { id: string; label: string; stub?: boolean }
interface LayerDef {
  id: string; label: string; desc: string;
  steps: StepDef[]; flow: "parallel" | "sequential"; output: string;
}

const COLORS = [C.cobalt, C.indigo, C.violet, C.pink, C.peri] as const;
const ICONS  = ["⬡", "⇌", "✦", "◈", "✧"]               as const;

const PIPELINE: LayerDef[] = [
  {
    id: "L1", label: "Monitoring", desc: "Fetch paralelo de trends",
    flow: "parallel", output: "TrendEvents",
    steps: [
      { id: "google_trends",     label: "Google Trends" },
      { id: "reddit_memes",      label: "Reddit RSS"    },
      { id: "rss_feeds",         label: "RSS Feeds"     },
      { id: "youtube_rss",       label: "YouTube RSS"   },
      { id: "gemini_web_trends", label: "Gemini Trends" },
      { id: "brazil_viral_rss",  label: "Brasil Viral"  },
      { id: "bluesky_trends",    label: "BlueSky"     },
      { id: "hackernews_rss",    label: "HackerNews"  },
      { id: "lemmy_communities", label: "Lemmy"       },
      { id: "tiktok_trends",     label: "TikTok",    stub: true },
      { id: "instagram_explore", label: "Instagram", stub: true },
      { id: "twitter_x",         label: "Twitter/X", stub: true },
    ],
  },
  {
    id: "L2", label: "Broker", desc: "Dedup + ranking",
    flow: "sequential", output: "Ranked Events",
    steps: [
      { id: "ingest", label: "Ingest Queue" },
      { id: "dedup",  label: "Dedup Filter" },
      { id: "rank",   label: "Rank & Sort"  },
    ],
  },
  {
    id: "L3", label: "Curator", desc: "Gemini seleciona",
    flow: "sequential", output: "WorkOrders",
    steps: [
      { id: "analyze",     label: "Gemini Analyzer" },
      { id: "keyword_map", label: "Keyword Map"     },
      { id: "work_orders", label: "WorkOrders"      },
    ],
  },
  {
    id: "L4", label: "Generation", desc: "Frases + backgrounds + composicao",
    flow: "parallel", output: "ContentPackages",
    steps: [
      { id: "phrases",    label: "PhraseWorker" },
      { id: "backgrounds", label: "BackgroundResolver" },
      { id: "compose",    label: "ImageComposer" },
    ],
  },
  {
    id: "L5", label: "Post-Prod", desc: "Enriquecimento",
    flow: "parallel", output: "Pacotes Finais",
    steps: [
      { id: "caption",  label: "CaptionWorker"  },
      { id: "hashtags", label: "HashtagWorker"  },
      { id: "quality",  label: "QualityWorker"  },
    ],
  },
];

// ── Canvas node ───────────────────────────────────────────────────────────────
interface CNode {
  id: string; x: number; y: number; w: number; h: number;
  label: string; sub: string; icon: string; color: string;
  pipelineIdx: number;
}

const NW = 168;
const NH = 88;

// Main nodes positioned in upper area; sub-nodes extend below
const STAGGER_Y = [20, -20, 30, -20, 20];
const BASE_Y    = 40;

const EDGES_DEF = [
  { id: "e1", from: "L1",     to: "L2"     },
  { id: "e2", from: "L2",     to: "L3"     },
  { id: "e3", from: "L3",     to: "L4"     },
  { id: "e4", from: "L4",     to: "L5"     },
  { id: "e5", from: "L5",     to: "output" },
];

const GAP = 52;

function makeNodes(): CNode[] {
  const nodes: CNode[] = PIPELINE.map((l, i) => ({
    id:          l.id,
    x:           20 + i * (NW + GAP),
    y:           BASE_Y + STAGGER_Y[i],
    w:           NW,
    h:           NH,
    label:       l.label,
    sub:         l.desc,
    icon:        ICONS[i],
    color:       COLORS[i],
    pipelineIdx: i,
  }));

  const lastX = 20 + 5 * (NW + GAP);
  nodes.push({
    id: "output", x: lastX, y: BASE_Y + 10,
    w: 140, h: 68,
    label: "Output", sub: "*.png + meta",
    icon: "◇", color: C.lav, pipelineIdx: -1,
  });
  return nodes;
}

function getStatus(id: string, layers?: Record<string, LayerStatus>): Status {
  if (id === "output") return layers?.L5?.status === "done" ? "done" : "idle";
  return (layers?.[id]?.status ?? "idle") as Status;
}

// ── Particle burst (sparkles on completion) ──────────────────────────────────
function ParticleBurst({
  cx, cy, color, id,
}: { cx: number; cy: number; color: string; id: string }) {
  // 8 particles radiating outward with staggered timing
  const particles = useMemo(() => {
    const count = 8;
    return Array.from({ length: count }, (_, i) => {
      const angle = (i / count) * Math.PI * 2;
      const dist = 12 + Math.random() * 8;
      const tx = Math.cos(angle) * dist;
      const ty = Math.sin(angle) * dist;
      const size = 1.2 + Math.random() * 1.5;
      const delay = i * 0.04;
      return { tx, ty, size, delay, angle };
    });
  }, []);

  return (
    <g>
      {particles.map((p, i) => (
        <circle key={`${id}-p${i}`}
          cx={cx} cy={cy} r={p.size}
          fill={color} opacity="0">
          <animate attributeName="cx" from={String(cx)} to={String(cx + p.tx)}
            dur="0.7s" begin={`${p.delay}s`} fill="freeze" />
          <animate attributeName="cy" from={String(cy)} to={String(cy + p.ty)}
            dur="0.7s" begin={`${p.delay}s`} fill="freeze" />
          <animate attributeName="opacity" values="0;1;0.8;0"
            dur="0.7s" begin={`${p.delay}s`} fill="freeze" />
          <animate attributeName="r" from={String(p.size)} to="0.3"
            dur="0.7s" begin={`${p.delay}s`} fill="freeze" />
        </circle>
      ))}
      {/* center flash */}
      <circle cx={cx} cy={cy} r="0" fill={color} opacity="0">
        <animate attributeName="r" values="0;6;0" dur="0.5s" fill="freeze" />
        <animate attributeName="opacity" values="0;0.6;0" dur="0.5s" fill="freeze" />
      </circle>
    </g>
  );
}

// ── Sub-node group with cascading animations ─────────────────────────────────
const SH   = 23;  // sub-node height
const SGAP = 5;   // vertical gap between sub-nodes
const STEM = 16;  // gap from parent bottom to first sub-node

// Delay per step activation (ms)
const SEQ_DELAY  = 1200; // sequential: 1.2s between each step
const PAR_DELAY  = 350;  // parallel: 0.35s stagger for spawn feel

type SubStepStatus = "idle" | "pending" | "scanning" | "running" | "done";

function SubNodeGroup({
  px, py, pw, ph, color, flow, steps, parentStatus, layerId,
}: {
  px: number; py: number; pw: number; ph: number;
  color: string; flow: "parallel" | "sequential";
  steps: StepDef[]; parentStatus: Status; layerId: string;
}) {
  const baseY = py + ph + STEM;
  const cx    = px + pw / 2;
  const isParallelFlow = flow === "parallel";
  const activeSteps = steps.filter(s => !s.stub);
  const delay = isParallelFlow ? PAR_DELAY : SEQ_DELAY;

  // Track per-step animation state internally
  const [stepStates, setStepStates] = useState<Record<string, SubStepStatus>>({});
  const prevParentStatus = useRef<Status>("idle");
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Cascade animation when parent transitions to running
  useEffect(() => {
    const wasIdle = prevParentStatus.current === "idle";
    prevParentStatus.current = parentStatus;

    // Clear any existing timers
    timersRef.current.forEach(t => clearTimeout(t));
    timersRef.current = [];

    if (parentStatus === "running" && wasIdle) {
      // Reset all to idle first
      const initial: Record<string, SubStepStatus> = {};
      steps.forEach(s => { initial[s.id] = s.stub ? "idle" : "pending"; });
      setStepStates(initial);

      // Cascade activation: pending → scanning → running → done
      activeSteps.forEach((step, i) => {
        const baseDelay = i * delay;

        // scanning phase
        timersRef.current.push(setTimeout(() => {
          setStepStates(prev => ({ ...prev, [step.id]: "scanning" }));
        }, baseDelay));

        // running phase
        timersRef.current.push(setTimeout(() => {
          setStepStates(prev => ({ ...prev, [step.id]: "running" }));
        }, baseDelay + 400));

        // For parallel, all finish around the same time at the end
        // For sequential, each finishes before the next starts
        if (!isParallelFlow && i < activeSteps.length - 1) {
          timersRef.current.push(setTimeout(() => {
            setStepStates(prev => ({ ...prev, [step.id]: "done" }));
          }, baseDelay + delay - 200));
        }
      });
    } else if (parentStatus === "done") {
      // All steps done
      const done: Record<string, SubStepStatus> = {};
      steps.forEach(s => { done[s.id] = s.stub ? "idle" : "done"; });
      setStepStates(done);
    } else if (parentStatus === "idle") {
      setStepStates({});
    } else if (parentStatus === "running" && !wasIdle) {
      // Already running — keep last running step active, don't reset
    }

    return () => {
      timersRef.current.forEach(t => clearTimeout(t));
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentStatus]);

  // Track which steps just completed (for particle burst)
  const [burstSteps, setBurstSteps] = useState<Set<string>>(new Set());
  const prevStatesRef = useRef<Record<string, SubStepStatus>>({});
  useEffect(() => {
    const newBursts = new Set<string>();
    for (const [id, st] of Object.entries(stepStates)) {
      if (st === "done" && prevStatesRef.current[id] !== "done") {
        newBursts.add(id);
      }
    }
    prevStatesRef.current = { ...stepStates };
    if (newBursts.size > 0) {
      setBurstSteps(prev => new Set([...prev, ...newBursts]));
      // Clear burst after animation completes
      const t = setTimeout(() => {
        setBurstSteps(prev => {
          const next = new Set(prev);
          newBursts.forEach(id => next.delete(id));
          return next;
        });
      }, 900);
      return () => clearTimeout(t);
    }
  }, [stepStates]);

  return (
    <g>
      {/* flow type label */}
      <text x={cx} y={py + ph + 10} textAnchor="middle"
        fontSize="6" fill={color} fontFamily="monospace"
        opacity="0.45" letterSpacing="0.12em">
        {isParallelFlow ? "∥  PARALLEL" : "→  SEQUENTIAL"}
      </text>

      {/* vertical stem from parent bottom */}
      <line x1={cx} y1={py + ph + 1} x2={cx} y2={baseY - 1}
        stroke={color} strokeWidth="0.7" strokeDasharray="2 3" opacity="0.32" />

      {/* energy pulse down the stem when running */}
      {parentStatus === "running" && (
        <circle r="1.8" fill={color} opacity="0">
          <animate attributeName="opacity" values="0;0.9;0" dur="1.2s" repeatCount="indefinite" />
          <animate attributeName="cy"
            from={String(py + ph + 1)} to={String(baseY - 1)}
            dur="1.2s" repeatCount="indefinite" />
          <animate attributeName="cx" values={`${cx};${cx}`} dur="1.2s" repeatCount="indefinite" />
        </circle>
      )}

      {steps.map((step, i) => {
        const sy = baseY + i * (SH + SGAP);
        const stepColor = step.stub ? C.dim : color;
        const ss = stepStates[step.id] ?? "idle";
        const isScanning = ss === "scanning";
        const isRunning  = ss === "running";
        const isDone     = ss === "done";
        const isPending  = ss === "pending";
        const hasBurst   = burstSteps.has(step.id);

        // Progress fill width for scanning/running
        const progressW = isDone ? pw : isRunning ? pw * 0.7 : isScanning ? pw * 0.3 : 0;

        return (
          <g key={step.id}>
            {/* inter-step connector */}
            {i > 0 && !isParallelFlow && (
              <g>
                <line x1={cx} y1={sy - SGAP} x2={cx} y2={sy}
                  stroke={color} strokeWidth="0.5" opacity="0.2" />
                {/* energy orb traveling between sequential steps */}
                {(isScanning || isRunning) && (
                  <circle r="1.4" fill={color} opacity="0">
                    <animate attributeName="opacity" values="0;1;0.6;0" dur="0.6s" fill="freeze" />
                    <animate attributeName="cy"
                      from={String(sy - SGAP)} to={String(sy)}
                      dur="0.6s" fill="freeze" />
                    <animate attributeName="cx" values={`${cx};${cx}`} dur="0.6s" fill="freeze" />
                  </circle>
                )}
              </g>
            )}
            {i > 0 && isParallelFlow && (
              <line x1={cx} y1={baseY - 1} x2={cx} y2={sy}
                stroke={color} strokeWidth="0.4" strokeDasharray="1.5 2.5" opacity="0.18" />
            )}

            {/* glow halo behind card when active */}
            {(isRunning || isScanning) && !step.stub && (
              <rect x={px - 2} y={sy - 2} width={pw + 4} height={SH + 4} rx="7"
                fill="none" stroke={color} strokeWidth="0.8"
                opacity={isRunning ? "0.4" : "0.2"}
                style={{ animation: isRunning ? "subNodeGlow 1.5s ease-in-out infinite" : undefined }}>
              </rect>
            )}

            {/* done glow ring — brief flash */}
            {isDone && !step.stub && hasBurst && (
              <rect x={px - 3} y={sy - 3} width={pw + 6} height={SH + 6} rx="8"
                fill="none" stroke={C.emerald} strokeWidth="1.2" opacity="0">
                <animate attributeName="opacity" values="0;0.7;0" dur="0.6s" fill="freeze" />
              </rect>
            )}

            <g opacity={step.stub ? 0.36 : 1}>
              {/* card background */}
              <rect x={px} y={sy} width={pw} height={SH} rx="5"
                fill={`${color}08`} stroke={`${color}26`} strokeWidth="0.7" />

              {/* scanning / running progress fill */}
              {!step.stub && progressW > 0 && (
                <rect x={px} y={sy} width={progressW} height={SH} rx="5"
                  fill={isDone ? `${C.emerald}12` : `${color}14`}
                  style={{
                    transition: "width 0.6s cubic-bezier(.4,0,.2,1)",
                  }}>
                  {isScanning && (
                    <animate attributeName="opacity" values="0.4;1;0.4" dur="0.8s" repeatCount="indefinite" />
                  )}
                </rect>
              )}

              {/* scanning shimmer bar (horizontal light sweep) */}
              {isScanning && !step.stub && (
                <rect x={px} y={sy} width="20" height={SH} rx="5"
                  fill={color} opacity="0.15">
                  <animate attributeName="x" from={String(px)} to={String(px + pw)}
                    dur="1s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.15;0.05;0.15" dur="1s" repeatCount="indefinite" />
                </rect>
              )}

              {/* left accent bar — glows when active */}
              <rect x={px} y={sy + 4} width="1.8" height={SH - 8} rx="0.9"
                fill={isDone ? C.emerald : stepColor}
                opacity={step.stub ? 0.22 : isDone ? 0.9 : isRunning ? 1 : isScanning ? 0.8 : 0.6}>
                {isRunning && (
                  <animate attributeName="opacity" values="0.7;1;0.7" dur="0.8s" repeatCount="indefinite" />
                )}
              </rect>

              {/* flow icon — animated states */}
              {isParallelFlow ? (
                <g>
                  <circle cx={px + 11} cy={sy + SH / 2} r="2.4"
                    fill={isDone ? C.emerald : stepColor}
                    opacity={step.stub ? 0.3 : isDone ? 0.9 : 0.65}>
                    {isRunning && (
                      <animate attributeName="r" values="2.4;3.2;2.4" dur="1s" repeatCount="indefinite" />
                    )}
                  </circle>
                  {isScanning && !step.stub && (
                    <circle cx={px + 11} cy={sy + SH / 2} r="2.4"
                      fill="none" stroke={color} strokeWidth="0.6" opacity="0.6">
                      <animate attributeName="r" values="2.4;5;2.4" dur="1.2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.6;0;0.6" dur="1.2s" repeatCount="indefinite" />
                    </circle>
                  )}
                </g>
              ) : (
                <g>
                  <text x={px + 11} y={sy + SH / 2 + 3.5} textAnchor="middle"
                    fontSize="7" fill={isDone ? C.emerald : stepColor}
                    opacity={step.stub ? 0.3 : isDone ? 0.9 : 0.7}>
                    {isDone ? "✓" : "▸"}
                  </text>
                  {isRunning && !step.stub && (
                    <circle cx={px + 11} cy={sy + SH / 2} r="0"
                      fill={color} opacity="0">
                      <animate attributeName="r" values="0;6;0" dur="1.4s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0;0.2;0" dur="1.4s" repeatCount="indefinite" />
                    </circle>
                  )}
                </g>
              )}

              {/* step label — brightens when active */}
              <text x={px + 21} y={sy + SH / 2 + 3.5}
                fontSize="8.5"
                fill={step.stub ? C.dimLt : isDone ? C.emerald : isRunning ? "#fff" : C.text}
                fontFamily="monospace"
                fontWeight={isRunning ? "bold" : "normal"}>
                {step.label}
              </text>

              {/* stub badge */}
              {step.stub && (
                <text x={px + pw - 6} y={sy + SH / 2 + 3.5}
                  textAnchor="end" fontSize="6.5" fill={C.dim}
                  fontFamily="monospace" fontStyle="italic">
                  stub
                </text>
              )}

              {/* status indicator (right side) */}
              {!step.stub && isPending && (
                <circle cx={px + pw - 9} cy={sy + SH / 2} r="1.8"
                  fill={color} opacity="0.25" />
              )}
              {!step.stub && isScanning && (
                <g>
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="2.2"
                    fill={color} opacity="0.5">
                    <animate attributeName="opacity" values="0.3;0.8;0.3" dur="0.6s" repeatCount="indefinite" />
                  </circle>
                  {/* scanning ring */}
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="2.2"
                    fill="none" stroke={color} strokeWidth="0.5" opacity="0.4">
                    <animate attributeName="r" values="2.2;5;2.2" dur="0.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.4;0;0.4" dur="0.8s" repeatCount="indefinite" />
                  </circle>
                </g>
              )}
              {!step.stub && isRunning && (
                <g>
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="2.8"
                    fill={color} opacity="0.9"
                    style={{ animation: "pulse 1s ease-in-out infinite" }} />
                  {/* spinning ring */}
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="5"
                    fill="none" stroke={color} strokeWidth="0.6"
                    strokeDasharray="3 5" opacity="0.5">
                    <animateTransform attributeName="transform" type="rotate"
                      from={`0 ${px + pw - 9} ${sy + SH / 2}`}
                      to={`360 ${px + pw - 9} ${sy + SH / 2}`}
                      dur="2s" repeatCount="indefinite" />
                  </circle>
                  {/* outer pulse */}
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="2.8"
                    fill="none" stroke={color} strokeWidth="0.4" opacity="0">
                    <animate attributeName="r" values="2.8;8;2.8" dur="1.6s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0;0.3;0" dur="1.6s" repeatCount="indefinite" />
                  </circle>
                </g>
              )}
              {!step.stub && isDone && (
                <g>
                  <text x={px + pw - 6} y={sy + SH / 2 + 3.5}
                    textAnchor="end" fontSize="7.5" fill={C.emerald}
                    opacity="0.9" fontWeight="bold">✓</text>
                  {/* subtle done glow */}
                  <circle cx={px + pw - 9} cy={sy + SH / 2} r="4"
                    fill={C.emerald} opacity="0.08" />
                </g>
              )}
            </g>

            {/* Particle burst on completion */}
            {hasBurst && !step.stub && (
              <ParticleBurst
                cx={px + pw - 9} cy={sy + SH / 2}
                color={C.emerald}
                id={`${layerId}-${step.id}`}
              />
            )}

            {/* completion flash across the card */}
            {hasBurst && !step.stub && (
              <rect x={px} y={sy} width="0" height={SH} rx="5"
                fill={C.emerald} opacity="0.2">
                <animate attributeName="width" from="0" to={String(pw)}
                  dur="0.4s" fill="freeze" />
                <animate attributeName="opacity" values="0.2;0.05"
                  dur="0.4s" fill="freeze" />
              </rect>
            )}

            {/* sequential: energy trail line from done step to next */}
            {isDone && !isParallelFlow && i < steps.length - 1 && !steps[i + 1].stub && (
              <line x1={cx} y1={sy + SH} x2={cx} y2={sy + SH + SGAP}
                stroke={C.emerald} strokeWidth="1" opacity="0.5">
                <animate attributeName="opacity" values="0.5;0.2;0.5" dur="2s" repeatCount="indefinite" />
              </line>
            )}
          </g>
        );
      })}

      {/* progress counter for sequential flows */}
      {!isParallelFlow && parentStatus === "running" && (
        <text
          x={px + pw - 2}
          y={py + ph + 10}
          textAnchor="end" fontSize="6" fill={color}
          fontFamily="monospace" opacity="0.6">
          {activeSteps.filter(s => stepStates[s.id] === "done").length}/{activeSteps.length}
        </text>
      )}
    </g>
  );
}

// ── Edge ──────────────────────────────────────────────────────────────────────
function Edge({
  from, to, animated, active,
}: { from: CNode; to: CNode; animated: boolean; active: boolean }) {
  const fx = from.x + from.w / 2, fy = from.y + from.h / 2;
  const tx = to.x   + to.w   / 2, ty = to.y   + to.h   / 2;
  const dx = tx - fx;
  const path = `M${fx},${fy} C${fx + dx * 0.5},${fy} ${tx - dx * 0.5},${ty} ${tx},${ty}`;
  const gid  = `eg-${from.id}`;

  return (
    <g>
      <defs>
        <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor={from.color} stopOpacity="0.9" />
          <stop offset="100%" stopColor={to.color}   stopOpacity="0.9" />
        </linearGradient>
      </defs>
      {/* glow halo */}
      <path d={path} fill="none" stroke={`url(#${gid})`}
        strokeWidth="12" opacity="0.06" strokeLinecap="round" />
      {/* soft glow */}
      <path d={path} fill="none" stroke={`url(#${gid})`}
        strokeWidth="4"  opacity="0.14" strokeLinecap="round" />
      {/* main line */}
      <path d={path} fill="none" stroke={`url(#${gid})`}
        strokeWidth={active ? 1.8 : 1}
        opacity={active ? 0.9 : 0.18}
        strokeLinecap="round"
        strokeDasharray={animated ? "7 5" : undefined}
        style={animated ? { animation: "flowdash 0.9s linear infinite" } : undefined}
      />
      {/* animated orb */}
      {animated && (
        <>
          <circle r="5" fill={from.color} opacity="0.12">
            <animateMotion dur="1.5s" repeatCount="indefinite" path={path} />
          </circle>
          <circle r="2.8" fill={from.color} opacity="1">
            <animateMotion dur="1.5s" repeatCount="indefinite" path={path} />
          </circle>
        </>
      )}
      {!animated && active && (
        <circle r="2" fill={to.color} opacity="0.5">
          <animateMotion dur="2.8s" repeatCount="indefinite" path={path} />
        </circle>
      )}
    </g>
  );
}

// ── Node card (SVG) ───────────────────────────────────────────────────────────
function Node({
  n, status, selected, onMouseDown, onClick,
}: {
  n: CNode; status: Status; selected: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
  onClick:     (e: React.MouseEvent) => void;
}) {
  const s    = ST[status];
  const isR  = status === "running";
  const isD  = status === "done";
  const { x, y, w, h, color, icon, label, sub, id } = n;
  const midY = h / 2;

  return (
    <g transform={`translate(${x},${y})`}
      onMouseDown={onMouseDown} onClick={onClick}
      style={{ cursor: "grab", userSelect: "none" }}>

      {/* selection / pulse ring */}
      {(selected || isR) && (
        <rect x="-7" y="-7" width={w + 14} height={h + 14} rx="19"
          fill="none" stroke={color} strokeWidth="1" opacity="0.25"
          style={isR ? { animation: "outerPulse 2s ease-in-out infinite" } : undefined} />
      )}
      {selected && (
        <rect x="-2" y="-2" width={w + 4} height={h + 4} rx="14"
          fill="none" stroke={color} strokeWidth="1.4" opacity="0.6" />
      )}

      <defs>
        <linearGradient id={`ng-${id}`} x1="0%" y1="0%" x2="120%" y2="120%">
          <stop offset="0%"   stopColor={selected ? `${color}28` : "#0e0b24"} />
          <stop offset="100%" stopColor={selected ? `${color}08` : "#060415"} />
        </linearGradient>
      </defs>

      {/* background */}
      <rect x="0" y="0" width={w} height={h} rx="12"
        fill={`url(#ng-${id})`}
        stroke={selected ? color : C.border}
        strokeWidth={selected ? 1.4 : 0.8} />

      {/* shimmer top */}
      <rect x="14" y="0" width={w - 28} height="1" rx="0.5"
        fill={color} opacity={selected ? 0.7 : 0.2} />

      {/* left accent */}
      <rect x="0" y="12" width="2.5" height={h - 24} rx="1.5"
        fill={color} opacity="0.95" />

      {/* icon ring */}
      <circle cx="30" cy={midY} r="16"
        fill={`${color}18`} stroke={`${color}40`} strokeWidth="0.8" />
      {isD && (
        <circle cx="30" cy={midY} r="16" fill="none"
          stroke={color} strokeWidth="0.8" opacity="0.4" strokeDasharray="3 4">
          <animateTransform attributeName="transform" type="rotate"
            from={`0 30 ${midY}`} to={`360 30 ${midY}`}
            dur="14s" repeatCount="indefinite" />
        </circle>
      )}
      <text x="30" y={midY + 5} textAnchor="middle" fontSize="13" fill={color}>{icon}</text>

      {/* label */}
      <text x="52" y={midY - 5} fontSize="11" fontWeight="700"
        fill={C.text} fontFamily="'DM Sans',sans-serif">{label}</text>

      {/* sub */}
      <text x="52" y={midY + 11} fontSize="8.5"
        fill={C.dimLt} fontFamily="monospace">{sub}</text>

      {/* status dot top-right */}
      <circle cx={w - 10} cy="10" r="4.5" fill={s.color} opacity={isR ? 1 : 0.65}
        style={isR ? { animation: "pulse 1.1s ease-in-out infinite" } : undefined} />
      {isR && (
        <circle cx={w - 10} cy="10" r="8" fill={s.color} opacity="0.15"
          style={{ animation: "outerPulse 1.1s ease-in-out infinite" }} />
      )}

      {/* status label bottom */}
      <text x={w / 2} y={h - 6} textAnchor="middle"
        fontSize="7.5" fill={s.color} fontFamily="monospace"
        letterSpacing="0.12em" opacity="0.85">
        {s.icon} {s.label.toUpperCase()}
      </text>
    </g>
  );
}

// ── Side panel ────────────────────────────────────────────────────────────────
function SidePanel({
  node, layers, nodeMap,
}: { node: CNode; layers?: Record<string, LayerStatus>; nodeMap: Record<string, CNode> }) {
  const status  = getStatus(node.id, layers);
  const s       = ST[status];
  const isR     = status === "running";
  const def     = node.pipelineIdx >= 0 ? PIPELINE[node.pipelineIdx] : null;
  const ls      = layers?.[node.id];
  const steps   = ls?.steps ?? {};
  const conns   = EDGES_DEF.filter(e => e.from === node.id || e.to === node.id);

  return (
    <div style={{ padding: "20px 18px", width: 248, overflowY: "auto", height: "100%" }}>
      {/* Header */}
      <div style={{ marginBottom: 18 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12,
          background: `${node.color}1e`, border: `1px solid ${node.color}50`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20, marginBottom: 12,
          boxShadow: `0 0 22px ${node.color}30`,
        }}>{node.icon}</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{node.label}</div>
        {def && (
          <div style={{ fontSize: 9, color: node.color, fontFamily: "monospace",
            marginTop: 2, letterSpacing: "0.12em" }}>{node.id}</div>
        )}
        <div style={{ fontSize: 10, color: C.dim, marginTop: 3, fontFamily: "monospace" }}>
          {node.sub}
        </div>
      </div>

      {/* Status */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "7px 12px", borderRadius: 9, marginBottom: 18,
        background: `${s.color}15`, border: `1px solid ${s.color}30`,
      }}>
        <div style={{
          width: 7, height: 7, borderRadius: "50%",
          background: s.color, boxShadow: `0 0 8px ${s.color}`,
          animation: isR ? "pulse 1.1s infinite" : "none", flexShrink: 0,
        }} />
        <span style={{ fontSize: 11, color: s.color, fontWeight: 700,
          fontFamily: "monospace", letterSpacing: "0.1em" }}>
          {s.icon} {s.label.toUpperCase()}
        </span>
        {ls?.detail && (
          <span style={{ fontSize: 9, color: C.dimLt, marginLeft: "auto" }}>{ls.detail}</span>
        )}
      </div>

      {/* Steps */}
      {def && (
        <>
          <div style={{ fontSize: 8, color: C.dim, letterSpacing: "0.18em",
            fontFamily: "monospace", marginBottom: 8 }}>
            WORKERS · {def.flow.toUpperCase()}
          </div>
          <div style={{ marginBottom: 16 }}>
            {def.steps.map(step => {
              const raw = steps[step.id];
              let eff: Status = "idle";
              if (!step.stub) {
                if (raw?.status)               eff = raw.status as Status;
                else if (status === "done")    eff = "done";
                else if (status === "running") eff = "running";
              }
              const sc = ST[eff];
              return (
                <div key={step.id} style={{
                  display: "flex", alignItems: "center", gap: 7,
                  padding: "6px 0", borderBottom: `1px solid ${C.border}`,
                  opacity: step.stub ? 0.35 : 1,
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: "50%", flexShrink: 0,
                    background: step.stub ? C.dim : sc.color,
                    animation: eff === "running" ? "pulse 1.2s infinite" : "none",
                    boxShadow: eff === "running" ? `0 0 6px ${sc.color}` : "none",
                  }} />
                  <div style={{ flex: 1, fontSize: 11, color: C.text }}>{step.label}</div>
                  {step.stub
                    ? <span style={{ fontSize: 8, color: C.dim, fontStyle: "italic" }}>stub</span>
                    : <span style={{ fontSize: 8.5, color: sc.color, fontFamily: "monospace" }}>
                        {sc.label}
                      </span>
                  }
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Output */}
      {def && (
        <>
          <div style={{ fontSize: 8, color: C.dim, letterSpacing: "0.18em",
            fontFamily: "monospace", marginBottom: 7 }}>OUTPUT</div>
          <div style={{
            padding: "7px 11px", borderRadius: 7, marginBottom: 16,
            border: `1px dashed ${node.color}38`, background: `${node.color}06`,
          }}>
            <span style={{ fontSize: 10, color: node.color, fontFamily: "monospace" }}>
              {def.output}
            </span>
          </div>
        </>
      )}

      {/* Connections */}
      {conns.length > 0 && (
        <>
          <div style={{ fontSize: 8, color: C.dim, letterSpacing: "0.18em",
            fontFamily: "monospace", marginBottom: 8 }}>CONNECTIONS</div>
          {conns.map(e => {
            const isIn  = e.to === node.id;
            const other = nodeMap[isIn ? e.from : e.to];
            if (!other) return null;
            return (
              <div key={e.id} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "6px 0", borderBottom: `1px solid ${C.border}`,
              }}>
                <span style={{ fontSize: 8, fontFamily: "monospace", fontWeight: 700,
                  color: isIn ? C.lav : C.blue, width: 24, letterSpacing: "0.1em" }}>
                  {isIn ? "IN" : "OUT"}
                </span>
                <span style={{ flex: 1, fontSize: 11, color: C.text }}>{other.label}</span>
                <div style={{ width: 7, height: 7, borderRadius: "50%",
                  background: other.color, boxShadow: `0 0 6px ${other.color}` }} />
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}

// ── Log entry type ───────────────────────────────────────────────────────────
interface LogEntry {
  id: number;
  time: string;
  layer: string;
  icon: string;
  color: string;
  message: string;
  type: "info" | "success" | "error" | "start" | "progress";
}

const LAYER_META: Record<string, { icon: string; color: string; label: string }> = {
  L1: { icon: "⬡", color: C.cobalt, label: "Monitoring" },
  L2: { icon: "⇌", color: C.indigo, label: "Broker" },
  L3: { icon: "✦", color: C.violet, label: "Curator" },
  L4: { icon: "◈", color: C.pink,   label: "Generation" },
  L5: { icon: "✧", color: C.peri,   label: "Post-Prod" },
};

const LAYER_START_MSGS: Record<string, string> = {
  L1: "Iniciando fetch paralelo de trends — 6 agents ativos",
  L2: "Ingestao de eventos na fila de deduplicacao",
  L3: "Gemini Analyzer selecionando melhores temas",
  L4: "Gerando frases, resolvendo backgrounds e compondo memes",
  L5: "Enriquecimento: caption, hashtags e quality score",
};

const LAYER_DONE_MSGS: Record<string, string> = {
  L1: "Coleta de trends concluida",
  L2: "Ranking e deduplicacao finalizados",
  L3: "WorkOrders criadas com sucesso",
  L4: "Frases e imagens geradas",
  L5: "Pacotes finais prontos para publicacao",
};

const LAYER_DETAIL_MSGS: Record<string, string[]> = {
  L1: [
    "Google Trends BR — buscando topicos em alta",
    "Reddit RSS — verificando 8 subreddits brasileiros",
    "RSS Feeds — Sensacionalista + portais",
    "YouTube RSS — canais BR verificados",
    "Gemini Web Trends — grounding com Google Search",
    "Brasil Viral RSS — HUEstation, Metropoles, Omelete",
  ],
  L2: [
    "Ingerindo eventos na asyncio.Queue",
    "Filtrando duplicatas por similaridade",
    "Ranking por score multi-fonte",
  ],
  L3: [
    "Gemini analisando relevancia e potencial viral",
    "Mapeando keywords para situacoes visuais",
    "Emitindo WorkOrders com situacao_key",
  ],
  L4: [
    "PhraseWorker — gerando frases via Gemini API",
    "BackgroundResolver — Gemini Image ou pool estatico por tema",
    "ImageComposer — Pillow overlay (frase + watermark)",
  ],
  L5: [
    "CaptionWorker — legendas Instagram com CTA",
    "HashtagWorker — hashtags trending + branded",
    "QualityWorker — scoring de qualidade final",
  ],
};

function nowTimestamp(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
}

// ── Progress bar component ───────────────────────────────────────────────────
function PipelineProgressBar({
  progress, isRunning, isDone, isError,
}: {
  progress: number; isRunning: boolean; isDone: boolean; isError: boolean;
}) {
  const barColor = isError ? C.err : isDone ? C.emerald : C.violet;
  const glowColor = isError ? C.err : isDone ? C.emerald : C.pink;

  return (
    <div style={{
      padding: "12px 20px 8px",
      background: C.panel,
      borderTop: `1px solid ${C.border}`,
    }}>
      {/* header row */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 8,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            fontSize: 8, color: C.dim, fontFamily: "monospace",
            letterSpacing: "0.18em",
          }}>
            PIPELINE PROGRESS
          </span>
          {isRunning && (
            <div style={{
              width: 5, height: 5, borderRadius: "50%",
              background: C.pink, boxShadow: `0 0 6px ${C.pink}`,
              animation: "pulse 1.2s ease-in-out infinite",
            }} />
          )}
        </div>
        <span style={{
          fontSize: 12, fontWeight: 700, color: barColor,
          fontFamily: "monospace", letterSpacing: "0.05em",
        }}>
          {Math.round(progress)}%
        </span>
      </div>

      {/* bar track */}
      <div style={{
        position: "relative", height: 6, borderRadius: 3,
        background: `${C.border}80`, overflow: "hidden",
      }}>
        {/* fill */}
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${Math.min(progress, 100)}%`,
          borderRadius: 3,
          background: `linear-gradient(90deg, ${barColor}cc, ${barColor})`,
          transition: "width 0.8s cubic-bezier(.4,0,.2,1)",
          boxShadow: `0 0 12px ${glowColor}60`,
        }} />

        {/* shimmer on running */}
        {isRunning && progress < 100 && (
          <div style={{
            position: "absolute", left: 0, top: 0, bottom: 0,
            width: `${Math.min(progress, 100)}%`,
            borderRadius: 3,
            overflow: "hidden",
          }}>
            <div style={{
              position: "absolute", top: 0, bottom: 0, width: 40,
              background: `linear-gradient(90deg, transparent, ${barColor}40, transparent)`,
              animation: "shimmerSlide 1.5s ease-in-out infinite",
            }} />
          </div>
        )}

        {/* glow dot at edge */}
        {isRunning && progress > 0 && progress < 100 && (
          <div style={{
            position: "absolute",
            left: `calc(${Math.min(progress, 100)}% - 3px)`,
            top: -1, width: 8, height: 8, borderRadius: "50%",
            background: glowColor,
            boxShadow: `0 0 10px ${glowColor}, 0 0 20px ${glowColor}60`,
            animation: "pulse 1s ease-in-out infinite",
            transition: "left 0.8s cubic-bezier(.4,0,.2,1)",
          }} />
        )}
      </div>

      {/* layer indicators */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        marginTop: 6, padding: "0 2px",
      }}>
        {PIPELINE.map(l => {
          const meta = LAYER_META[l.id];
          return (
            <span key={l.id} style={{
              fontSize: 7, fontFamily: "monospace", color: meta.color,
              opacity: 0.5, letterSpacing: "0.06em",
            }}>
              {meta.icon} {l.id}
            </span>
          );
        })}
      </div>
    </div>
  );
}

// ── Log panel component ──────────────────────────────────────────────────────
function PipelineLogPanel({ logs, isRunning }: { logs: LogEntry[]; isRunning: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length]);

  const typeStyles: Record<LogEntry["type"], { prefix: string; prefixColor: string }> = {
    start:    { prefix: "START",   prefixColor: C.blue },
    info:     { prefix: "INFO",    prefixColor: C.dimLt },
    progress: { prefix: "PROC",    prefixColor: C.gold },
    success:  { prefix: "DONE",    prefixColor: C.emerald },
    error:    { prefix: "ERROR",   prefixColor: C.err },
  };

  return (
    <div style={{
      background: "#04020c",
      borderTop: `1px solid ${C.border}`,
      flexShrink: 0,
    }}>
      {/* log header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 20px 6px",
        borderBottom: `1px solid ${C.border}50`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            fontSize: 8, color: C.dim, fontFamily: "monospace",
            letterSpacing: "0.18em",
          }}>
            EXECUTION LOG
          </span>
          {isRunning && (
            <span style={{
              fontSize: 7, color: C.pink, fontFamily: "monospace",
              letterSpacing: "0.1em",
              animation: "pulse 1.4s ease-in-out infinite",
            }}>
              STREAMING
            </span>
          )}
        </div>
        <span style={{
          fontSize: 8, color: C.dim, fontFamily: "monospace",
        }}>
          {logs.length} {logs.length === 1 ? "entrada" : "entradas"}
        </span>
      </div>

      {/* log entries */}
      <div
        ref={scrollRef}
        style={{
          maxHeight: 180, overflowY: "auto", padding: "6px 0",
          scrollBehavior: "smooth",
        }}
      >
        {logs.length === 0 ? (
          <div style={{
            padding: "16px 20px", textAlign: "center",
            fontSize: 10, color: C.dim, fontFamily: "monospace",
          }}>
            Aguardando execucao do pipeline...
          </div>
        ) : (
          logs.map((log, i) => {
            const ts = typeStyles[log.type];
            const isLast = i === logs.length - 1;
            return (
              <div
                key={log.id}
                style={{
                  display: "flex", alignItems: "flex-start", gap: 0,
                  padding: "3px 20px",
                  background: isLast && isRunning ? `${log.color}08` : "transparent",
                  borderLeft: isLast && isRunning ? `2px solid ${log.color}60` : "2px solid transparent",
                  animation: isLast ? "logFadeIn 0.3s ease-out" : undefined,
                }}
              >
                {/* timestamp */}
                <span style={{
                  fontSize: 9, color: C.dim, fontFamily: "monospace",
                  width: 58, flexShrink: 0, opacity: 0.6,
                }}>
                  {log.time}
                </span>

                {/* type badge */}
                <span style={{
                  fontSize: 7, fontFamily: "monospace", fontWeight: 700,
                  color: ts.prefixColor, width: 38, flexShrink: 0,
                  letterSpacing: "0.08em", paddingTop: 1,
                }}>
                  {ts.prefix}
                </span>

                {/* layer icon */}
                <span style={{
                  fontSize: 9, color: log.color, width: 16,
                  flexShrink: 0, textAlign: "center",
                }}>
                  {log.icon}
                </span>

                {/* message */}
                <span style={{
                  fontSize: 10, color: log.type === "success" ? C.emerald
                    : log.type === "error" ? C.err
                    : C.text,
                  fontFamily: "monospace",
                  opacity: log.type === "info" ? 0.7 : 0.9,
                }}>
                  {log.message}
                </span>

                {/* running indicator on last entry */}
                {isLast && isRunning && log.type !== "success" && log.type !== "error" && (
                  <span style={{
                    marginLeft: 6, fontSize: 8,
                    animation: "pulse 1s ease-in-out infinite",
                  }}>
                    <span style={{
                      display: "inline-block", width: 4, height: 4,
                      borderRadius: "50%", background: log.color,
                      boxShadow: `0 0 4px ${log.color}`,
                    }} />
                  </span>
                )}
              </div>
            );
          })
        )}

        {/* cursor blink at bottom */}
        {isRunning && logs.length > 0 && (
          <div style={{
            padding: "2px 20px 4px",
            display: "flex", alignItems: "center", gap: 4,
          }}>
            <span style={{
              fontSize: 9, color: C.dim, fontFamily: "monospace",
              width: 58, opacity: 0.6,
            }}>
              {nowTimestamp()}
            </span>
            <span style={{
              display: "inline-block", width: 6, height: 12,
              background: C.violet, opacity: 0.7,
              animation: "cursorBlink 1s step-end infinite",
            }} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Hook: generate logs from layer transitions ──────────────────────────────
function useLayerLogs(
  layers?: Record<string, LayerStatus>,
  pipelineStatus?: string,
  errors?: string[],
  stats?: { trends: number; orders: number; images: number; packages: number },
): LogEntry[] {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const prevLayers = useRef<Record<string, string>>({});
  const nextId = useRef(0);
  const detailIdx = useRef<Record<string, number>>({});
  const detailTimers = useRef<ReturnType<typeof setInterval>[]>([]);

  const addLog = useCallback((
    layer: string, message: string, type: LogEntry["type"],
  ) => {
    const meta = LAYER_META[layer] ?? { icon: "◇", color: C.lav, label: "System" };
    setLogs(prev => [...prev, {
      id: nextId.current++,
      time: nowTimestamp(),
      layer,
      icon: meta.icon,
      color: meta.color,
      message,
      type,
    }]);
  }, []);

  // Watch layer transitions
  useEffect(() => {
    if (!layers) return;

    for (const [id, ls] of Object.entries(layers)) {
      const prevStatus = prevLayers.current[id] ?? "idle";
      const newStatus = ls.status;

      if (prevStatus === newStatus) continue;
      prevLayers.current[id] = newStatus;

      const meta = LAYER_META[id];
      if (!meta) continue;

      if (newStatus === "running" && prevStatus !== "running") {
        addLog(id, LAYER_START_MSGS[id] ?? `${meta.label} iniciando...`, "start");

        // Drip-feed detail messages for this layer
        const details = LAYER_DETAIL_MSGS[id];
        if (details) {
          detailIdx.current[id] = 0;
          const interval = setInterval(() => {
            const idx = detailIdx.current[id] ?? 0;
            if (idx < details.length) {
              addLog(id, details[idx], "progress");
              detailIdx.current[id] = idx + 1;
            } else {
              clearInterval(interval);
            }
          }, 800);
          detailTimers.current.push(interval);
        }
      }

      if (newStatus === "done" && prevStatus !== "done") {
        // Add stats if available
        let extra = "";
        if (id === "L1" && stats?.trends) extra = ` — ${stats.trends} eventos coletados`;
        if (id === "L3" && stats?.orders) extra = ` — ${stats.orders} work orders`;
        if (id === "L4" && stats?.images) extra = ` — ${stats.images} imagens geradas`;
        if (id === "L5" && stats?.packages) extra = ` — ${stats.packages} pacotes finais`;
        addLog(id, (LAYER_DONE_MSGS[id] ?? `${meta.label} concluido`) + extra, "success");
      }

      if (newStatus === "error") {
        addLog(id, `Erro em ${meta.label}`, "error");
      }
    }
  }, [layers, addLog, stats]);

  // Pipeline-level events
  useEffect(() => {
    if (pipelineStatus === "completed") {
      addLog("L5", "Pipeline concluido com sucesso!", "success");
    }
    if (pipelineStatus === "error" || pipelineStatus === "failed") {
      const msg = errors?.[0] ?? "Pipeline falhou";
      addLog("L1", msg, "error");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineStatus]);

  // Reset on new run
  useEffect(() => {
    if (!layers || Object.keys(layers).length === 0) {
      prevLayers.current = {};
      detailIdx.current = {};
      detailTimers.current.forEach(t => clearInterval(t));
      detailTimers.current = [];
    }
  }, [layers]);

  return logs;
}

// ── Main ──────────────────────────────────────────────────────────────────────
export interface PipelineDiagramProps {
  layers?: Record<string, LayerStatus>;
  currentLayer?: string | null;
  pipelineStatus?: PipelineRunResult | null;
  isRunning?: boolean;
}

const WORLD_W  = 20 + 6 * (NW + GAP) + 40;
const INITIAL_ZOOM = 0.92;
const INITIAL_PAN  = { x: 16, y: 38 };

export function PipelineDiagram({ layers, pipelineStatus, isRunning: isRunningProp }: PipelineDiagramProps) {
  const [nodes, setNodes]       = useState<CNode[]>(makeNodes);
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom]         = useState(INITIAL_ZOOM);
  const [pan]                   = useState(INITIAL_PAN);
  const dragging                = useRef<{ id: string; ox: number; oy: number } | null>(null);
  const svgRef                  = useRef<SVGSVGElement>(null);

  // Derive pipeline state
  const ps = pipelineStatus;
  const isRunning = isRunningProp ?? false;
  const isDone = ps?.status === "completed";
  const isError = ps?.status === "error" || ps?.status === "failed";

  // Progress: based on layer completion (5 layers = 20% each) + partial from stats
  const progress = useMemo(() => {
    if (!layers) return 0;
    if (isDone) return 100;
    let p = 0;
    const layerWeight = 20;
    for (const l of PIPELINE) {
      const st = layers[l.id]?.status;
      if (st === "done") p += layerWeight;
      else if (st === "running") p += layerWeight * 0.4;
    }
    return Math.min(Math.round(p), isRunning ? 95 : 100);
  }, [layers, isDone, isRunning]);

  // Logs from layer transitions
  const logs = useLayerLogs(
    layers,
    ps?.status,
    ps?.errors,
    ps ? {
      trends: ps.trends_fetched,
      orders: ps.work_orders,
      images: ps.images_generated,
      packages: ps.packages_produced,
    } : undefined,
  );

  // non-passive wheel for zoom
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const fn = (e: WheelEvent) => {
      e.preventDefault();
      setZoom(z => Math.max(0.28, Math.min(3.0, z - e.deltaY * 0.0008)));
    };
    el.addEventListener("wheel", fn, { passive: false });
    return () => el.removeEventListener("wheel", fn);
  }, []);

  const onNodeDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const svg = svgRef.current!;
    const pt  = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const sp = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const n  = nodes.find(n => n.id === id)!;
    dragging.current = {
      id,
      ox: (sp.x - pan.x) / zoom - n.x,
      oy: (sp.y - pan.y) / zoom - n.y,
    };
  }, [nodes, zoom, pan]);

  const onMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const d = dragging.current;
    if (!d) return;
    const svg = svgRef.current!;
    const pt  = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const sp = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const nx = (sp.x - pan.x) / zoom - d.ox;
    const ny = (sp.y - pan.y) / zoom - d.oy;
    setNodes(prev => prev.map(n => n.id === d.id ? { ...n, x: nx, y: ny } : n));
  }, [zoom, pan]);

  const stopDrag = useCallback(() => { dragging.current = null; }, []);

  const nodeMap = useMemo(() => Object.fromEntries(nodes.map(n => [n.id, n])), [nodes]);
  const sel     = nodes.find(n => n.id === selected) ?? null;

  const running = PIPELINE.filter(l => layers?.[l.id]?.status === "running").length;

  return (
    <div style={{
      width: "100%", background: C.bg, borderRadius: 14, overflow: "hidden",
      display: "flex", flexDirection: "column", fontFamily: "'DM Sans',sans-serif",
    }}>
      <style>{`
        @keyframes flowdash    { to { stroke-dashoffset: -24; } }
        @keyframes pulse       { 0%,100%{opacity:1} 50%{opacity:0.22} }
        @keyframes outerPulse  { 0%,100%{opacity:0.18} 50%{opacity:0.52} }
        @keyframes subNodeGlow { 0%,100%{opacity:0.2;stroke-width:0.6} 50%{opacity:0.5;stroke-width:1.2} }
        @keyframes shimmerSlide { 0%{transform:translateX(-40px)} 100%{transform:translateX(calc(100vw))} }
        @keyframes logFadeIn   { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes cursorBlink { 0%,100%{opacity:0.7} 50%{opacity:0} }
      `}</style>

      {/* ── Top bar ──────────────────────────────────────────────────────────── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "9px 20px", borderBottom: `1px solid ${C.border}`,
        background: C.panel, flexShrink: 0,
      }}>
        <div />

        {running > 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6, padding: "4px 12px",
            background: "#1a0d2e", border: `1px solid ${C.pink}44`, borderRadius: 20,
            color: C.pink, fontSize: 10, fontWeight: 700,
            fontFamily: "monospace", letterSpacing: "0.1em",
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: "50%",
              background: C.pink, boxShadow: `0 0 8px ${C.pink}`,
              animation: "pulse 1.4s ease-in-out infinite",
            }} />
            LIVE
          </div>
        )}
      </div>

      {/* ── Canvas + side panel ──────────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <svg
          ref={svgRef}
          style={{ flex: 1, display: "block", minHeight: 500 }}
          onMouseMove={onMouseMove}
          onMouseUp={stopDrag}
          onMouseLeave={stopDrag}
          onClick={() => setSelected(null)}
        >
          <defs>
            <pattern id="gsm" width="28" height="28" patternUnits="userSpaceOnUse">
              <path d="M28 0L0 0 0 28" fill="none" stroke={C.gridSm} strokeWidth="0.6" />
            </pattern>
            <pattern id="glg" width="140" height="140" patternUnits="userSpaceOnUse">
              <rect width="140" height="140" fill="url(#gsm)" />
              <path d="M140 0L0 0 0 140" fill="none" stroke={C.gridLg} strokeWidth="1.2" />
            </pattern>
            <radialGradient id="rbg1" cx="40%" cy="60%" r="65%">
              <stop offset="0%"   stopColor="#2e1065" stopOpacity="0.45" />
              <stop offset="100%" stopColor={C.bg}    stopOpacity="0"    />
            </radialGradient>
            <radialGradient id="rbg2" cx="85%" cy="15%" r="50%">
              <stop offset="0%"   stopColor="#1e3a8a" stopOpacity="0.2" />
              <stop offset="100%" stopColor={C.bg}    stopOpacity="0"   />
            </radialGradient>
          </defs>

          <rect width="100%" height="100%" fill="url(#glg)" />
          <rect width="100%" height="100%" fill="url(#rbg1)" />
          <rect width="100%" height="100%" fill="url(#rbg2)" />

          <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
            {/* Edges */}
            {EDGES_DEF.map(e => {
              const fn = nodeMap[e.from], tn = nodeMap[e.to];
              if (!fn || !tn) return null;
              const fs = getStatus(e.from, layers);
              return (
                <Edge key={e.id} from={fn} to={tn}
                  animated={fs === "running"}
                  active={fs !== "idle"} />
              );
            })}

            {/* Sub-node groups (rendered before main nodes so main nodes appear on top) */}
            {nodes.map(n => {
              if (n.pipelineIdx < 0) return null;
              const def = PIPELINE[n.pipelineIdx];
              const st  = getStatus(n.id, layers);
              return (
                <SubNodeGroup
                  key={`subs-${n.id}`}
                  px={n.x} py={n.y} pw={n.w} ph={n.h}
                  color={n.color} flow={def.flow}
                  steps={def.steps} parentStatus={st}
                  layerId={n.id}
                />
              );
            })}

            {/* Main nodes */}
            {nodes.map(n => (
              <Node
                key={n.id} n={n}
                status={getStatus(n.id, layers)}
                selected={selected === n.id}
                onMouseDown={ev => onNodeDown(ev, n.id)}
                onClick={ev => { ev.stopPropagation(); setSelected(n.id); }}
              />
            ))}
          </g>

          {/* world width hint */}
          <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
            <rect x="0" y="0" width={WORLD_W} height="1" fill="none" />
          </g>
        </svg>

        {/* Side panel */}
        <div style={{
          width: sel ? 248 : 0, overflow: "hidden",
          transition: "width 0.3s cubic-bezier(.4,0,.2,1)",
          background: C.panel, borderLeft: `1px solid ${C.border}`, flexShrink: 0,
        }}>
          {sel && <SidePanel node={sel} layers={layers} nodeMap={nodeMap} />}
        </div>
      </div>

      {/* ── Progress bar + Log panel ─────────────────────────────────────────── */}
      {(isRunning || isDone || isError || logs.length > 0) && (
        <>
          <PipelineProgressBar
            progress={progress}
            isRunning={isRunning}
            isDone={isDone}
            isError={isError}
          />
          <PipelineLogPanel logs={logs} isRunning={isRunning} />
        </>
      )}

      {/* ── Bottom bar ───────────────────────────────────────────────────────── */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16, padding: "6px 20px",
        borderTop: `1px solid ${C.border}`, background: C.panel,
        fontSize: 9.5, color: C.dim, fontFamily: "monospace",
        letterSpacing: "0.06em", flexShrink: 0,
      }}>
        <span>SCROLL TO ZOOM · DRAG NODES · CLICK TO INSPECT</span>
        <span style={{ marginLeft: "auto", color: C.violet }}>
          ZOOM {Math.round(zoom * 100)}%
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          {([["−", -0.12], ["+", 0.12]] as [string, number][]).map(([btn, d]) => (
            <button key={btn}
              onClick={() => setZoom(z => Math.max(0.28, Math.min(3.0, z + d)))}
              style={{
                width: 24, height: 24, borderRadius: 6, cursor: "pointer",
                border: `1px solid ${C.border}`, background: "#0e0b24",
                color: C.lav, fontSize: 14,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>{btn}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
