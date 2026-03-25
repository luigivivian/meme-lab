"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import * as api from "@/lib/api";
import type { ContentPackage, ManualRunParams } from "@/lib/api";

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

interface ManualPipelineState {
  isRunning: boolean;
  runId: string | null;
  results: ContentPackage[];
  error: string | null;
  progress: number;
}

export function useManualPipeline() {
  const [state, setState] = useState<ManualPipelineState>({
    isRunning: false,
    runId: null,
    results: [],
    error: null,
    progress: 0,
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const run = useCallback(
    async (params: ManualRunParams) => {
      stopPolling();
      setState({ isRunning: true, runId: null, results: [], error: null, progress: 0 });

      try {
        const result = await api.manualRun(params);
        const runId = result.run_id;
        setState((s) => ({ ...s, runId }));

        // If already completed (sync response), set results immediately
        if (result.status === "completed" || result.status === "error" || result.status === "failed") {
          setState((s) => ({
            ...s,
            isRunning: false,
            results: result.content ?? [],
            progress: 100,
            error: result.status === "error" || result.status === "failed"
              ? (result.errors?.[0] ?? "Erro desconhecido")
              : null,
          }));
          return;
        }

        pollRef.current = setInterval(async () => {
          try {
            const status = await api.getPipelineStatus(runId);
            const total = (params.count ?? 3) * 2;
            const done = (status.images_generated ?? 0) + (status.packages_produced ?? 0);
            const pct = Math.min(Math.round((done / total) * 100), 95);
            setState((s) => ({ ...s, progress: pct }));

            if (status.status === "completed" || status.status === "error" || status.status === "failed") {
              stopPolling();
              setState((s) => ({
                ...s,
                isRunning: false,
                results: status.content ?? [],
                progress: 100,
                error: status.status === "error" || status.status === "failed"
                  ? (status.errors?.[0] ?? "Erro desconhecido")
                  : null,
              }));
            }
          } catch {
            // keep polling on transient errors
          }
        }, 2000);
      } catch (err) {
        setState({
          isRunning: false,
          runId: null,
          results: [],
          error: err instanceof Error ? err.message : "Erro desconhecido",
          progress: 0,
        });
      }
    },
    [stopPolling]
  );

  const approve = useCallback(async (packageId: number) => {
    // Optimistic update
    setState((s) => ({
      ...s,
      results: s.results.map((r) =>
        r.id === packageId ? { ...r, approval_status: "approved" } : r
      ),
    }));
    try {
      await api.approveContent(packageId);
    } catch {
      // Revert on error
      setState((s) => ({
        ...s,
        results: s.results.map((r) =>
          r.id === packageId ? { ...r, approval_status: "pending" } : r
        ),
      }));
    }
  }, []);

  const reject = useCallback(async (packageId: number) => {
    setState((s) => ({
      ...s,
      results: s.results.map((r) =>
        r.id === packageId ? { ...r, approval_status: "rejected" } : r
      ),
    }));
    try {
      await api.rejectContent(packageId);
    } catch {
      setState((s) => ({
        ...s,
        results: s.results.map((r) =>
          r.id === packageId ? { ...r, approval_status: "pending" } : r
        ),
      }));
    }
  }, []);

  const unreject = useCallback(async (packageId: number) => {
    setState((s) => ({
      ...s,
      results: s.results.map((r) =>
        r.id === packageId ? { ...r, approval_status: "pending" } : r
      ),
    }));
    try {
      await api.unrejectContent(packageId);
    } catch {
      setState((s) => ({
        ...s,
        results: s.results.map((r) =>
          r.id === packageId ? { ...r, approval_status: "rejected" } : r
        ),
      }));
    }
  }, []);

  const bulkApprove = useCallback(async () => {
    const ids = state.results.filter((r) => r.id != null).map((r) => r.id!);
    if (ids.length === 0) return;
    setState((s) => ({
      ...s,
      results: s.results.map((r) => ({ ...r, approval_status: "approved" })),
    }));
    try {
      await api.bulkApproveContent(ids);
    } catch {
      // Revert
      setState((s) => ({
        ...s,
        results: s.results.map((r) => ({ ...r, approval_status: "pending" })),
      }));
    }
  }, [state.results]);

  const bulkReject = useCallback(async () => {
    const ids = state.results.filter((r) => r.id != null).map((r) => r.id!);
    if (ids.length === 0) return;
    setState((s) => ({
      ...s,
      results: s.results.map((r) => ({ ...r, approval_status: "rejected" })),
    }));
    try {
      await api.bulkRejectContent(ids);
    } catch {
      setState((s) => ({
        ...s,
        results: s.results.map((r) => ({ ...r, approval_status: "pending" })),
      }));
    }
  }, [state.results]);

  const reset = useCallback(() => {
    stopPolling();
    setState({
      isRunning: false,
      runId: null,
      results: [],
      error: null,
      progress: 0,
    });
  }, [stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  return {
    ...state,
    run,
    approve,
    reject,
    unreject,
    bulkApprove,
    bulkReject,
    reset,
  };
}
