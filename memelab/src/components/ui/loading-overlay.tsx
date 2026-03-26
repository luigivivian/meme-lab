"use client";

import { Loader2 } from "lucide-react";
import { IndeterminateProgress } from "./progress";
import { cn } from "@/lib/utils";

interface LoadingOverlayProps {
  message?: string;
  progress?: number;
  className?: string;
}

export function LoadingOverlay({ message, progress, className }: LoadingOverlayProps) {
  return (
    <div className={cn(
      "flex flex-col items-center justify-center gap-3 py-12",
      className
    )}>
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      {message && (
        <p className="text-sm text-muted-foreground animate-pulse">{message}</p>
      )}
      {progress !== undefined ? (
        <div className="w-48">
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1 text-center text-xs text-muted-foreground">{Math.round(progress)}%</p>
        </div>
      ) : (
        <div className="w-48">
          <IndeterminateProgress />
        </div>
      )}
    </div>
  );
}

interface ActionFeedbackProps {
  loading: boolean;
  success?: string | null;
  error?: string | null;
  progress?: number;
}

export function ActionFeedback({ loading, success, error, progress }: ActionFeedbackProps) {
  if (!loading && !success && !error) return null;

  return (
    <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
      {loading && (
        <div className="flex items-center gap-3 rounded-xl bg-secondary/50 p-3">
          <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground">Processando...</p>
            {progress !== undefined && (
              <div className="mt-1.5">
                <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-in fade-in duration-300">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <p className="text-sm text-emerald-400">{success}</p>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-in fade-in duration-300">
          <div className="h-2 w-2 rounded-full bg-destructive" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}
    </div>
  );
}
