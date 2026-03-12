"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  TrendingUp, RefreshCw, ExternalLink, Sparkles, Loader2,
  Search, Star, StarOff, Filter, Flame,
  ArrowUpRight, Clock, Settings2, X,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useTrendsFeed, useTrendsCategories } from "@/hooks/use-api";
import type { TrendFeedItem, TrendCategory } from "@/lib/api";
import { searchTrends } from "@/lib/api";

// ── Source agent metadata ────────────────────────────────────────────────────
const SOURCE_META: Record<string, { label: string; icon: string; color: string }> = {
  google_trends:    { label: "Google Trends",    icon: "G",  color: "text-blue-400" },
  reddit_memes:     { label: "Reddit",           icon: "R",  color: "text-orange-400" },
  rss_feeds:        { label: "RSS Feeds",        icon: "◉",  color: "text-amber-400" },
  youtube_rss:      { label: "YouTube",          icon: "▶",  color: "text-red-400" },
  gemini_web_trends:{ label: "Gemini Web",       icon: "✦",  color: "text-violet-400" },
  brazil_viral_rss: { label: "Brasil Viral",     icon: "🇧🇷", color: "text-green-400" },
  gemini_search:    { label: "Busca Gemini",     icon: "🔍", color: "text-cyan-400" },
};

const ALL_AGENTS = Object.keys(SOURCE_META);

// ── Favorites from localStorage ──────────────────────────────────────────────
function loadFavorites(): string[] {
  if (typeof window === "undefined") return ["humor", "cultura_pop", "cotidiano", "viral"];
  try {
    const stored = localStorage.getItem("trends-favorites");
    return stored ? JSON.parse(stored) : ["humor", "cultura_pop", "cotidiano", "viral"];
  } catch { return ["humor", "cultura_pop", "cotidiano", "viral"]; }
}

function saveFavorites(favs: string[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem("trends-favorites", JSON.stringify(favs));
}

// ── Score display ────────────────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const intensity = Math.min(score / 100, 1);
  const bg = intensity > 0.7
    ? "bg-primary/20 text-primary border-primary/30"
    : intensity > 0.3
    ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
    : "bg-secondary text-muted-foreground border-border";
  return (
    <Badge variant="outline" className={`text-[10px] tabular-nums ${bg}`}>
      {score > 0 ? score.toFixed(0) : "—"}
    </Badge>
  );
}

// ── Time ago helper ──────────────────────────────────────────────────────────
function timeAgo(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
    if (diffMin < 1) return "agora";
    if (diffMin < 60) return `${diffMin}min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h`;
    return `${Math.floor(diffH / 24)}d`;
  } catch { return ""; }
}

// ── Highlight matching text ──────────────────────────────────────────────────
function HighlightText({ text, terms }: { text: string; terms: string[] }) {
  if (terms.length === 0) return <>{text}</>;
  const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        escaped.some(e => new RegExp(`^${e}$`, "i").test(part))
          ? <mark key={i} className="bg-primary/25 text-primary rounded-sm px-0.5">{part}</mark>
          : part
      )}
    </>
  );
}

// ── Search helper: match item against multiple terms ────────────────────────
function matchesSearch(item: TrendFeedItem, terms: string[]): boolean {
  const sourceLabel = (SOURCE_META[item._agent]?.label ?? item.source).toLowerCase();
  const searchable = `${item.title} ${item.category} ${sourceLabel} ${item.sentiment}`.toLowerCase();
  return terms.every(t => searchable.includes(t));
}

