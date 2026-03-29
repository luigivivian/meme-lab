import useSWR from "swr";
import * as api from "@/lib/api";

export function useAdJobs() {
  return useSWR("ad-jobs", () => api.getAdJobs(), { refreshInterval: 5000 });
}

export function useAdJob(jobId: string | null) {
  return useSWR(
    jobId ? `ad-job-${jobId}` : null,
    () => api.getAdJob(jobId!),
    { refreshInterval: 3000, errorRetryCount: 1 }
  );
}

export function useAdSteps(jobId: string | null) {
  return useSWR(
    jobId ? `ad-steps-${jobId}` : null,
    () => api.getAdSteps(jobId!),
    { refreshInterval: 2000, errorRetryCount: 1 }
  );
}
