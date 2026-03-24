import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-[var(--radius)]",
        className
      )}
      {...props}
    />
  );
}

function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-[var(--radius)] border border-white/[0.04] bg-[var(--color-surface-1)] p-5 space-y-3", className)}>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-7 w-16" />
        </div>
        <Skeleton className="h-11 w-11 rounded-xl" />
      </div>
    </div>
  );
}

function SkeletonList({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-9 w-full"
          style={{ animationDelay: `${i * 100}ms` }}
        />
      ))}
    </div>
  );
}

export { Skeleton, SkeletonCard, SkeletonList };
