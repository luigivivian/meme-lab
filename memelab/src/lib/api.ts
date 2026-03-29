const BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token =
    typeof window !== "undefined"
      ? (localStorage.getItem("access_token") ?? sessionStorage.getItem("access_token"))
      : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    // On 401, redirect to login (per D-02) — skip for auth endpoints to avoid redirect loop
    if (
      res.status === 401 &&
      typeof window !== "undefined" &&
      !path.startsWith("/auth/")
    ) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("refresh_token");
      window.location.href = "/login";
      throw new Error("Sessao expirada");
    }
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// --- Types ---
export interface StatusResponse {
  api_key_ok: boolean;
  refs_loaded: number;
  output_path: string;
  total_images_generated: number;
  total_backgrounds: number;
  jobs_total: number;
  jobs_running: number;
  pipeline_runs: number;
  models: Record<string, unknown>;
  pipeline: string;
}

export interface AgentInfo {
  name: string;
  available: boolean;
  type: "source" | "worker";
}

export interface FetchResult {
  agent: string;
  count: number;
  items: TrendItem[];
}

export interface TrendItem {
  title: string;
  source: string;
  score: number;
  url: string;
  traffic?: number;
}

export interface ImageInfo {
  filename: string;
  theme: string;
  size_kb: number;
  modified_at: string;
  category?: "background" | "meme";
}

export interface DriveImagesResponse {
  total: number;
  offset: number;
  limit: number;
  images: ImageInfo[];
}

export interface DriveLatestResponse {
  count: number;
  images: ImageInfo[];
}

export interface DriveThemesResponse {
  themes: string[];
  counts: Record<string, number>;
}

export interface DriveHealthResponse {
  output_folder: string;
  output_exists: boolean;
  total_images: number;
  refs_folder: string;
  refs_exists: boolean;
}

export interface StepStatus {
  status: "idle" | "running" | "done" | "error";
  detail: string;
}

export interface LayerStatus {
  status: "idle" | "running" | "done" | "error";
  detail: string;
  steps?: Record<string, StepStatus>;
}

export interface PipelineRunResult {
  run_id: string;
  status: string;
  trends_fetched: number;
  work_orders: number;
  images_generated: number;
  packages_produced: number;
  errors: string[];
  content: ContentPackage[];
  duration_seconds: number;
  layers?: Record<string, LayerStatus>;
  current_layer?: string | null;
}

export interface ImageMetadata {
  pose?: string;
  scene?: string;
  theme_key?: string;
  prompt_used?: string;
  reference_images?: string[];
  rendering_config?: Record<string, string>;
  phrase_context_used?: boolean;
  character_dna_used?: boolean;
  tier?: string;  // "gemini_free" or "gemini_paid" — added Phase 11
}

export interface ContentPackage {
  id?: number;
  phrase: string;
  image_path: string;
  topic: string;
  caption: string;
  hashtags: string;
  quality_score: number;
  approval_status?: string;
  background_path?: string;
  background_source?: string;
  image_metadata?: ImageMetadata;
  character_id?: number;
}

export interface PipelineRunSummary {
  run_id: string;
  status: string;
  packages_produced: number;
  images_generated: number;
  trends_fetched: number;
  duration_seconds: number | null;
  started_at: string | null;
  finished_at: string | null;
  errors: string[];
}

export interface PipelineRunsResponse {
  total: number;
  offset: number;
  limit: number;
  runs: PipelineRunSummary[];
}

export interface ThemeInfo {
  key: string;
  label: string;
  count: number;
  acao?: string;
  cenario?: string;
}

export interface ThemesResponse {
  total: number;
  offset: number;
  limit: number;
  themes: ThemeInfo[];
}

export interface ComposeResponse {
  success: boolean;
  image_path: string;
  phrase: string;
  background: string;
}

export interface PhrasesResponse {
  topic: string;
  phrases: string[];
  count: number;
}

// --- Single Generation ---
export interface SingleGenParams {
  theme_key: string;
  acao_custom?: string;
  cenario_custom?: string;
  auto_refine?: boolean;
  refinement_passes?: number;
}

export interface SingleGenResponse {
  success: boolean;
  theme: string;
  file: string;
  path: string;
  refined: boolean;
  refinement_passes: number;
}

// --- Refinement ---
export interface RefineParams {
  filename: string;
  instrucao: string;
  referencias_adicionais?: number;
  passes?: number;
}

export interface RefinePassResult {
  pass: number;
  file: string;
  path: string;
}

export interface RefineResponse {
  success: boolean;
  original: string;
  passes_completed: number;
  passes_requested: number;
  results: RefinePassResult[];
  final_file: string;
}

// --- Jobs ---
export interface BatchThemeItem {
  key: string;
  acao?: string;
  cenario?: string;
  count?: number;
}

export interface BatchParams {
  themes: (string | BatchThemeItem)[];
  n_refs?: number;
  pausa?: number;
  auto_refine?: boolean;
  refinement_passes?: number;
}

export interface BatchResponse {
  job_id: string;
  status: string;
  total_themes: number;
  auto_refine: boolean;
}

export interface JobResult {
  theme: string;
  file: string;
  path: string;
  refined: boolean;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed";
  done: number;
  failed: number;
  total: number;
  results: JobResult[];
  errors: string[];
  created_at: string;
  finished_at: string | null;
  auto_refine: boolean;
  refinement_passes: number;
}

