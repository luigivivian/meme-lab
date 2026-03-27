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
  const key = `drive-images-${query?.theme ?? ""}-${query?.category ?? ""}-${query?.limit ?? 20}-${query?.offset ?? 0}`;
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

export function useThemeKeys() {
  return useSWR("theme-keys", () => api.getThemeKeys(), {
    refreshInterval: 0,
    revalidateOnFocus: false,
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

export function useContentPackages(limit = 6) {
  return useSWR(`content-packages-${limit}`, () => api.getContentPackages({ limit }), {
    refreshInterval: 15000,
  });
}

export function useCharacters() {
  return useSWR("characters", () => api.getCharacters(), {
    refreshInterval: 30000,
  });
}

export function useCharacter(slug: string | null) {
  return useSWR(
    slug ? `character-${slug}` : null,
    () => (slug ? api.getCharacter(slug) : null),
    { refreshInterval: 0, revalidateOnFocus: false }
  );
}

export function useCharacterRefs(slug: string | null) {
  return useSWR(
    slug ? `character-refs-${slug}` : null,
    () => (slug ? api.getCharacterRefs(slug) : null),
    { refreshInterval: 5000 }
  );
}

export function useRefsGenerateStatus(slug: string | null, enabled = false) {
  return useSWR(
    slug && enabled ? `refs-generate-${slug}` : null,
    () => (slug ? api.getRefsGenerateStatus(slug) : null),
    { refreshInterval: 2000 }
  );
}

export function useRenderingPresets() {
  return useSWR("rendering-presets", () => api.getRenderingPresets(), {
    refreshInterval: 0,
    revalidateOnFocus: false,
  });
}

export function useCharacterValidation(slug: string | null) {
  return useSWR(
    slug ? `character-validation-${slug}` : null,
    () => (slug ? api.validateCharacter(slug) : null),
    { refreshInterval: 0, revalidateOnFocus: false }
  );
}

export function usePublishingQueue(params?: { status?: string; platform?: string; limit?: number }) {
  const key = `publishing-queue-${params?.status ?? ""}-${params?.platform ?? ""}-${params?.limit ?? 20}`;
  return useSWR(key, () => api.getPublishingQueue(params), {
    refreshInterval: 5000,
  });
}

export function useQueueSummary() {
  return useSWR("queue-summary", () => api.getQueueSummary(), {
    refreshInterval: 10000,
  });
}

export function usePublishingCalendar(startDate: string, endDate: string) {
  return useSWR(
    `publishing-calendar-${startDate}-${endDate}`,
    () => api.getPublishingCalendar(startDate, endDate),
    { refreshInterval: 30000 }
  );
}

export function useBestTimes() {
  return useSWR("best-times", () => api.getBestTimes(), {
    refreshInterval: 0,
    revalidateOnFocus: false,
  });
}

export function useUsage() {
  return useSWR("usage", () => api.getUsage(), {
    refreshInterval: 30000,
  });
}

export function useVideoBudget() {
  return useSWR("video-budget", () => api.getVideoBudget(), {
    refreshInterval: 30000,
    errorRetryCount: 1,
  });
}

export function useVideoStatus(contentPackageId: number | null, enabled = false) {
  return useSWR(
    contentPackageId && enabled ? `video-status-${contentPackageId}` : null,
    () => (contentPackageId ? api.getVideoStatus(contentPackageId) : null),
    { refreshInterval: 3000 }
  );
}

export function useBillingStatus() {
  return useSWR("billing-status", () => api.getBillingStatus(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useVideoList() {
  const swr = useSWR("video-list", () => api.getVideoList(), {
    refreshInterval: 30000,
    errorRetryCount: 1,
  });
  // Poll faster (3s) when videos are actively generating
  const hasGenerating = swr.data?.videos.some((v) => v.video_status === "generating");
  return useSWR("video-list", () => api.getVideoList(), {
    refreshInterval: hasGenerating ? 3000 : 30000,
    errorRetryCount: 1,
  });
}

export function useVideoGallery(params?: api.VideoGalleryParams) {
  const key = `video-gallery-${params?.status ?? ""}-${params?.model ?? ""}-${params?.sort ?? "newest"}-${params?.limit ?? 50}`;
  return useSWR(key, () => api.getVideoList(params), {
    refreshInterval: 15000,
    errorRetryCount: 1,
  });
}

export function useInstagramStatus() {
  return useSWR("instagram-status", () => api.getInstagramStatus(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useVideoModels() {
  return useSWR("video-models", () => api.getVideoModels(), {
    revalidateOnFocus: false,
  });
}

export function useVideoProgress(contentPackageId: number | null, enabled = false) {
  return useSWR(
    contentPackageId && enabled ? `video-progress-${contentPackageId}` : null,
    () => (contentPackageId ? api.getVideoProgress(contentPackageId) : null),
    { refreshInterval: 3000, errorRetryCount: 1 }
  );
}

export function useDashboardUsageHistory() {
  return useSWR("dashboard-usage-history", () => api.getDashboardUsageHistory(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useDashboardCostBreakdown() {
  return useSWR("dashboard-cost-breakdown", () => api.getDashboardCostBreakdown(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useDashboardPipelineActivity() {
  return useSWR("dashboard-pipeline-activity", () => api.getDashboardPipelineActivity(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useDashboardPublishingStats() {
  return useSWR("dashboard-publishing-stats", () => api.getDashboardPublishingStats(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useVideoCredits(days = 30) {
  return useSWR(`video-credits-${days}`, () => api.getVideoCredits(days), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}

export function useBusinessMetrics() {
  return useSWR("dashboard-business-metrics", () => api.getBusinessMetrics(), {
    refreshInterval: 60000,
    errorRetryCount: 1,
  });
}
