import {
  LayoutDashboard,
  Bot,
  Workflow,
  Image,
  MessageSquareQuote,
  TrendingUp,
  Palette,
  Layers,
} from "lucide-react";

export const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Agents", href: "/agents", icon: Bot },
  { label: "Pipeline", href: "/pipeline", icon: Workflow },
  { label: "Gallery", href: "/gallery", icon: Image },
  { label: "Phrases", href: "/phrases", icon: MessageSquareQuote },
  { label: "Trends", href: "/trends", icon: TrendingUp },
  { label: "Temas", href: "/themes", icon: Palette },
  { label: "Jobs", href: "/jobs", icon: Layers },
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
