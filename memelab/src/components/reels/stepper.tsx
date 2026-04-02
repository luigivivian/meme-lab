"use client";

import { Check, MessageSquare, Image, FileText, Mic, Captions, Clapperboard, Film } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useRef, type ReactNode } from "react";
import type { StepState } from "@/lib/api";

const STEPS = [
  { id: "prompt", label: "Prompt", icon: MessageSquare },
  { id: "script", label: "Roteiro", icon: FileText },
  { id: "tts", label: "Narracao", icon: Mic },
  { id: "srt", label: "Legendas", icon: Captions },
  { id: "images", label: "Imagens", icon: Image },
  { id: "clips", label: "Clips", icon: Clapperboard },
  { id: "video", label: "Video", icon: Film },
] as const;

function getStepStatus(index: number, currentStep: number, stepState: StepState) {
  const stepId = STEPS[index].id;
  const data = stepState[stepId as keyof StepState];
  if (data && typeof data === "object" && "approved" in data && data.approved) return "completed";
  if (index === currentStep) return "active";
  return "pending";
}

export function StepperHeader({
  currentStep,
  stepState,
  displayStep,
  onStepClick,
}: {
  currentStep: number;
  stepState: StepState;
  displayStep?: number;
  onStepClick?: (index: number) => void;
}) {
  const activeDisplay = displayStep ?? currentStep;

  return (
    <div className="flex items-center justify-center gap-1 sm:gap-2 py-4">
      {STEPS.map((step, i) => {
        const status = getStepStatus(i, currentStep, stepState);
        const isViewing = i === activeDisplay;
        const isClickable = status === "completed" && !isViewing;
        const Icon = step.icon;
        return (
          <div key={step.id} className="flex items-center">
            {i > 0 && (
              <div
                className={`h-0.5 w-4 sm:w-8 mx-1 transition-colors ${
                  status === "completed" || (i <= currentStep && getStepStatus(i - 1, currentStep, stepState) === "completed")
                    ? "bg-emerald-500"
                    : "bg-border"
                }`}
              />
            )}
            <button
              type="button"
              disabled={!isClickable}
              onClick={() => isClickable && onStepClick?.(i)}
              className={`flex flex-col items-center gap-1 group ${
                isClickable ? "cursor-pointer" : status === "pending" ? "cursor-not-allowed" : "cursor-default"
              }`}
            >
              <div
                className={`flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 transition-all ${
                  isViewing && status !== "active"
                    ? "border-purple-500 ring-2 ring-purple-500/30 bg-emerald-500/20 text-emerald-400"
                    : status === "completed"
                      ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                      : status === "active"
                        ? "border-purple-500 text-purple-400 bg-purple-500/10"
                        : "border-muted text-muted-foreground"
                } ${isClickable ? "group-hover:scale-110 group-hover:ring-2 group-hover:ring-emerald-500/30" : ""}`}
              >
                {status === "completed" ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </div>
              <span
                className={`text-[10px] sm:text-xs hidden sm:block transition-colors ${
                  isViewing
                    ? "text-purple-400 font-medium"
                    : status === "active"
                      ? "text-purple-400 font-medium"
                      : "text-muted-foreground"
                } ${isClickable ? "group-hover:text-emerald-400" : ""}`}
              >
                {step.label}
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}

const variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 200 : -200,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction < 0 ? 200 : -200,
    opacity: 0,
  }),
};

export function StepContent({ currentStep, displayStep, children }: { currentStep: number; displayStep?: number; children: ReactNode }) {
  const step = displayStep ?? currentStep;
  const prevStep = useRef(step);
  const direction = step >= prevStep.current ? 1 : -1;
  prevStep.current = step;

  return (
    <AnimatePresence mode="wait" custom={direction}>
      <motion.div
        key={step}
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
