"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useStepState } from "@/hooks/use-reels";
import { approveStep, regenerateStep } from "@/lib/api";
import { StepperHeader, StepContent } from "@/components/reels/stepper";
import { StepPrompt } from "@/components/reels/step-prompt";
import { StepScript } from "@/components/reels/step-script";
import { StepNarration } from "@/components/reels/step-narration";
import { StepSubtitles } from "@/components/reels/step-subtitles";
import { StepImages } from "@/components/reels/step-images";
import { StepClips } from "@/components/reels/step-clips";
import { StepVideo } from "@/components/reels/step-video";

export default function ReelJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { data: stepState, error, isLoading, mutate } = useStepState(jobId);
  const [viewStep, setViewStep] = useState<number | null>(null);
  const prevCurrentStep = useRef<number>(0);

  // All hooks must be above early returns (Rules of Hooks)
  const currentStep = stepState?.current_step ?? 0;

  // When backend's currentStep changes (approve/regenerate from any step component),
  // auto-reset viewStep so the user follows the new active step
  useEffect(() => {
    if (currentStep !== prevCurrentStep.current) {
      prevCurrentStep.current = currentStep;
      setViewStep(null);
    }
  }, [currentStep]);

  if (isLoading || !stepState) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
        <p className="text-sm text-muted-foreground">Carregando reel...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/reels" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center">
          <p className="text-red-400">Reel nao encontrado ou erro ao carregar.</p>
        </div>
      </div>
    );
  }

  const state = stepState!;

  // When viewing a past step, approve should return to the current step (no-op on backend)
  // When viewing the current step, approve advances normally
  async function handleApprove(step: string) {
    await approveStep(jobId, step);
    // If we were viewing a past step, return to the backend's current step
    if (viewStep !== null) {
      setViewStep(null);
    }
    mutate();
  }

  async function handleRegenerate(step: string) {
    await regenerateStep(jobId, step);
    // Regenerate clears downstream and resets current_step — follow it
    setViewStep(null);
    mutate();
  }

  const displayStep = viewStep ?? currentStep;
  // Whether we're viewing a past completed step (read-only navigation)
  const isViewingPast = viewStep !== null && viewStep < currentStep;

  function renderStepContent() {
    // When viewing a past step, show a "back to current" bar
    const viewingPastBar = isViewingPast ? (
      <div className="flex items-center justify-between rounded-lg border border-purple-500/30 bg-purple-500/5 p-3 mb-3">
        <p className="text-sm text-purple-300">Visualizando passo anterior. Pode regenerar ou voltar ao passo atual.</p>
        <button
          type="button"
          onClick={() => setViewStep(null)}
          className="text-sm text-purple-400 hover:text-purple-300 font-medium"
        >
          Voltar ao passo atual →
        </button>
      </div>
    ) : null;

    let content;
    switch (displayStep) {
      case 0:
        content = <StepPrompt jobId={jobId} stepState={state} onApprove={handleApprove} mutate={() => mutate()} />;
        break;
      case 1:
        content = <StepScript jobId={jobId} stepState={state} onApprove={handleApprove} mutate={() => mutate()} />;
        break;
      case 2:
        content = (
          <StepNarration
            jobId={jobId}
            stepData={state.tts}
            onApprove={handleApprove}
            onRegenerate={handleRegenerate}
            mutate={() => mutate()}
          />
        );
        break;
      case 3:
        content = (
          <StepSubtitles
            jobId={jobId}
            stepData={state.srt}
            onApprove={handleApprove}
            onRegenerate={handleRegenerate}
            mutate={() => mutate()}
          />
        );
        break;
      case 4:
        content = <StepImages jobId={jobId} stepState={state} mutate={() => mutate()} onApprove={handleApprove} />;
        break;
      case 5:
        content = (
          <StepClips
            jobId={jobId}
            stepData={state.clips}
            stepState={state}
            mutate={() => mutate()}
          />
        );
        break;
      case 6:
        content = (
          <StepVideo
            jobId={jobId}
            stepData={state.video}
            stepState={state}
            mutate={() => mutate()}
          />
        );
        break;
      default:
        content = (
          <div className="rounded-lg border p-8 text-center">
            <p className="text-muted-foreground">Passo desconhecido.</p>
          </div>
        );
    }

    return (
      <>
        {viewingPastBar}
        {content}
      </>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/reels" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
        <h1 className="text-xl font-bold tracking-tight">Reel Interativo</h1>
      </div>

      <StepperHeader
        currentStep={currentStep}
        stepState={state}
        displayStep={displayStep}
        onStepClick={setViewStep}
      />

      <StepContent currentStep={currentStep} displayStep={displayStep}>
        {renderStepContent()}
      </StepContent>
    </div>
  );
}
