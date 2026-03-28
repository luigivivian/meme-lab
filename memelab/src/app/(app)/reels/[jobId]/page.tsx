"use client";

import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useStepState } from "@/hooks/use-reels";
import { StepperHeader, StepContent } from "@/components/reels/stepper";
import { StepPrompt } from "@/components/reels/step-prompt";
import { StepImages } from "@/components/reels/step-images";
import { StepScript } from "@/components/reels/step-script";

export default function ReelJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { data: stepState, error, isLoading } = useStepState(jobId);

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

  function renderStepContent() {
    switch (currentStep) {
      case 0:
        return <StepPrompt jobId={jobId} stepState={state} />;
      case 1:
        return <StepImages jobId={jobId} stepState={state} />;
      case 2:
        return <StepScript jobId={jobId} stepState={state} />;
      default:
        return (
          <div className="rounded-lg border p-8 text-center">
            <p className="text-muted-foreground">Em breve...</p>
            <p className="text-xs text-muted-foreground mt-1">Passo {currentStep + 1} de 6</p>
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