export interface JobsListResponse {
  total: number;
  jobs: JobStatus[];
}

// --- Theme Enhance ---
export interface EnhanceResponse {
  original_input: string;
  enhanced_theme: ThemeInfo & { acao: string; cenario: string };
  saved_to_db: boolean;
  prompt_preview: string;
}

// --- Theme Generate ---
export interface GenerateThemesParams {
  count?: number;
  categories?: string[];
  avoid_existing?: boolean;
  save_to_db?: boolean;
  character_id?: number | null;
}

export interface GenerateThemesResponse {
  generated: number;
  saved_to_db: boolean;
  themes: ThemeInfo[];
}

// --- Trends Feed ---
export interface TrendFeedItem {
  title: string;
  source: string;
  score: number;
  url: string;
  traffic?: number;
  category: string;
  velocity: number;
  sentiment: string;
  event_id: string;
  fetched_at: string;
  _agent: string;
  _resumo?: string;
}

export interface TrendsFeedResponse {
  total: number;
  items: TrendFeedItem[];
  agent_counts: Record<string, number>;
  category_counts: Record<string, number>;
}

export interface TrendsSearchResponse {
  total: number;
  items: TrendFeedItem[];
  query: string;
}

export interface TrendCategory {
  key: string;
  label: string;
  keywords: string[];
}

export interface TrendCategoriesResponse {
  categories: TrendCategory[];
  preferences: {
    favorites: string[];
    hidden: string[];
  };
}

// --- Content Packages (DB) ---
export interface ContentPackageDB {
  id: number;
  phrase: string;
  topic: string;
  source: string;
  image_path: string;
  background_path: string | null;
  background_source: string;
  caption: string;
  hashtags: string[];
  quality_score: number;
  approval_status?: string;
  image_metadata: ImageMetadata;
  is_published: boolean;
  published_at: string | null;
  created_at: string | null;
  pipeline_run_id: number | null;
  character_id: number | null;
  video_status: string | null;
  video_path: string | null;
  video_task_id: string | null;
  video_metadata: Record<string, unknown> | null;
}

export interface ContentPackagesResponse {
  total: number;
  offset: number;
  limit: number;
  packages: ContentPackageDB[];
}

// --- Usage ---
export interface ServiceUsage {
  service: string;
  tier: string;
  used: number;
  limit: number;
  remaining: number;
}

export interface UsageResponse {
  services: ServiceUsage[];
  resets_at: string;
}

export const getUsage = () => request<UsageResponse>("/auth/me/usage");

// --- Status ---
export const getStatus = () => request<StatusResponse>("/status");

// --- Agents ---
export const getAgents = () => request<AgentInfo[]>("/agents");
export const fetchAgent = (name: string) =>
  request<FetchResult>(`/agents/${name}/fetch`, { method: "POST" });

// --- Trends Feed ---
export const getTrendsFeed = (limit = 50) =>
  request<TrendsFeedResponse>(`/trends/feed?limit=${limit}`);
export const getTrendsCategories = () =>
  request<TrendCategoriesResponse>("/trends/categories");
export const saveCategoryPreferences = (favorites: string[], hidden: string[]) =>
  request<{ favorites: string[]; hidden: string[] }>("/trends/categories/preferences", {
    method: "POST",
    body: JSON.stringify({ favorites, hidden }),
  });
export const searchTrends = (q: string) =>
  request<TrendsSearchResponse>(`/trends/search?q=${encodeURIComponent(q)}`);

// --- Pipeline ---
export interface TopicInput {
  topic: string;
  humor_angle?: string;
}

export interface PipelineRunParams {
  count?: number;
  phrases_per_topic?: number;
  use_gemini_image?: boolean;
  use_phrase_context?: boolean;
  use_comfyui?: boolean;
  theme_tags?: string[];
  character_slug?: string;
  background_mode?: "auto" | "comfyui" | "gemini" | "static";
  topics?: TopicInput[];
}