// ── Trend Card ───────────────────────────────────────────────────────────────
function TrendCard({
  item, index, onGenerate, searchTerms,
}: {
  item: TrendFeedItem; index: number; onGenerate: (title: string) => void; searchTerms: string[];
}) {
  const source = SOURCE_META[item._agent] ?? { label: item.source, icon: "?", color: "text-muted-foreground" };

  return (
    <motion.div variants={staggerItem} whileHover={{ y: -3 }}>
    <Card
      className="group transition-all duration-200 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5"
    >
      <CardContent className="p-4 space-y-3">
        {/* Header: title + score */}
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-sm font-medium leading-tight line-clamp-2 flex-1">
            <HighlightText text={item.title} terms={searchTerms} />
          </h3>
          <ScoreBadge score={item.score} />
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Source badge */}
          <Badge variant="secondary" className="text-[10px] gap-1">
            <span className={source.color}>{source.icon}</span>
            {source.label}
          </Badge>

          {/* Category badge */}
          <Badge variant="outline" className="text-[10px]">
            {item.category}
          </Badge>

          {/* Time */}
          {item.fetched_at && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-0.5 ml-auto">
              <Clock className="h-2.5 w-2.5" />
              {timeAgo(item.fetched_at)}
            </span>
          )}
        </div>

        {/* Resumo from Gemini search */}
        {item._resumo && (
          <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2">
            {item._resumo}
          </p>
        )}

        {/* Traffic indicator */}
        {item.traffic && Number(item.traffic) > 0 && (
          <div className="flex items-center gap-1.5">
            <ArrowUpRight className="h-3 w-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 font-medium">
              {Number(item.traffic) > 1000
                ? `${(Number(item.traffic) / 1000).toFixed(0)}K+ buscas`
                : `${item.traffic} buscas`}
            </span>
          </div>
        )}

        {/* Action row */}
        <div className="flex items-center justify-end gap-1 pt-1 opacity-0 transition-opacity group-hover:opacity-100">
          {item.url && (
            <Button variant="ghost" size="icon" className="h-7 w-7" asChild>
              <a href={item.url} target="_blank" rel="noopener noreferrer" title="Abrir fonte">
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 hover:text-primary"
            onClick={() => onGenerate(item.title)}
            title="Gerar conteudo"
          >
            <Sparkles className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
    </motion.div>
  );
}

// ── Category chip ────────────────────────────────────────────────────────────
function CategoryChip({
  category, count, active, isFavorite, onToggle, onToggleFavorite,
}: {
  category: TrendCategory;
  count: number;
  active: boolean;
  isFavorite: boolean;
  onToggle: () => void;
  onToggleFavorite: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={`
        group/chip flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
        transition-all duration-200 border shrink-0
        ${active
          ? "bg-primary/15 text-primary border-primary/30 shadow-sm shadow-primary/10"
          : "bg-secondary/50 text-muted-foreground border-border hover:border-primary/20 hover:text-foreground"
        }
      `}
    >
      <span>{category.label}</span>
      {count > 0 && (
        <Badge variant="secondary" className="text-[9px] px-1 py-0 h-4 min-w-[18px] justify-center">
          {count}
        </Badge>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onToggleFavorite(); }}
        className="ml-0.5 opacity-0 group-hover/chip:opacity-100 transition-opacity"
        title={isFavorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}
      >
        {isFavorite
          ? <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
          : <StarOff className="h-3 w-3 text-muted-foreground" />}
      </button>
    </button>
  );
}

