"use client";

import { Check, Search, Image, Wand2, Film, Type, Music, Layers, Download, Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useRef, type ReactNode } from "react";
import type { AdStepData } from "@/lib/api";

const STEPS = [
  { id: "analysis", label: "Analise", icon: Search },
  { id: "scene", label: "Cenario", icon: Image },
  { id: "prompt", label: "Prompt", icon: Wand2 },
  { id: "video", label: "Video", icon: Film },
  { id: "copy", label: "Copy", icon: Type },
  { id: "audio", label: "Audio", icon: Music },
  { id: "assembly", label: "Montagem", icon: Layers },
  { id: "export", label: "Export", icon: Download },
] as const;

export const ADS_STEP_ORDER: string[] = STEPS.map((s) => s.id);

export type StepStatus = "completed" | "active" | "generating" | "failed" | "pending";

export function getStepStatus(
  stepId: string,
  currentStepId: string,
  stepsMap: Record<string, AdStepData>
): StepStatus {
  const data = stepsMap[stepId];
  if (data?.status === "approved") return "completed";
  if (data?.status === "complete") return "completed";
  if (data?.status === "generating") return "generating";
  if (data?.status === "error") return "failed";
  if (stepId === currentStepId) return "active";
  return "pending";
}

/** Check if a step is navigable (completed or active or failed) */
export function isStepNavigable(
  stepId: string,
  currentStepId: string,
  stepsMap: Record<string, AdStepData>
): boolean {
  const status = getStepStatus(stepId, currentStepId, stepsMap);
  return status !== "pending";
}

export function AdStepper({
  currentStep,
  steps,
  viewingStep,
  onStepClick,
}: {
  currentStep: string;
  steps: AdStepData[];
  viewingStep?: string;
  onStepClick?: (stepId: string) => void;
}) {
  const stepsMap: Record<string, AdStepData> = {};
  for (const s of steps) stepsMap[s.step_name] = s;

  const completedCount = STEPS.filter(
    (s) => getStepStatus(s.id, currentStep, stepsMap) === "completed"
  ).length;
  const progressPct = (completedCount / STEPS.length) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {completedCount}/{STEPS.length}
        </span>
      </div>

      <div className="flex items-center justify-center gap-0.5 sm:gap-1 py-2 overflow-x-auto">
        {STEPS.map((step, i) => {
          const status = getStepStatus(step.id, currentStep, stepsMap);
          const Icon = step.icon;
          const navigable = isStepNavigable(step.id, currentStep, stepsMap);
          const isViewing = viewingStep === step.id;

          return (
            <div key={step.id} className="flex items-center shrink-0">
              {i > 0 && (
                <div
                  className={`h-0.5 w-3 sm:w-6 mx-0.5 transition-colors duration-500 ${
                    status === "completed" ? "bg-emerald-500" : "bg-border"
                  }`}
                />
              )}
              <button
                type="button"
                disabled={!navigable}
                onClick={() => navigable && onStepClick?.(step.id)}
                className="flex flex-col items-center gap-1 group"
              >
                <div
                  className={`flex items-center justify-center w-7 h-7 sm:w-9 sm:h-9 rounded-full border-2 transition-all duration-300 ${
                    isViewing
                      ? "border-purple-500 text-purple-400 bg-purple-500/10 ring-2 ring-purple-500/30"
                      : status === "completed"
                        ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                        : status === "active"
                          ? "border-purple-500 text-purple-400 bg-purple-500/10"
                          : status === "generating"
                            ? "border-amber-500 text-amber-400 bg-amber-500/10"
                            : status === "failed"
                              ? "border-red-500 text-red-400 bg-red-500/10"
                              : "border-muted text-muted-foreground"
                  } ${navigable ? "cursor-pointer hover:scale-110" : "cursor-default opacity-50"}`}
                >
                  {status === "completed" ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : status === "generating" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                </div>
                <span
                  className={`text-[9px] sm:text-xs hidden sm:block transition-colors ${
                    isViewing
                      ? "text-purple-400 font-bold"
                      : status === "active" || status === "generating"
                        ? "text-purple-400 font-medium"
                        : status === "completed"
                          ? "text-emerald-400"
                          : "text-muted-foreground"
                  }`}
                >
                  {step.label}
                </span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const variants = {
  enter: (direction: number) => ({ x: direction > 0 ? 200 : -200, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({ x: direction < 0 ? 200 : -200, opacity: 0 }),
};

export function AdStepContent({ currentStep, children }: { currentStep: number; children: ReactNode }) {
  const prevStep = useRef(currentStep);
  const direction = currentStep >= prevStep.current ? 1 : -1;
  prevStep.current = currentStep;

  return (
    <AnimatePresence mode="wait" custom={direction}>
      <motion.div
        key={currentStep}
        custom={direction}
        variants={variants}
        initial="enter"
        animate="center"
        exit="exit"
        transition={{ duration: 0.2, ease: "easeInOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
