import useSWR from "swr";
import * as api from "@/lib/api";

export function useAdJobs() {
  return useSWR(
    "ad-jobs",
    () => api.fetchAdJobs(),
    { refreshInterval: 5000 }
  );
}

export function useAdJob(jobId: string | null) {
  return useSWR(
    jobId ? `ad-job-${jobId}` : null,
    () => api.fetchAdJob(jobId!),
    { refreshInterval: 3000 }
  );
}

export function useAdSteps(jobId: string | null) {
  return useSWR(
    jobId ? `ad-steps-${jobId}` : null,
    () => api.fetchAdSteps(jobId!),
    { refreshInterval: 2000 }
  );
}
