"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion, LayoutGroup, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown, Check, ChevronsLeft, ChevronsRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useCharacterContext } from "@/contexts/character-context";

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  draft: { label: "Rascunho", color: "bg-amber-500/15 text-amber-400" },
  refining: { label: "Refinando", color: "bg-sky-500/15 text-sky-400" },
  ready: { label: "Pronto", color: "bg-emerald-500/15 text-emerald-400" },
};

function CharacterSelector({ collapsed }: { collapsed: boolean }) {
  const [open, setOpen] = useState(false);
  const { characters, activeCharacter, setActiveSlug } = useCharacterContext();

  if (!activeCharacter) return null;

  if (collapsed) {
    return (
      <div className="px-2 pb-2">
        <button
          onClick={() => setOpen(!open)}
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl mx-auto",
            "bg-primary/10 text-primary text-sm font-bold",
            "transition-all duration-200 hover:bg-primary/15 cursor-pointer"
          )}
          title={activeCharacter.name}
        >
          {activeCharacter.name.charAt(0)}
        </button>
      </div>
    );
  }

  const badge = STATUS_BADGE[activeCharacter.status] ?? STATUS_BADGE.draft;

  return (
    <div className="relative px-3 pb-2">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left",
          "border border-white/[0.04] transition-all duration-200",
          "hover:bg-white/[0.03] cursor-pointer",
          open && "bg-white/[0.03] border-primary/20"
        )}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary text-sm font-bold">
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
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="absolute left-3 right-3 top-full z-50 mt-1 rounded-xl border border-white/[0.06] bg-[var(--color-surface-2)] shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden"
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
                      "transition-colors duration-150 cursor-pointer",
                      isActive ? "bg-primary/8" : "hover:bg-white/[0.04]"
                    )}
                  >
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary text-xs font-bold">
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
            <div className="border-t border-white/[0.04] p-1">
              <Link
                href="/characters"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-white/[0.04] hover:text-foreground transition-colors"
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

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();

  const sidebarContent = (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-white/[0.04] bg-[var(--color-surface-1)] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
        collapsed ? "w-[72px]" : "w-64"
      )}
    >
      {/* Logo */}
      <div className={cn(
        "flex items-center gap-3 py-5 transition-all duration-300",
        collapsed ? "justify-center px-3" : "px-6"
      )}>
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary shadow-[0_0_16px_rgba(139,92,246,0.25)]">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            className="text-xl font-bold tracking-tight whitespace-nowrap overflow-hidden"
          >
            meme<span className="text-gradient">Lab</span>
          </motion.span>
        )}
      </div>

      {/* Character Selector */}
      <CharacterSelector collapsed={collapsed} />

      {/* Nav */}
      <LayoutGroup>
        <nav className={cn(
          "flex-1 space-y-0.5 py-4 overflow-y-auto overflow-x-hidden",
          collapsed ? "px-2" : "px-3"
        )}>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onMobileClose}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "group relative flex items-center rounded-xl text-sm font-medium",
                  "transition-all duration-200 ease-out",
                  collapsed ? "justify-center h-10 w-10 mx-auto" : "gap-3 px-3 py-2.5",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground"
                )}
              >
                {active && (
                  <motion.div
                    layoutId="sidebar-active"
                    className={cn(
                      "absolute inset-0 rounded-xl bg-primary/[0.08]",
                      "border border-primary/10"
                    )}
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                {active && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-primary shadow-[0_0_8px_rgba(139,92,246,0.5)]"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                <item.icon className={cn(
                  "relative h-5 w-5 shrink-0 transition-all duration-200",
                  active ? "text-primary" : "group-hover:text-foreground"
                )} />
                {!collapsed && <span className="relative">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </LayoutGroup>

      {/* Collapse toggle + Footer */}
      <div className={cn(
        "border-t border-white/[0.04] py-3",
        collapsed ? "px-2" : "px-3"
      )}>
        <button
          onClick={onToggle}
          className={cn(
            "flex items-center gap-2 rounded-xl px-3 py-2 text-sm",
            "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground",
            "transition-all duration-200 cursor-pointer w-full",
            collapsed && "justify-center"
          )}
          title={collapsed ? "Expandir sidebar" : "Recolher sidebar"}
        >
          {collapsed ? (
            <ChevronsRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronsLeft className="h-4 w-4" />
              <span>Recolher</span>
            </>
          )}
        </button>
        {!collapsed && (
          <p className="text-[10px] text-muted-foreground/50 px-3 mt-2 tracking-wider uppercase">clip-flow pipeline</p>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        {sidebarContent}
      </div>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden"
              onClick={onMobileClose}
            />
            <motion.div
              initial={{ x: -280, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -280, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 z-50 md:hidden"
            >
              <aside className="flex h-screen w-64 flex-col border-r border-white/[0.04] bg-[var(--color-surface-1)]">
                {/* Logo */}
                <div className="flex items-center gap-3 px-6 py-5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-[0_0_16px_rgba(139,92,246,0.25)]">
                    <Sparkles className="h-5 w-5 text-white" />
                  </div>
                  <span className="text-xl font-bold tracking-tight">
                    meme<span className="text-gradient">Lab</span>
                  </span>
                </div>

                <CharacterSelector collapsed={false} />

                <LayoutGroup>
                  <nav className="flex-1 space-y-0.5 px-3 py-4 overflow-y-auto">
                    {NAV_ITEMS.map((item) => {
                      const active = pathname === item.href || pathname.startsWith(item.href + "/");
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={onMobileClose}
                          className={cn(
                            "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
                            "transition-all duration-200 ease-out",
                            active
                              ? "bg-primary/[0.08] text-foreground"
                              : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground"
                          )}
                        >
                          <item.icon className={cn("h-5 w-5", active && "text-primary")} />
                          {item.label}
                        </Link>
                      );
                    })}
                  </nav>
                </LayoutGroup>

                <div className="border-t border-white/[0.04] px-6 py-4">
                  <p className="text-[10px] text-muted-foreground/50 tracking-wider uppercase">clip-flow pipeline</p>
                </div>
              </aside>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
