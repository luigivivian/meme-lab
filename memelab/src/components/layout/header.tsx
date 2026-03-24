"use client";

import { usePathname } from "next/navigation";
import { Menu, Activity, ChevronRight } from "lucide-react";
import { NAV_ITEMS } from "@/lib/constants";
import { Badge } from "@/components/ui/badge";
import { useStatus } from "@/hooks/use-api";

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname();
  const { data: status, isLoading } = useStatus();

  const current = NAV_ITEMS.find(
    (item) => pathname === item.href || pathname.startsWith(item.href + "/")
  );
  const title = current?.label ?? "memeLab";
  const Icon = current?.icon;

  const isOnline = !!status?.api_key_ok;

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/[0.04] bg-[var(--color-surface-0)]/80 backdrop-blur-xl px-4 md:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-white/[0.04] transition-colors duration-200 md:hidden cursor-pointer"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5 text-muted-foreground" />
        </button>

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground/60 hidden sm:inline">memeLab</span>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/30 hidden sm:block" />
          <div className="flex items-center gap-2">
            {Icon && <Icon className="h-4 w-4 text-primary/80" />}
            <h1 className="font-semibold">{title}</h1>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {status && (
          <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
            <span className="tabular-nums">{status.total_images_generated} imgs</span>
            <span className="h-3 w-px bg-white/[0.06]" />
            <span className="tabular-nums">{status.refs_loaded} refs</span>
          </div>
        )}
        <Badge
          variant={isLoading ? "secondary" : isOnline ? "success" : "destructive"}
          className="gap-1.5 text-[11px]"
        >
          <span className="relative flex h-2 w-2">
            {isOnline && !isLoading && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
            )}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${isLoading ? "bg-muted-foreground" : isOnline ? "bg-emerald-400" : "bg-rose-400"}`} />
          </span>
          <span className="hidden sm:inline">
            {isLoading ? "Conectando..." : isOnline ? "API Online" : "API Offline"}
          </span>
          <span className="sm:hidden">
            {isLoading ? "..." : isOnline ? "ON" : "OFF"}
          </span>
        </Badge>
      </div>
    </header>
  );
}