export interface ThemeKeysResponse {
  total: number;
  keys: string[];
}
export const runPipeline = (params: PipelineRunParams) =>
  request<PipelineRunResult>("/pipeline/run", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const runPipelineSync = (params: PipelineRunParams) =>
  request<PipelineRunResult>("/pipeline/run-sync", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const getPipelineStatus = (runId: string) =>
  request<PipelineRunResult>(`/pipeline/status/${runId}`);
export const getPipelineRuns = () =>
  request<PipelineRunsResponse>("/pipeline/runs");

// --- Manual Pipeline (Phase 12) ---

export interface ManualRunParams {
  input_mode: "topic" | "phrase";
  topic?: string;
  phrases?: string[];
  count?: number;
  theme_key?: string;
  background_type?: "solid" | "image";
  background_color?: string;
  background_image?: string;
  layout?: string;
  enable_l5?: boolean;
  use_gemini_image?: boolean;
  character_slug?: string;
}

export interface ThemeWithColors {
  key: string;
  label: string;
  colors: string[];
}

export interface BackgroundFile {
  filename: string;
  path: string;
}

export interface ApprovalResponse {
  id?: number;
  updated?: number;
  approval_status: string;
}

export const manualRun = (params: ManualRunParams) =>
  request<PipelineRunResult>("/pipeline/manual-run", {
    method: "POST",
    body: JSON.stringify(params),
  });

export const approveContent = (packageId: number) =>
  request<ApprovalResponse>(`/pipeline/content/${packageId}/approve`, { method: "PATCH" });

export const rejectContent = (packageId: number) =>
  request<ApprovalResponse>(`/pipeline/content/${packageId}/reject`, { method: "PATCH" });

export const unrejectContent = (packageId: number) =>
  request<ApprovalResponse>(`/pipeline/content/${packageId}/unreject`, { method: "PATCH" });

export const bulkApproveContent = (packageIds: number[]) =>
  request<ApprovalResponse>("/pipeline/content/bulk-approve", {
    method: "PATCH",
    body: JSON.stringify({ package_ids: packageIds }),
  });

export const bulkRejectContent = (packageIds: number[]) =>
  request<ApprovalResponse>("/pipeline/content/bulk-reject", {
    method: "PATCH",
    body: JSON.stringify({ package_ids: packageIds }),
  });

export const uploadBackground = async (file: File, characterSlug: string) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(
    `${BASE}/pipeline/backgrounds/upload?character_slug=${encodeURIComponent(characterSlug)}`,
    { method: "POST", headers, body: formData }
  );
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Upload ${res.status}: ${text}`);
  }
  return res.json() as Promise<{ filename: string; path: string; width: number; height: number }>;
};

export const listBackgrounds = (characterSlug: string) =>
  request<{ backgrounds: BackgroundFile[] }>(`/pipeline/backgrounds/${encodeURIComponent(characterSlug)}`);

export const deleteBackground = (filename: string, characterSlug: string) =>
  request<{ deleted: string }>(
    `/pipeline/backgrounds/${encodeURIComponent(characterSlug)}/${encodeURIComponent(filename)}`,
    { method: "DELETE" }
  );

export const backgroundImageUrl = (filename: string, characterSlug: string) =>
  `${BASE}/pipeline/backgrounds/${encodeURIComponent(characterSlug)}/image/${encodeURIComponent(filename)}`;

export const getThemesWithColors = () =>
  request<{ themes: ThemeWithColors[] }>("/pipeline/themes");

// --- Generation ---
export interface ComposeParams {
  phrase: string;
  background_filename?: string;
  situacao?: string;
  descricao_custom?: string;
  cenario_custom?: string;
  auto_refine?: boolean;
  refinement_passes?: number;
  use_phrase_context?: boolean;
}
export const composeMeme = (params: ComposeParams) =>
  request<ComposeResponse>("/generate/compose", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const generateSingle = (params: SingleGenParams) =>
  request<SingleGenResponse>("/generate/single", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const refineImage = (params: RefineParams) =>
  request<RefineResponse>("/generate/refine", {
    method: "POST",
    body: JSON.stringify(params),
  });

// --- Phrases ---
export interface PhraseParams {
  topic: string;
  count?: number;
}
export const generatePhrases = (params: PhraseParams) =>
  request<PhrasesResponse>("/phrases/generate", {
    method: "POST",
    body: JSON.stringify(params),
  });

// --- Themes ---
export const getThemes = () => request<ThemesResponse>("/themes");
export const addTheme = (theme: Record<string, unknown>) =>
  request<{ added: string; total_themes: number }>("/themes", {
    method: "POST",
    body: JSON.stringify(theme),
  });
export const deleteTheme = (key: string) =>
  request<{ removed: string; total_themes: number }>(`/themes/${key}`, {
    method: "DELETE",
  });
export const generateThemes = (params?: GenerateThemesParams) =>
  request<GenerateThemesResponse>("/themes/generate", {
    method: "POST",
    body: params ? JSON.stringify(params) : undefined,
  });
export const getThemeKeys = () => request<ThemeKeysResponse>("/themes/keys");
export const enhanceTheme = (concept: string, save = false) =>
  request<EnhanceResponse>("/themes/enhance", {
    method: "POST",
    body: JSON.stringify({ input_text: concept, save_to_db: save }),
  });

// --- Jobs ---
export const createBatchJob = (params: BatchParams) =>
  request<BatchResponse>("/jobs/batch", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const createBatchFromConfig = (autoRefine = false, passes = 1) =>
  request<BatchResponse>(
    `/jobs/batch/from-config?auto_refine=${autoRefine}&refinement_passes=${passes}`,
    { method: "POST" }
  );
export const getJobStatus = (jobId: string) =>
  request<JobStatus>(`/jobs/${jobId}`);
export const getJobs = () => request<JobsListResponse>("/jobs");

export const getContentPackages = (params?: { limit?: number; offset?: number }) => {
  const p = new URLSearchParams();
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset) p.set("offset", String(params.offset));
  const qs = p.toString();
  return request<ContentPackagesResponse>(`/content${qs ? `?${qs}` : ""}`);
};

// --- Drive ---
export interface DriveQuery {
  theme?: string;
  category?: "background" | "meme";
  limit?: number;
  offset?: number;
}
export const getDriveImages = (q?: DriveQuery) => {
  const params = new URLSearchParams();
  if (q?.theme) params.set("theme", q.theme);
  if (q?.category) params.set("category", q.category);
  if (q?.limit) params.set("limit", String(q.limit));
  if (q?.offset) params.set("offset", String(q.offset));
  const qs = params.toString();
  return request<DriveImagesResponse>(`/drive/images${qs ? `?${qs}` : ""}`);
};
export const getLatestImages = (count = 4) =>
  request<DriveLatestResponse>(`/drive/images/latest?count=${count}`);
export const getDriveThemes = () =>
  request<DriveThemesResponse>("/drive/themes");
export const getDriveHealth = () =>
  request<DriveHealthResponse>("/drive/health");
export const imageUrl = (filename: string) =>
  `${BASE}/drive/images/${encodeURIComponent(filename)}`;

export const videoFileUrl = (contentPackageId: number) =>
  `${BASE}/generate/video/file/${contentPackageId}`;

export const imageDownloadUrl = (filename: string) =>
  `${BASE}/drive/images/${encodeURIComponent(filename)}/download`;

// --- Video Delete ---

export const deleteVideo = (contentPackageId: number) =>
  request<{ deleted: boolean }>(`/generate/video/${contentPackageId}`, { method: "DELETE" });

// --- Video Approve ---

export const approveVideo = (contentPackageId: number) =>
  request<{ content_package_id: number; approved: boolean }>(
    `/generate/video/${contentPackageId}/approve`,
    { method: "PATCH" }
  );

// --- Instagram OAuth ---

export interface InstagramStatus {
  connected: boolean;
  ig_username: string | null;
  ig_user_id: string | null;
  page_id: string | null;
  token_expires_at: string | null;
  connected_at: string | null;
  status: string | null;
}

export const getInstagramStatus = () =>
  request<InstagramStatus>("/publishing/instagram/status");

export const getInstagramAuthUrl = () =>
  request<{ auth_url: string; state: string }>("/publishing/instagram/auth-url");

export const disconnectInstagram = () =>
  request<{ disconnected: boolean }>("/publishing/instagram/disconnect", { method: "POST" });

export const instagramCallback = (code: string) =>
  request<{ connected: boolean }>("/publishing/instagram/callback", {
    method: "POST",
    body: JSON.stringify({ code }),
  });

// --- Characters ---
export interface CharacterRefsStats {
  approved: number;
  pending: number;
  rejected: number;
  min_required: number;
  ideal: number;
  is_ready: boolean;
}

export interface CharacterSummary {
  slug: string;
  name: string;
  handle: string;
  status: "draft" | "refining" | "ready";
  avatar: string | null;
  refs: CharacterRefsStats;
  themes_count: number;
}

export interface CharacterPersona {
  system_prompt: string;
  humor_style: string;
  tone: string;
  catchphrases: string[];
  rules: { max_chars: number; forbidden: string[] };
}

export interface RenderingConfig {
  art_style?: string;
  art_style_custom?: string;
  lighting?: string;
  lighting_custom?: string;
  camera?: string;
  camera_custom?: string;
  extra_instructions?: string;
}

export interface RenderingPreset {
  label: string;
  prompt: string;
}

export interface RenderingPresetsResponse {
  art_style: Record<string, RenderingPreset>;
  lighting: Record<string, RenderingPreset>;
  camera: Record<string, RenderingPreset>;
}

export interface CharacterVisual {
  character_dna: string;
  negative_traits: string;
  composition: string;
  rendering: RenderingConfig;
}

export interface CharacterComfyUI {
  trigger_word: string;
  character_dna: string;
  lora_path: string;
}

export interface CharacterBranding {
  branded_hashtags: string[];
  caption_prompt: string;
}

export interface CharacterStyleConfig {
  overlay_color: number[];
  glow_color: number[];
  text_color: number[];
  text_stroke_width: number;
  text_vertical_position: number;
  font_size: number;
  watermark_color: number[];
  watermark_font_size: number;
}

export interface CharacterDetail {
  slug: string;
  name: string;
  handle: string;
  watermark: string;
  status: "draft" | "refining" | "ready";
  persona: CharacterPersona;
  visual: CharacterVisual;
  comfyui: CharacterComfyUI;
  branding: CharacterBranding;
  style: CharacterStyleConfig;
  refs: CharacterRefsStats;
  themes_count: number;
}

export interface CharacterCreateParams {
  name: string;
  handle?: string;
  watermark?: string;
  persona?: Partial<CharacterPersona>;
  visual?: Partial<CharacterVisual>;
  comfyui?: Partial<CharacterComfyUI>;
  branding?: Partial<CharacterBranding>;
  style?: Partial<CharacterStyleConfig>;
}

export interface CharacterUpdateParams {
  name?: string;
  handle?: string;
  watermark?: string;
  status?: string;
  persona?: Partial<CharacterPersona>;
  visual?: Partial<CharacterVisual>;
  comfyui?: Partial<CharacterComfyUI>;
  branding?: Partial<CharacterBranding>;
  style?: Partial<CharacterStyleConfig>;
  refs_config?: Record<string, unknown>;
}

export interface CharactersListResponse {
  total: number;
  offset: number;
  limit: number;
  characters: CharacterSummary[];
}

export const getCharacters = () =>
  request<CharactersListResponse>("/characters");

export const getCharacter = (slug: string) =>
  request<CharacterDetail>(`/characters/${slug}`);

export const createCharacter = (params: CharacterCreateParams) =>
  request<CharacterDetail>("/characters", {
    method: "POST",
    body: JSON.stringify(params),
  });

export const updateCharacter = (slug: string, params: CharacterUpdateParams) =>
  request<CharacterDetail>(`/characters/${slug}`, {
    method: "PUT",
    body: JSON.stringify(params),
  });

export const deleteCharacter = (slug: string) =>
  request<{ deleted: string }>(`/characters/${slug}`, {
    method: "DELETE",
  });

// --- Character Refs ---
export interface RefInfo {
  filename: string;
  status: "approved" | "pending" | "rejected";
  size_kb: number;
  modified_at: string;
}

export interface RefsListResponse {
  slug: string;
  stats: CharacterRefsStats;
  refs: RefInfo[];
}

export interface RefActionResponse {
  status: string;
  filename: string;
  refs_stats?: CharacterRefsStats;
}

export interface RefGenerateJob {
  job_id: string;
  slug: string;
  status: "queued" | "running" | "completed" | "none";
  done: number;
  failed: number;
  total: number;
  results: { filename: string; pose: string; index: number }[];
  errors: string[];
  created_at: string;
  finished_at: string | null;
  message?: string;
}

export const getCharacterRefs = (slug: string) =>
  request<RefsListResponse>(`/characters/${slug}/refs`);

export const generateCharacterRefs = (slug: string, batchSize = 15) =>
  request<RefGenerateJob>(`/characters/${slug}/refs/generate`, {
    method: "POST",
    body: JSON.stringify({ batch_size: batchSize }),
  });

export const getRefsGenerateStatus = (slug: string) =>
  request<RefGenerateJob>(`/characters/${slug}/refs/generate/status`);

export const approveRef = (slug: string, filename: string) =>
  request<RefActionResponse>(`/characters/${slug}/refs/${encodeURIComponent(filename)}/approve`, {
    method: "POST",
  });

export const rejectRef = (slug: string, filename: string) =>
  request<RefActionResponse>(`/characters/${slug}/refs/${encodeURIComponent(filename)}/reject`, {
    method: "POST",
  });

export const deleteRef = (slug: string, filename: string) =>
  request<{ deleted: string; refs_stats: CharacterRefsStats }>(`/characters/${slug}/refs/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });

