import { Card, CardContent } from "@/components/ui/card";
import { type LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  description?: string;
  trend?: { value: number; label: string };
  className?: string;
  iconClassName?: string;
}

export function StatsCard({ title, value, icon: Icon, description, trend, className, iconClassName }: StatsCardProps) {
  return (
    <Card className={cn(
      "group relative overflow-hidden",
      "hover:shadow-[0_8px_32px_rgba(139,92,246,0.08)]",
      className
    )}>
      {/* Subtle gradient glow on hover */}
      <div className="absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500 group-hover:opacity-100 pointer-events-none bg-gradient-to-br from-primary/[0.03] via-transparent to-transparent" />

      <CardContent className="relative p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest">{title}</p>
            <p className="text-3xl font-bold tabular-nums tracking-tight">{value}</p>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
            {trend && (
              <div className="flex items-center gap-1.5">
                {trend.value > 0 ? (
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                ) : trend.value < 0 ? (
                  <TrendingDown className="h-3.5 w-3.5 text-rose-400" />
                ) : (
                  <Minus className="h-3.5 w-3.5 text-muted-foreground" />
                )}
                <span className={cn(
                  "text-[11px] font-semibold px-1.5 py-0.5 rounded-md",
                  trend.value > 0
                    ? "text-emerald-400 bg-emerald-500/10"
                    : trend.value < 0
                      ? "text-rose-400 bg-rose-500/10"
                      : "text-muted-foreground bg-muted/50"
                )}>
                  {trend.value > 0 ? "+" : ""}{trend.value}%
                </span>
                <span className="text-[10px] text-muted-foreground">{trend.label}</span>
              </div>
            )}
          </div>
          <div className={cn(
            "flex h-11 w-11 items-center justify-center rounded-xl",
            "bg-primary/[0.08] transition-all duration-300",
            "group-hover:bg-primary/[0.15] group-hover:shadow-[0_0_20px_rgba(139,92,246,0.15)]",
            iconClassName
          )}>
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
