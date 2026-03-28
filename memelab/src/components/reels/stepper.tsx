"use client";

import { Check, MessageSquare, Image, FileText, Mic, Captions, Film } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useRef, type ReactNode } from "react";
import type { StepState } from "@/lib/api";

const STEPS = [
  { id: "prompt", label: "Prompt", icon: MessageSquare },
  { id: "script", label: "Roteiro", icon: FileText },
  { id: "images", label: "Imagens", icon: Image },
  { id: "tts", label: "Narracao", icon: Mic },
  { id: "srt", label: "Legendas", icon: Captions },
  { id: "video", label: "Video", icon: Film },
] as const;

function getStepStatus(index: number, currentStep: number, stepState: StepState) {
  const stepId = STEPS[index].id;
  const data = stepState[stepId as keyof StepState];
  if (data && typeof data === "object" && "approved" in data && data.approved) return "completed";
  if (index === currentStep) return "active";
  return "pending";
}

export function StepperHeader({ currentStep, stepState }: { currentStep: number; stepState: StepState }) {
  return (
    <div className="flex items-center justify-center gap-1 sm:gap-2 py-4">
      {STEPS.map((step, i) => {
        const status = getStepStatus(i, currentStep, stepState);
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
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 transition-colors ${
                  status === "completed"
                    ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                    : status === "active"
                      ? "border-purple-500 text-purple-400 bg-purple-500/10"
                      : "border-muted text-muted-foreground"
                }`}
              >
                {status === "completed" ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </div>
              <span
                className={`text-[10px] sm:text-xs hidden sm:block ${
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

export function StepContent({ currentStep, children }: { currentStep: number; children: ReactNode }) {
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
