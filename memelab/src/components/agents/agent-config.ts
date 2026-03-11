import {
  Globe, MessageCircle, Rss, Youtube, Sparkles, Flame,
  type LucideIcon,
} from "lucide-react";

export interface AgentPersona {
  label: string;
  icon: LucideIcon;
  color: string;           // tailwind text color
  bgGradient: string;      // gradient for modal header
  accentHex: string;       // hex for Framer Motion glow
  glowColor: string;       // rgba for box-shadow
  iconBg: string;          // bg class for icon container
  badgeClass: string;      // badge styling
  description: string;     // short description
  animationType: "pulse" | "orbit" | "wave" | "bounce" | "sparkle" | "flame";
}

export const AGENT_PERSONAS: Record<string, AgentPersona> = {
  google_trends: {
    label: "Google Trends",
    icon: Globe,
    color: "text-blue-400",
    bgGradient: "from-blue-600/20 via-blue-500/10 to-transparent",
    accentHex: "#60a5fa",
    glowColor: "rgba(96, 165, 250, 0.3)",
    iconBg: "bg-blue-500/15 ring-1 ring-blue-500/30",
    badgeClass: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    description: "Trending topics do Google Brasil via RSS",
    animationType: "pulse",
  },
  reddit_memes: {
    label: "Reddit Memes",
    icon: MessageCircle,
    color: "text-orange-400",
    bgGradient: "from-orange-600/20 via-orange-500/10 to-transparent",
    accentHex: "#fb923c",
    glowColor: "rgba(251, 146, 60, 0.3)",
    iconBg: "bg-orange-500/15 ring-1 ring-orange-500/30",
    badgeClass: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    description: "8 subreddits brasileiros de memes",
    animationType: "bounce",
  },
  rss_feeds: {
    label: "RSS Feeds",
    icon: Rss,
    color: "text-amber-400",
    bgGradient: "from-amber-600/20 via-amber-500/10 to-transparent",
    accentHex: "#fbbf24",
    glowColor: "rgba(251, 191, 36, 0.3)",
    iconBg: "bg-amber-500/15 ring-1 ring-amber-500/30",
    badgeClass: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    description: "Sensacionalista + Reddit RSS",
    animationType: "wave",
  },
  youtube_rss: {
    label: "YouTube",
    icon: Youtube,
    color: "text-red-400",
    bgGradient: "from-red-600/20 via-red-500/10 to-transparent",
    accentHex: "#f87171",
    glowColor: "rgba(248, 113, 113, 0.3)",
    iconBg: "bg-red-500/15 ring-1 ring-red-500/30",
    badgeClass: "bg-red-500/15 text-red-400 border-red-500/30",
    description: "Canais BR: Porta dos Fundos, KondZilla...",
    animationType: "bounce",
  },
  gemini_web_trends: {
    label: "Gemini Web",
    icon: Sparkles,
    color: "text-violet-400",
    bgGradient: "from-violet-600/20 via-violet-500/10 to-transparent",
    accentHex: "#a78bfa",
    glowColor: "rgba(167, 139, 250, 0.3)",
    iconBg: "bg-violet-500/15 ring-1 ring-violet-500/30",
    badgeClass: "bg-violet-500/15 text-violet-400 border-violet-500/30",
    description: "Gemini + Google Search grounding, 15 topics",
    animationType: "sparkle",
  },
  brazil_viral_rss: {
    label: "Brasil Viral",
    icon: Flame,
    color: "text-emerald-400",
    bgGradient: "from-emerald-600/20 via-emerald-500/10 to-transparent",
    accentHex: "#34d399",
    glowColor: "rgba(52, 211, 153, 0.3)",
    iconBg: "bg-emerald-500/15 ring-1 ring-emerald-500/30",
    badgeClass: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    description: "Subreddits meme BR + portais (Hypeness, Omelete)",
    animationType: "flame",
  },
};

export function getAgentPersona(name: string): AgentPersona {
  return (
    AGENT_PERSONAS[name] ?? {
      label: name,
      icon: Globe,
      color: "text-muted-foreground",
      bgGradient: "from-zinc-600/20 via-zinc-500/10 to-transparent",
      accentHex: "#a1a1aa",
      glowColor: "rgba(161, 161, 170, 0.3)",
      iconBg: "bg-zinc-500/15 ring-1 ring-zinc-500/30",
      badgeClass: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
      description: "Agent",
      animationType: "pulse" as const,
    }
  );
}