export const refImageUrl = (slug: string, filename: string) =>
  `${BASE}/characters/${slug}/refs/image/${encodeURIComponent(filename)}`;

// --- Character AI Profile Generation ---
export interface GeneratedProfile {
  system_prompt: string;
  humor_style: string;
  tone: string;
  catchphrases: string[];
  max_chars: number;
  forbidden: string[];
  character_dna: string;
  negative_traits: string;
  composition: string;
  branded_hashtags: string[];
  caption_prompt: string;
  watermark: string;
}

export const generateProfile = (name: string, description: string, handle?: string) =>
  request<{ profile: GeneratedProfile }>("/characters/generate-profile", {
    method: "POST",
    body: JSON.stringify({ name, description, handle }),
  });

// --- Character Validation & Testing ---
export interface ValidationCheck {
  area: string;
  item: string;
  ok: boolean;
  detail: string;
}

export interface ValidationResult {
  slug: string;
  status: string;
  checks: ValidationCheck[];
  area_scores: Record<string, number>;
  overall_score: number;
  total_checks: number;
  total_ok: number;
  is_production_ready: boolean;
}

export interface PhraseValidation {
  phrase: string;
  chars: number;
  over_limit: boolean;
  forbidden_found: string[];
  ok: boolean;
}

export interface TestPhrasesResult {
  slug: string;
  topic: string;
  phrases: PhraseValidation[];
  persona_used: {
    humor_style: string;
    tone: string;
    max_chars: number;
  };
}

