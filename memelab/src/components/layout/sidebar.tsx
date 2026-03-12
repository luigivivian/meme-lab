"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion, LayoutGroup, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useCharacterContext } from "@/contexts/character-context";

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  draft: { label: "Rascunho", color: "bg-amber-500/20 text-amber-400" },
  refining: { label: "Refinando", color: "bg-blue-500/20 text-blue-400" },
  ready: { label: "Pronto", color: "bg-emerald-500/20 text-emerald-400" },
};

function CharacterSelector() {
  const [open, setOpen] = useState(false);
  const { characters, activeCharacter, setActiveSlug } = useCharacterContext();

  if (!activeCharacter) return null;

  const badge = STATUS_BADGE[activeCharacter.status] ?? STATUS_BADGE.draft;

  return (
    <div className="relative px-3 pb-2">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left",
          "border border-border/50 transition-all duration-200",
          "hover:bg-secondary/50",
          open && "bg-secondary/50 border-primary/30"
        )}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary text-sm font-bold">
          {activeCharacter.name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{activeCharacter.name}</p>
          <p className="text-xs text-muted-foreground truncate">{activeCharacter.handle}</p>
        </div>
        <ChevronDown className={cn(
          "h-4 w-4 text-muted-foreground transition-transform duration-200",
          open && "rotate-180"
        )} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute left-3 right-3 top-full z-50 mt-1 rounded-xl border bg-card shadow-lg overflow-hidden"
          >
            <div className="p-1 max-h-64 overflow-y-auto">
              {characters.map((char) => {
                const isActive = char.slug === activeCharacter.slug;
                const charBadge = STATUS_BADGE[char.status] ?? STATUS_BADGE.draft;
                return (
                  <button
                    key={char.slug}
                    onClick={() => {
                      setActiveSlug(char.slug);
                      setOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left",
                      "transition-colors duration-150",
                      isActive ? "bg-primary/10" : "hover:bg-secondary"
                    )}
                  >
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/20 text-primary text-xs font-bold">
                      {char.name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{char.name}</p>
                      <div className="flex items-center gap-1.5">
                        <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full", charBadge.color)}>
                          {charBadge.label}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {char.refs.approved} refs
                        </span>
                      </div>
                    </div>
                    {isActive && <Check className="h-4 w-4 text-primary" />}
                  </button>
                );
              })}
            </div>
            <div className="border-t p-1">
              <Link
                href="/characters"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                Gerenciar personagens
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <span className="text-xl font-bold tracking-tight">
          meme<span className="text-primary">Lab</span>
        </span>
      </div>

      {/* Character Selector */}
      <CharacterSelector />

      {/* Nav */}
      <LayoutGroup>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
                  "transition-all duration-200 ease-out",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                {active && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-primary"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                <item.icon className={cn(
                  "h-5 w-5 transition-transform duration-200",
                  active ? "scale-110" : "group-hover:scale-105"
                )} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </LayoutGroup>

      {/* Footer */}
      <div className="border-t px-6 py-4">
        <p className="text-xs text-muted-foreground">clip-flow pipeline</p>
      </div>
    </aside>
  );
}
