"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";

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

      {/* Nav */}
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
                <div className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-primary animate-fade-in" />
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

      {/* Footer */}
      <div className="border-t px-6 py-4">
        <p className="text-xs text-muted-foreground">@magomestre420</p>
        <p className="text-xs text-muted-foreground/60">clip-flow pipeline</p>
      </div>
    </aside>
  );
}
