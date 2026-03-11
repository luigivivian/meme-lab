"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import * as api from "@/lib/api";

interface PipelineState {
  isRunning: boolean;
  runId: string | null;
  status: api.PipelineRunResult | null;
  error: string | null;
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>({
    isRunning: false,
    runId: null,
    status: null,
    error: null,
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const run = useCallback(
    async (params: api.PipelineRunParams) => {
      stopPolling();
      setState({ isRunning: true, runId: null, status: null, error: null });

      try {
        const result = await api.runPipeline(params);
        const runId = result.run_id;
        setState((s) => ({ ...s, runId }));

        pollRef.current = setInterval(async () => {
          try {
            const status = await api.getPipelineStatus(runId);
            setState((s) => ({ ...s, status }));
            if (status.status === "completed" || status.status === "error" || status.status === "failed") {
              stopPolling();
              setState((s) => ({ ...s, isRunning: false }));
            }
          } catch {
            // keep polling
          }
        }, 2000);
      } catch (err) {
        setState({
          isRunning: false,
          runId: null,
          status: null,
          error: err instanceof Error ? err.message : "Erro desconhecido",
        });
      }
    },
    [stopPolling]
  );

  useEffect(() => stopPolling, [stopPolling]);

  return { ...state, run, stopPolling };
}