export interface TestVisualResult {
  success: boolean;
  filename: string;
  slug: string;
  pose: string;
  image_url: string;
}

export interface TestComposeResult {
  success: boolean;
  slug: string;
  phrase: string;
  topic: string;
  situacao: string;
  background_path: string;
  image_path: string;
  image_url: string;
}

export const getRenderingPresets = () =>
  request<RenderingPresetsResponse>("/characters/rendering-presets");

export const validateCharacter = (slug: string) =>
  request<ValidationResult>(`/characters/${slug}/validate`);

export const testCharacterPhrases = (slug: string, topic = "segunda-feira", count = 3) =>
  request<TestPhrasesResult>(`/characters/${slug}/test-phrases`, {
    method: "POST",
    body: JSON.stringify({ topic, count }),
  });

export const testCharacterVisual = (slug: string, pose?: string) =>
  request<TestVisualResult>(`/characters/${slug}/test-visual`, {
    method: "POST",
    body: JSON.stringify({ pose }),
  });

export const testCharacterCompose = (slug: string, topic = "segunda-feira", situacao = "sabedoria") =>
  request<TestComposeResult>(`/characters/${slug}/test-compose`, {
    method: "POST",
    body: JSON.stringify({ topic, situacao }),
  });

// --- Publishing / Scheduling ---
export interface ScheduledPost {
  id: number;
  content_package_id: number;
  character_id: number | null;
  platform: string;
  status: "queued" | "publishing" | "published" | "failed" | "cancelled";
  scheduled_at: string;
  published_at: string | null;
  publish_result: Record<string, unknown> | null;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  content_summary?: {
    phrase: string;
    topic: string;
    image_path: string;
    quality_score: number;
  };
  character_name?: string;
}

export interface ScheduledPostsResponse {
  total: number;
  offset: number;
  limit: number;
  items: ScheduledPost[];
}

