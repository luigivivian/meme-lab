import useSWR from "swr";
import * as api from "@/lib/api";

export function useStatus() {
  return useSWR("status", () => api.getStatus(), {
    refreshInterval: 10000,
    errorRetryCount: 2,
  });
}

export function useAgents() {
  return useSWR("agents", () => api.getAgents(), {
    refreshInterval: 15000,
  });
}

export function usePipelineRuns() {
  return useSWR("pipeline-runs", () => api.getPipelineRuns(), {
    refreshInterval: 10000,
  });
}

export function useLatestImages(count = 4) {
  return useSWR(`latest-images-${count}`, () => api.getLatestImages(count), {
    refreshInterval: 30000,
  });
}

export function useDriveImages(query?: api.DriveQuery) {
  const key = `drive-images-${query?.theme ?? ""}-${query?.limit ?? 20}-${query?.offset ?? 0}`;
  return useSWR(key, () => api.getDriveImages(query), {
    refreshInterval: 30000,
  });
}

export function useDriveThemes() {
  return useSWR("drive-themes", () => api.getDriveThemes(), {
    refreshInterval: 60000,
  });
}

export function useDriveHealth() {
  return useSWR("drive-health", () => api.getDriveHealth(), {
    refreshInterval: 30000,
  });
}

export function useThemes() {
  return useSWR("themes", () => api.getThemes(), {
    refreshInterval: 60000,
  });
}

export function useTrendsFeed(limit = 50) {
  return useSWR(`trends-feed-${limit}`, () => api.getTrendsFeed(limit), {
    refreshInterval: 5 * 60 * 1000,
    revalidateOnFocus: false,
  });
}

export function useTrendsCategories() {
  return useSWR("trends-categories", () => api.getTrendsCategories(), {
    refreshInterval: 0,
    revalidateOnFocus: false,
  });
}

export function useJobs() {
  return useSWR("jobs", () => api.getJobs(), {
    refreshInterval: 5000,
  });
}
