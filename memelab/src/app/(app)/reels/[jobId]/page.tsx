"use client";

import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useStepState } from "@/hooks/use-reels";
import { approveStep, regenerateStep } from "@/lib/api";
import { StepperHeader, StepContent } from "@/components/reels/stepper";
import { StepPrompt } from "@/components/reels/step-prompt";
import { StepImages } from "@/components/reels/step-images";
import { StepScript } from "@/components/reels/step-script";
import { StepNarration } from "@/components/reels/step-narration";
import { StepSubtitles } from "@/components/reels/step-subtitles";
import { StepVideo } from "@/components/reels/step-video";

export default function ReelJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { data: stepState, error, isLoading, mutate } = useStepState(jobId);

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

  const currentStep = stepState.current_step;
  const state = stepState!;

  async function handleApprove(step: string) {
    await approveStep(jobId, step);
    mutate();
  }

  async function handleRegenerate(step: string) {
    await regenerateStep(jobId, step);
    mutate();
  }

  function renderStepContent() {
    switch (currentStep) {
      case 0:
        return <StepPrompt jobId={jobId} stepState={state} />;
      case 1:
        return <StepScript jobId={jobId} stepState={state} />;
      case 2:
        return <StepImages jobId={jobId} stepState={state} />;
      case 3:
        return (
          <StepNarration
            jobId={jobId}
            stepData={state.tts}
            onApprove={handleApprove}
            onRegenerate={handleRegenerate}
            mutate={() => mutate()}
          />
        );
      case 4:
        return (
          <StepSubtitles
            jobId={jobId}
            stepData={state.srt}
            onApprove={handleApprove}
            onRegenerate={handleRegenerate}
            mutate={() => mutate()}
          />
        );
      case 5:
        return (
          <StepVideo
            jobId={jobId}
            stepData={state.video}
            mutate={() => mutate()}
          />
        );
      default:
        return (
          <div className="rounded-lg border p-8 text-center">
            <p className="text-muted-foreground">Passo desconhecido.</p>
          </div>
        );
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/reels" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
        <h1 className="text-xl font-bold tracking-tight">Reel Interativo</h1>
      </div>

      <StepperHeader currentStep={currentStep} stepState={state} />

      <StepContent currentStep={currentStep}>
        {renderStepContent()}
      </StepContent>
    </div>
  );
}