export interface QueueSummary {
  total: number;
  by_status: Record<string, number>;
  by_platform: Record<string, number>;
}

export interface CalendarDay {
  post_id: number;
  time: string;
  platform: string;
  status: string;
  content_summary: {
    phrase: string;
    topic: string;
    quality_score: number;
  };
}

export interface CalendarResponse {
  dates: Record<string, CalendarDay[]>;
  start_date: string;
  end_date: string;
}

export interface BestTimesResponse {
  monday: string[];
  tuesday: string[];
  wednesday: string[];
  thursday: string[];
  friday: string[];
  saturday: string[];
  sunday: string[];
}

// --- Publishing API functions ---
export const schedulePost = (params: {
  content_package_id: number;
  platform?: string;
  scheduled_at: string;
  character_id?: number;
}) =>
  request<ScheduledPost>("/publishing/schedule", {
    method: "POST",
    body: JSON.stringify(params),
  });

export const getPublishingQueue = (params?: {
  status?: string;
  platform?: string;
  limit?: number;
  offset?: number;
}) => {
  const p = new URLSearchParams();
  if (params?.status) p.set("status", params.status);
  if (params?.platform) p.set("platform", params.platform);
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset) p.set("offset", String(params.offset));
  const qs = p.toString();
  return request<ScheduledPostsResponse>(`/publishing/queue${qs ? `?${qs}` : ""}`);
};

export const getQueueSummary = () =>
  request<QueueSummary>("/publishing/queue/summary");

export const getScheduledPost = (postId: number) =>
  request<ScheduledPost>(`/publishing/queue/${postId}`);

export const cancelScheduledPost = (postId: number) =>
  request<ScheduledPost>(`/publishing/queue/${postId}/cancel`, { method: "POST" });

export const retryScheduledPost = (postId: number) =>
  request<ScheduledPost>(`/publishing/queue/${postId}/retry`, { method: "POST" });

export const getPublishingCalendar = (startDate: string, endDate: string) =>
  request<CalendarResponse>(
    `/publishing/calendar?start_date=${startDate}&end_date=${endDate}`
  );

export const getBestTimes = () =>
  request<BestTimesResponse>("/publishing/best-times");

// --- Video Generation (Phase 999.1) ---
export interface VideoGenerateRequest {
  content_package_id: number;
  duration: number; // 10 or 15
  character_ids?: string[];
  custom_prompt?: string;
  model?: string;
}

export interface VideoStatusResponse {
  content_package_id: number;
  video_status: string | null;
  video_task_id: string | null;
  video_path: string | null;
  video_source: string | null;
  video_metadata: Record<string, unknown> | null;
}

export interface VideoBudgetResponse {
  daily_budget_usd: number;
  spent_today_usd: number;
  remaining_usd: number;
  videos_remaining_estimate: number;
}

export const generateVideo = (params: VideoGenerateRequest) =>
  request<VideoStatusResponse>("/generate/video", {
    method: "POST",
    body: JSON.stringify(params),
  });

export interface VideoFromImageRequest {
  filename: string;
  duration: number;
  character_ids?: string[];
  custom_prompt?: string;
  model?: string;
}

export const generateVideoFromImage = (params: VideoFromImageRequest) =>
  request<VideoStatusResponse>("/generate/video/from-image", {
    method: "POST",
    body: JSON.stringify(params),
  });

export const generateVideoBatch = (params: {
  content_package_ids: number[];
  duration?: number;
  character_ids?: string[];
}) =>
  request<VideoStatusResponse[]>("/generate/video/batch", {
    method: "POST",
    body: JSON.stringify({ duration: 10, ...params }),
  });

export const getVideoStatus = (contentPackageId: number) =>
  request<VideoStatusResponse>(`/generate/video/status/${contentPackageId}`);

export interface VideoModel {
  id: string;
  name: string;
  resolution: string;
  tier: string;
  durations: number[];
  prices_brl: Record<string, number>;
  speed: number;
  notes: string;
  is_default: boolean;
}

export interface VideoModelsResponse {
  models: VideoModel[];
  default: string;
  usd_to_brl: number;
}

export const getVideoModels = () =>
  request<VideoModelsResponse>("/generate/video/models");

export interface VideoProgressResponse {
  content_package_id: number;
  state: string;
  progress: number;
  step_label: string;
}

export const getVideoProgress = (contentPackageId: number) =>
  request<VideoProgressResponse>(`/generate/video/progress/${contentPackageId}`);

export async function retryVideo(contentPackageId: number): Promise<VideoStatusResponse> {
  return request<VideoStatusResponse>(`/generate/video/retry/${contentPackageId}`, {
    method: "POST",
  });
}

export const getVideoBudget = () =>
  request<VideoBudgetResponse>("/generate/video/budget");

// --- Billing (Phase 17) ---
export interface BillingService {
  service: string;
  tier: string;
  used: number;
  limit: number;
  remaining: number;
}

