"use client";

import { usePathname } from "next/navigation";
import { Activity } from "lucide-react";
import { NAV_ITEMS } from "@/lib/constants";
import { Badge } from "@/components/ui/badge";
import { useStatus } from "@/hooks/use-api";

export function Header() {
  const pathname = usePathname();
  const { data: status, isLoading } = useStatus();

  const current = NAV_ITEMS.find(
    (item) => pathname === item.href || pathname.startsWith(item.href + "/")
  );
  const title = current?.label ?? "memeLab";

  const isOnline = !!status?.api_key_ok;

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <h1 className="text-lg font-semibold">{title}</h1>
      <div className="flex items-center gap-3">
        {status && (
          <span className="text-xs text-muted-foreground">
            {status.total_images_generated} imgs | {status.refs_loaded} refs
          </span>
        )}
        <Badge
          variant={isLoading ? "secondary" : isOnline ? "success" : "destructive"}
          className="gap-1.5"
        >
          <Activity className="h-3 w-3" />
          {isLoading ? "Conectando..." : isOnline ? "API Online" : "API Offline"}
        </Badge>
      </div>
    </header>
  );
}