// ── Source filter pill ────────────────────────────────────────────────────────
function SourcePill({
  agentKey, count, active, onToggle,
}: {
  agentKey: string; count: number; active: boolean; onToggle: () => void;
}) {
  const meta = SOURCE_META[agentKey];
  if (!meta) return null;
  return (
    <button
      onClick={onToggle}
      className={`
        flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium
        transition-all duration-200 border shrink-0
        ${active
          ? "bg-secondary text-foreground border-border"
          : "bg-transparent text-muted-foreground/50 border-transparent hover:text-muted-foreground"
        }
      `}
    >
      <span className={meta.color}>{meta.icon}</span>
      <span>{meta.label}</span>
      <span className="text-[9px] text-muted-foreground">{count}</span>
    </button>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function TrendsPage() {
  const router = useRouter();
  const { data: feedData, isLoading, mutate } = useTrendsFeed(200);
  const { data: catData } = useTrendsCategories();

  const [search, setSearch] = useState("");
  const [activeCategories, setActiveCategories] = useState<Set<string>>(new Set());
  const [activeAgents, setActiveAgents] = useState<Set<string>>(new Set(ALL_AGENTS));
  const [favorites, setFavorites] = useState<string[]>(loadFavorites);
  const [showCategoryConfig, setShowCategoryConfig] = useState(false);
  const [sortBy, setSortBy] = useState<"score" | "recent">("score");
  const [searchResults, setSearchResults] = useState<TrendFeedItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Sync favorites to localStorage
  useEffect(() => { saveFavorites(favorites); }, [favorites]);

  const categories = catData?.categories ?? [];
  const items = feedData?.items ?? [];
  const agentCounts = feedData?.agent_counts ?? {};
  const categoryCounts = feedData?.category_counts ?? {};

  // Parse search terms (split by space, filter empty)
  const searchTerms = useMemo(() =>
    search.trim() ? search.toLowerCase().trim().split(/\s+/).filter(Boolean) : [],
    [search]
  );

  // Toggle helpers
  const toggleCategory = useCallback((key: string) => {
    setActiveCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleAgent = useCallback((key: string) => {
    setActiveAgents((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleFavorite = useCallback((key: string) => {
    setFavorites((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }, []);

  const handleGenerate = useCallback((title: string) => {
    router.push(`/phrases?topic=${encodeURIComponent(title)}`);
  }, [router]);

  // Search via Gemini API (Enter key)
  const handleSearch = useCallback(async () => {
    const q = search.trim();
    if (!q || q.length < 2) return;
    setIsSearching(true);
    setSearchQuery(q);
    try {
      const res = await searchTrends(q);
      setSearchResults(res.items);
    } catch (e) {
      console.error("Search failed:", e);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [search]);

  // Clear search results when search text is cleared
  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
      setSearchQuery("");
    }
  }, [search]);

  // Filtered items (local filter + API search results merged)
  const filtered = useMemo(() => {
    let result = items;

    // Category filter
    if (activeCategories.size > 0) {
      result = result.filter((t) => activeCategories.has(t.category));
    }

    // Agent filter
    if (activeAgents.size < ALL_AGENTS.length) {
      result = result.filter((t) => activeAgents.has(t._agent));
    }

    // Multi-term search across title + category + source + sentiment
    if (searchTerms.length > 0) {
      result = result.filter((t) => matchesSearch(t, searchTerms));
    }

    // Merge API search results (avoid duplicates by title)
    if (searchResults.length > 0) {
      const existingTitles = new Set(result.map(r => r.title.toLowerCase()));
      const newItems = searchResults.filter(sr => !existingTitles.has(sr.title.toLowerCase()));
      result = [...result, ...newItems];
    }

    // Sort
    if (sortBy === "recent") {
      result = [...result].sort((a, b) => {
        const da = new Date(a.fetched_at).getTime();
        const db = new Date(b.fetched_at).getTime();
        return db - da;
      });
    }

    return result;
  }, [items, activeCategories, activeAgents, searchTerms, sortBy, searchResults]);

  // Favorite categories first in display
  const sortedCategories = useMemo(() => {
    return [...categories].sort((a, b) => {
      const aFav = favorites.includes(a.key) ? 0 : 1;
      const bFav = favorites.includes(b.key) ? 0 : 1;
      if (aFav !== bFav) return aFav - bFav;
      return (categoryCounts[b.key] ?? 0) - (categoryCounts[a.key] ?? 0);
    });
  }, [categories, favorites, categoryCounts]);

  const hasActiveFilters = activeCategories.size > 0 || searchTerms.length > 0 || activeAgents.size < ALL_AGENTS.length;

  return (
    <div className="space-y-4">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Trending Feed
          </h2>
          <p className="text-sm text-muted-foreground">
            {feedData
              ? `${feedData.total} trends de ${Object.keys(agentCounts).length} fontes`
              : "Carregando trends..."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setShowCategoryConfig(!showCategoryConfig)}
            title="Configurar categorias"
          >
            <Settings2 className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => mutate()}
            disabled={isLoading}
            size="sm"
            className={`gap-2 ${isLoading ? "pulse-glow" : ""}`}
          >
            {isLoading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <RefreshCw className="h-3.5 w-3.5" />}
            {isLoading ? "Buscando..." : "Atualizar"}
          </Button>
        </div>
      </div>

      {/* ── Search + Sort ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar trends... (Enter para buscar na web via Gemini)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
            className="pl-9 h-9"
          />
          {(search || isSearching) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              {isSearching ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              ) : (
                <>
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    {filtered.length}
                  </span>
                  <button
                    onClick={() => setSearch("")}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 rounded-lg border bg-secondary/50 p-0.5">
          <button
            onClick={() => setSortBy("score")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              sortBy === "score" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            Top Score
          </button>
          <button
            onClick={() => setSortBy("recent")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              sortBy === "recent" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            Recentes
          </button>
        </div>
      </div>

      {/* ── Category chips ─────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
            Categorias
          </span>
          {activeCategories.size > 0 && (
            <button
              onClick={() => setActiveCategories(new Set())}
              className="text-[10px] text-primary hover:underline ml-1"
            >
              Limpar filtros
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {sortedCategories.map((cat) => (
            <CategoryChip
              key={cat.key}
              category={cat}
              count={categoryCounts[cat.key] ?? 0}
              active={activeCategories.has(cat.key)}
              isFavorite={favorites.includes(cat.key)}
              onToggle={() => toggleCategory(cat.key)}
              onToggleFavorite={() => toggleFavorite(cat.key)}
            />
          ))}
        </div>
      </div>

      {/* ── Category config panel ──────────────────────────────────────────── */}
      {showCategoryConfig && (
        <Card className="animate-fade-in">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">Configurar Categorias Favoritas</h4>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setShowCategoryConfig(false)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Categorias favoritas aparecem primeiro no feed. Clique na estrela para favoritar.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.key}
                  onClick={() => toggleFavorite(cat.key)}
                  className={`
                    flex items-center gap-2 p-2 rounded-lg border text-xs transition-all
                    ${favorites.includes(cat.key)
                      ? "bg-amber-500/10 border-amber-500/30 text-foreground"
                      : "bg-secondary/30 border-border text-muted-foreground hover:text-foreground"
                    }
                  `}
                >
                  {favorites.includes(cat.key)
                    ? <Star className="h-3 w-3 text-amber-400 fill-amber-400 shrink-0" />
                    : <StarOff className="h-3 w-3 shrink-0" />}
                  <span className="truncate">{cat.label}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Source filters ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {ALL_AGENTS.map((key) => (
          <SourcePill
            key={key}
            agentKey={key}
            count={agentCounts[key] ?? 0}
            active={activeAgents.has(key)}
            onToggle={() => toggleAgent(key)}
          />
        ))}
      </div>

      <Separator />

      {/* ── Results summary ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {filtered.length} resultado{filtered.length !== 1 ? "s" : ""}
          {activeCategories.size > 0 && ` em ${activeCategories.size} categoria${activeCategories.size > 1 ? "s" : ""}`}
          {searchTerms.length > 0 && ` para "${searchTerms.join(" ")}"`}
          {searchQuery && searchResults.length > 0 && ` (${searchResults.length} da busca Gemini)`}
          {items.length > 0 && filtered.length < items.length && !searchResults.length && ` (de ${items.length} total)`}
        </p>
        <div className="flex items-center gap-2">
          {searchTerms.length > 0 && !searchQuery && !isSearching && (
            <button
              onClick={handleSearch}
              className="text-[10px] text-primary hover:underline flex items-center gap-1"
            >
              <Search className="h-2.5 w-2.5" />
              Buscar na web
            </button>
          )}
          {hasActiveFilters && (
            <button
              onClick={() => { setActiveCategories(new Set()); setSearch(""); setActiveAgents(new Set(ALL_AGENTS)); }}
              className="text-[10px] text-primary hover:underline"
            >
              Limpar tudo
            </button>
          )}
        </div>
      </div>

      {/* ── Feed grid ──────────────────────────────────────────────────────── */}
      {isLoading && items.length === 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <motion.div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" variants={staggerContainer} initial="initial" animate="animate">
          {filtered.map((item, i) => (
            <TrendCard
              key={`${item.event_id || item.title}-${item._agent}-${i}`}
              item={item}
              index={i}
              onGenerate={handleGenerate}
              searchTerms={searchTerms}
            />
          ))}
        </motion.div>
      ) : items.length > 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Search className="h-8 w-8 text-muted-foreground" />
            <div className="text-center space-y-1">
              <p className="text-muted-foreground">Nenhum trend encontrado no feed local</p>
              {searchTerms.length > 0 && (
                <p className="text-xs text-muted-foreground/70">
                  Pressione <kbd className="px-1 py-0.5 bg-secondary rounded text-[10px] font-mono">Enter</kbd> para buscar &quot;{search}&quot; na web via Gemini
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {searchTerms.length > 0 && (
                <Button size="sm" onClick={handleSearch} disabled={isSearching} className="gap-2">
                  {isSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  {isSearching ? "Buscando..." : "Buscar na web"}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => { setActiveCategories(new Set()); setSearch(""); setActiveAgents(new Set(ALL_AGENTS)); }}>
                Limpar filtros
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="relative">
              <TrendingUp className="h-12 w-12 text-muted-foreground/30" />
              <Flame className="h-5 w-5 text-primary absolute -top-1 -right-1 animate-pulse" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-muted-foreground font-medium">Feed de Trends</p>
              <p className="text-sm text-muted-foreground/70">
                Clique em &quot;Atualizar&quot; para buscar trends de todas as fontes
              </p>
            </div>
            <Button onClick={() => mutate()} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Buscar Trends
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