export interface BillingStatus {
  plan: string;
  plan_name: string;
  subscription_status: string | null;
  subscription_ends_at: string | null;
  stripe_configured: boolean;
  services: BillingService[];
  resets_at: string;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

export async function getBillingStatus(): Promise<BillingStatus> {
  return request<BillingStatus>("/billing/status");
}

export async function createCheckoutSession(
  price_id: string,
  success_url: string,
  cancel_url: string
): Promise<CheckoutResponse> {
  return request<CheckoutResponse>("/billing/create-checkout", {
    method: "POST",
    body: JSON.stringify({ price_id, success_url, cancel_url }),
  });
}

export async function createPortalSession(
  return_url: string
): Promise<PortalResponse> {
  return request<PortalResponse>("/billing/portal", {
    method: "POST",
    body: JSON.stringify({ return_url }),
  });
}

// ── Video List ──────────────────────────────────────────────────────────

export interface VideoListItem {
  content_package_id: number;
  phrase: string;
  topic: string;
  image_path: string | null;
  video_status: string;
  video_path: string | null;
  video_task_id: string | null;
  video_source: string | null;
  video_metadata: Record<string, unknown> | null;
  video_prompt_used: string | null;
  legend_status: string | null;
  legend_path: string | null;
  created_at: string | null;
  is_published: boolean;
}

export interface VideoListResponse {
  total: number;
  videos: VideoListItem[];
}

export interface VideoGalleryParams {
  status?: string;
  model?: string;
  sort?: "newest" | "oldest";
  limit?: number;
}

export async function getVideoList(params?: VideoGalleryParams): Promise<VideoListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.model) searchParams.set("model", params.model);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return request<VideoListResponse>(`/generate/video/list${qs ? `?${qs}` : ""}`);
}

// ── Dashboard Analytics (Phase 16) ──────────────────────────────────────

export interface UsageHistoryResponse {
  history: { date: string; gemini_text: number; gemini_image: number; kie_video: number }[];
}

export interface CostBreakdownResponse {
  services: { service: string; cost_usd: number }[];
  total_cost_usd: number;
}

export interface PipelineActivityResponse {
  activity: { date: string; runs: number; packages: number }[];
}

export interface PublishingStatsResponse {
  total: number;
  published: number;
  queued: number;
  failed: number;
  cancelled: number;
}

export async function getDashboardUsageHistory(): Promise<UsageHistoryResponse> {
  return request<UsageHistoryResponse>("/dashboard/usage-history");
}

export async function getDashboardCostBreakdown(): Promise<CostBreakdownResponse> {
  return request<CostBreakdownResponse>("/dashboard/cost-breakdown");
}

export async function getDashboardPipelineActivity(): Promise<PipelineActivityResponse> {
  return request<PipelineActivityResponse>("/dashboard/pipeline-activity");
}

export async function getDashboardPublishingStats(): Promise<PublishingStatsResponse> {
  return request<PublishingStatsResponse>("/dashboard/publishing-stats");
}

export async function getBusinessMetrics(): Promise<BusinessMetricsResponse> {
  return request<BusinessMetricsResponse>("/dashboard/business-metrics");
}

// ── Business Metrics (Phase 21) ──────────────────────────────────────

export interface PeriodMetric {
  current: number;
  previous: number;
  total: number;
}

export interface CostPeriodMetric {
  current: number;
  previous: number;
}

export interface BudgetMetric {
  daily_remaining: number;
  daily_budget: number;
  daily_spent: number;
}

export interface ActivePackagesMetric {
  current: number;
  total: number;
}

export interface BusinessMetricsResponse {
  videos_generated: PeriodMetric;
  avg_cost_per_video_brl: CostPeriodMetric;
  budget_remaining_brl: BudgetMetric;
  trends_collected: PeriodMetric;
  active_packages: ActivePackagesMetric;
}

// ── Video Credits (Phase 20) ──────────────────────────────────────────

export interface ModelCostBreakdown {
  model_id: string;
  model_name: string;
  count: number;
  total_brl: number;
  avg_brl: number;
}

export interface VideoCreditsResponse {
  days: number;
  total_spent_brl: number;
  total_spent_usd: number;
  total_videos: number;
  avg_cost_brl: number;
  alltime_spent_brl: number;
  alltime_videos: number;
  models: ModelCostBreakdown[];
  failed_count: number;
  failed_zero_cost: boolean;
  daily_budget_brl: number;
  daily_spent_brl: number;
  daily_remaining_brl: number;
}

export async function getVideoCredits(days = 30): Promise<VideoCreditsResponse> {
  return request<VideoCreditsResponse>(`/generate/video/credits/summary?days=${days}`);
}

// --- Reels Pipeline (Phase 999.4) ---

export interface ReelGenerateRequest {
  tema: string;
  character_id?: number;
  character_slug?: string;
  no_character?: boolean;
  config_id?: number;
  tone?: string;
  target_duration?: number;
  niche?: string;
  keywords?: string[];
}

export interface ReelJob {
  job_id: string;
  status: string;
  tema: string;
  current_step?: string;
  progress_pct: number;
  video_url?: string;
  caption?: string;
  hashtags?: string[];
  cost_brl: number;
  error_message?: string;
  created_at: string;
}

export interface ReelsConfig {
  id: number;
  name: string;
  image_count: number;
  tone: string;
  target_duration: number;
  niche: string;
  tts_provider: string;
  tts_voice: string;
  tts_speed: number;
  image_duration: number;
  transition_type: string;
  transition_duration: number;
  subtitle_font_size: number;
  preset?: string;
}

export interface ReelsPresets {
  presets: Record<string, Partial<ReelsConfig>>;
}

