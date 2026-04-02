import {
  LayoutDashboard,
  Users,
  Bot,
  Workflow,
  Image,
  Film,
  Clapperboard,
  Megaphone,
  MessageSquareQuote,
  TrendingUp,
  Palette,
  Layers,
  Send,
  CreditCard,
} from "lucide-react";

export const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Personagens", href: "/characters", icon: Users },
  { label: "Agents", href: "/agents", icon: Bot },
  { label: "Pipeline", href: "/pipeline", icon: Workflow },
  { label: "Gallery", href: "/gallery", icon: Image },
  { label: "Videos", href: "/videos", icon: Film },
  { label: "Reels", href: "/reels", icon: Clapperboard },
  { label: "Product Ads", href: "/ads", icon: Megaphone },
  { label: "Phrases", href: "/phrases", icon: MessageSquareQuote },
  { label: "Trends", href: "/trends", icon: TrendingUp },
  { label: "Temas", href: "/themes", icon: Palette },
  { label: "Jobs", href: "/jobs", icon: Layers },
  { label: "Publicar", href: "/publishing", icon: Send },
  { label: "Billing", href: "/billing", icon: CreditCard },
] as const;

export const AGENT_TYPE_COLORS: Record<string, string> = {
  source: "bg-blue-500/20 text-blue-400",
  worker: "bg-emerald-500/20 text-emerald-400",
  processor: "bg-amber-500/20 text-amber-400",
};

export const STATUS_COLORS: Record<string, string> = {
  available: "bg-emerald-500",
  online: "bg-emerald-500",
  offline: "bg-zinc-600",
  running: "bg-amber-500",
  error: "bg-red-500",
};

export const SOURCE_COLORS: Record<string, string> = {
  gemini: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  gemini_free: "bg-sky-500/20 text-sky-400 border-sky-500/30",
  gemini_paid: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  comfyui: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  static: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

export const TREND_SOURCE_COLORS: Record<string, string> = {
  google_trends: "bg-red-500/20 text-red-400",
  reddit: "bg-orange-500/20 text-orange-400",
  rss_feed: "bg-amber-500/20 text-amber-400",
  youtube: "bg-rose-500/20 text-rose-400",
  gemini_trends: "bg-cyan-500/20 text-cyan-400",
  brazil_viral: "bg-green-500/20 text-green-400",
  bluesky: "bg-sky-500/20 text-sky-400",
  hackernews: "bg-orange-500/20 text-orange-300",
  lemmy: "bg-teal-500/20 text-teal-400",
};

export const PUBLISH_STATUS_COLORS: Record<string, string> = {
  queued: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  publishing: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  published: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/20 text-red-400 border-red-500/30",
  cancelled: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

export const PLATFORM_COLORS: Record<string, string> = {
  instagram: "bg-pink-500/20 text-pink-400",
  tiktok: "bg-cyan-500/20 text-cyan-400",
  youtube_shorts: "bg-red-500/20 text-red-400",
  facebook: "bg-blue-500/20 text-blue-400",
};

export const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Reels",
  youtube_shorts: "Shorts",
  tiktok: "TikTok",
  facebook: "Facebook",
};
