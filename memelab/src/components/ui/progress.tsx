"use client";

import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

const Progress = React.forwardRef<
  React.ComponentRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
    indicatorClassName?: string;
  }
>(({ className, value, indicatorClassName, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      "relative h-2 w-full overflow-hidden rounded-full bg-white/[0.04]",
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className={cn(
        "h-full rounded-full bg-primary transition-all duration-500 ease-out",
        "shadow-[0_0_8px_rgba(139,92,246,0.3)]",
        indicatorClassName
      )}
      style={{ width: `${value ?? 0}%` }}
    />
  </ProgressPrimitive.Root>
));
Progress.displayName = ProgressPrimitive.Root.displayName;

function IndeterminateProgress({ className }: { className?: string }) {
  return (
    <div className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-white/[0.04]", className)}>
      <div className="animate-indeterminate absolute h-full w-1/3 rounded-full bg-gradient-to-r from-primary/50 via-primary to-primary/50 shadow-[0_0_12px_rgba(139,92,246,0.4)]" />
    </div>
  );
}

export { Progress, IndeterminateProgress };