export async function generateReel(req: ReelGenerateRequest) {
  return request<{ job_id: string; status: string }>("/reels/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getReelStatus(jobId: string) {
  return request<ReelJob>(`/reels/status/${jobId}`);
}

export async function getReelJobs(status?: string) {
  const params = status ? `?status=${status}` : "";
  return request<ReelJob[]>(`/reels/jobs${params}`);
}

export async function getReelsConfig() {
  return request<ReelsConfig[]>("/reels/config");
}

export async function saveReelsConfig(config: Partial<ReelsConfig>) {
  return request<ReelsConfig>("/reels/config", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function getReelsPresets() {
  return request<ReelsPresets>("/reels/config/presets");
}

// --- Interactive Reels (Phase 999.5) ---

export interface StepState {
  job_id: string;
  current_step: number;
  prompt?: { text: string; approved: boolean; job_dir?: string };
  images?: { paths: string[]; approved: boolean; status?: string };
  script?: { json: Record<string, unknown>; approved: boolean; status?: string };
  tts?: { path: string; approved: boolean; status?: string };
  srt?: { path: string; approved: boolean; status?: string };
  video?: { path: string; approved: boolean; status?: string };
}

export interface StepEditPayload {
  text?: string;
  script_json?: Record<string, unknown>;
  srt_entries?: Array<{ index: number; start: string; end: string; text: string }>;
}

export interface InteractiveReelRequest {
  tema: string;
  character_id?: number;
  character_slug?: string;
  no_character?: boolean;
  config_id?: number;
  target_duration?: number;
}

export async function createInteractiveReel(req: InteractiveReelRequest) {
  return request<{ job_id: string; step_state: StepState }>("/reels/interactive", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getStepState(jobId: string) {
  return request<StepState>(`/reels/${jobId}/step-state`);
}

export async function executeStep(jobId: string, step: string) {
  return request<{ status: string }>(`/reels/${jobId}/step/${step}`, { method: "POST" });
}

export async function approveStep(jobId: string, step: string) {
  return request<{ step: string; approved: boolean; current_step: number }>(
    `/reels/${jobId}/approve/${step}`, { method: "POST" }
  );
}

export async function regenerateStep(jobId: string, step: string) {
  return request<{ status: string }>(`/reels/${jobId}/regenerate/${step}`, { method: "POST" });
}

export async function editStep(jobId: string, step: string, payload: StepEditPayload) {
  return request<{ step: string; updated: boolean }>(
    `/reels/${jobId}/edit/${step}`, { method: "PUT", body: JSON.stringify(payload) }
  );
}

export function reelFileUrl(jobId: string, filename: string): string {
  return `/api/reels/${jobId}/file/${encodeURIComponent(filename)}`;
}

// --- Content Export ---
export const exportContentPack = (packageId: number) =>
  `${BASE}/content/${packageId}/export`;

// ===== Product Ads =====

export interface AdJob {
  job_id: string;
  status: "draft" | "generating" | "complete" | "failed";
  style: "cinematic" | "narrated" | "lifestyle";
  product_name: string;
  video_model: string;
  audio_mode: "mute" | "music" | "narrated" | "ambient";
  step_state: Record<string, { status: string; result?: unknown }> | null;
  current_step: string | null;
  progress_pct: number;
  cost_brl: number | null;
  outputs: Record<string, string> | null;
  created_at: string;
  updated_at: string;
}

export interface AdCreateRequest {
  product_name: string;
  style: "cinematic" | "narrated" | "lifestyle";
  video_model?: string;
  audio_mode?: "mute" | "music" | "narrated" | "ambient";
  output_formats?: string[];
  target_duration?: number;
  tone?: string;
  niche?: string;
  audience?: string;
  scene_description?: string;
  with_human?: boolean;
}

export interface AdCostEstimate {
  video_brl: number;
  audio_brl: number;
  image_brl: number;
  total_brl: number;
}

export interface AdAnalysisResult {
  niche: string;
  tone: string;
  audience: string;
  scene_suggestions: string[];
  product_description: string;
}

export async function createAdJob(data: AdCreateRequest): Promise<AdJob> {
  return request<AdJob>("/ads/create", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export const fetchAdJobs = () => request<AdJob[]>("/ads/jobs");

export const fetchAdJob = (jobId: string) => request<AdJob>(`/ads/${jobId}`);

export const fetchAdSteps = (jobId: string) =>
  request<{ step_state: Record<string, unknown>; current_step: string; progress_pct: number }>(
    `/ads/${jobId}/steps`
  );

export async function executeAdStep(jobId: string, stepName: string) {
  return request<{ status: string }>(`/ads/${jobId}/step/${stepName}`, { method: "POST" });
}

export async function approveAdStep(jobId: string, stepName: string) {
  return request<{ step: string; approved: boolean }>(`/ads/${jobId}/approve/${stepName}`, {
    method: "POST",
  });
}

export async function regenerateAdStep(jobId: string, stepName: string) {
  return request<{ status: string }>(`/ads/${jobId}/regenerate/${stepName}`, { method: "POST" });
}

export const fetchAdCostEstimate = (jobId: string) =>
  request<AdCostEstimate>(`/ads/${jobId}/cost-estimate`);

export async function deleteAdJob(jobId: string) {
  return request<void>(`/ads/${jobId}`, { method: "DELETE" });
}
