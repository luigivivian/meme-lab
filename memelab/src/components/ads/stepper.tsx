"use client";

import { Check, Search, Image, Wand2, Film, Type, Music, Layers, Download } from "lucide-react";
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

function getStepStatus(
  stepId: string,
  currentStepId: string,
  stepsMap: Record<string, AdStepData>
): "completed" | "active" | "generating" | "failed" | "pending" {
  const data = stepsMap[stepId];
  if (data?.status === "approved") return "completed";
  if (data?.status === "completed") return "completed";
  if (data?.status === "generating") return "generating";
  if (data?.status === "failed") return "failed";
  if (stepId === currentStepId) return "active";
  return "pending";
}

export function AdStepper({
  currentStep,
  steps,
}: {
  currentStep: string;
  steps: AdStepData[];
}) {
  const stepsMap: Record<string, AdStepData> = {};
  for (const s of steps) stepsMap[s.step_name] = s;

  return (
    <div className="flex items-center justify-center gap-0.5 sm:gap-1 py-4 overflow-x-auto">
      {STEPS.map((step, i) => {
        const status = getStepStatus(step.id, currentStep, stepsMap);
        const Icon = step.icon;
        return (
          <div key={step.id} className="flex items-center flex-shrink-0">
            {i > 0 && (
              <div
                className={`h-0.5 w-3 sm:w-6 mx-0.5 transition-colors ${
                  status === "completed" ? "bg-emerald-500" : "bg-border"
                }`}
              />
            )}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex items-center justify-center w-7 h-7 sm:w-9 sm:h-9 rounded-full border-2 transition-colors ${
                  status === "completed"
                    ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                    : status === "active"
                      ? "border-purple-500 text-purple-400 bg-purple-500/10"
                      : status === "generating"
                        ? "border-amber-500 text-amber-400 bg-amber-500/10 animate-pulse"
                        : status === "failed"
                          ? "border-red-500 text-red-400 bg-red-500/10"
                          : "border-muted text-muted-foreground"
                }`}
              >
                {status === "completed" ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <Icon className="h-3.5 w-3.5" />
                )}
              </div>
              <span
                className={`text-[9px] sm:text-xs hidden sm:block ${
                  status === "active" ? "text-purple-400 font-medium" : "text-muted-foreground"
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
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
        transition={{ duration: 0.25, ease: "easeInOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
