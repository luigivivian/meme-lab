"use client";

import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useAdSteps } from "@/hooks/use-ads";
import { executeAdStep, approveAdStep, regenerateAdStep } from "@/lib/api";
import { AdStepper, AdStepContent, ADS_STEP_ORDER } from "@/components/ads/stepper";
import { StepAnalysis } from "@/components/ads/step-analysis";
import { StepScene } from "@/components/ads/step-scene";
import { StepPrompt } from "@/components/ads/step-prompt";
import { StepVideo } from "@/components/ads/step-video";
import { StepCopy } from "@/components/ads/step-copy";
import { StepAudio } from "@/components/ads/step-audio";
import { StepAssembly } from "@/components/ads/step-assembly";
import { StepExport } from "@/components/ads/step-export";

export default function AdJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { data, error, isLoading, mutate } = useAdSteps(jobId);

  if (isLoading || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
        <p className="text-sm text-muted-foreground">Carregando ad...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/ads" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center">
          <p className="text-red-400">Ad nao encontrado ou erro ao carregar.</p>
        </div>
      </div>
    );
  }

  const currentStepName = data.current_step;
  const currentStepIndex = ADS_STEP_ORDER.indexOf(currentStepName);
  const stepsMap: Record<string, (typeof data.steps)[number]> = {};
  for (const s of data.steps) stepsMap[s.step_name] = s;

  async function handleApprove(stepName: string) {
    await approveAdStep(jobId, stepName);
    const nextIdx = ADS_STEP_ORDER.indexOf(stepName) + 1;
    if (nextIdx < ADS_STEP_ORDER.length) {
      await executeAdStep(jobId, ADS_STEP_ORDER[nextIdx]);
    }
    mutate();
  }

  async function handleRegenerate(stepName: string) {
    await regenerateAdStep(jobId, stepName);
    mutate();
  }

  const analysisStep = stepsMap["analysis"];
  const analysisNiche =
    (analysisStep?.status === "approved" || analysisStep?.status === "completed")
      ? ((analysisStep.result as Record<string, unknown> | undefined)?.niche as string) ?? ""
      : "";

  function renderStepContent() {
    const stepData = stepsMap[currentStepName];
    const props = {
      stepState: stepData ?? { step_name: currentStepName, status: "pending" as const },
      onApprove: () => handleApprove(currentStepName),
      onRegenerate: () => handleRegenerate(currentStepName),
      jobId,
    };

    switch (currentStepName) {
      case "analysis":
        return <StepAnalysis {...props} />;
      case "scene":
        return <StepScene {...props} niche={analysisNiche} />;
      case "prompt":
        return <StepPrompt {...props} niche={analysisNiche} />;
      case "video":
        return <StepVideo {...props} />;
      case "copy":
        return <StepCopy {...props} />;
      case "audio":
        return <StepAudio {...props} />;
      case "assembly":
        return <StepAssembly {...props} />;
      case "export":
        return <StepExport {...props} />;
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
        <Link href="/ads" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
        <h1 className="text-xl font-bold tracking-tight">Product Ad</h1>
      </div>

      <AdStepper currentStep={currentStepName} steps={data.steps} />

      <AdStepContent currentStep={currentStepIndex}>
        {renderStepContent()}
      </AdStepContent>
    </div>
  );
}
