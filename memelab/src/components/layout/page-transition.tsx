"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";

export function TopLoader() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const prevPathname = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathname.current) {
      prevPathname.current = pathname;
      setLoading(true);
      setProgress(30);

      const t1 = setTimeout(() => setProgress(60), 100);
      const t2 = setTimeout(() => setProgress(90), 200);
      const t3 = setTimeout(() => {
        setProgress(100);
        setTimeout(() => {
          setLoading(false);
          setProgress(0);
        }, 200);
      }, 400);

      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);
      };
    }
  }, [pathname]);

  if (!loading && progress === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-0.5">
      <div
        className="h-full bg-primary shadow-[0_0_10px_var(--color-primary)] transition-all duration-300 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

export function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 ease-out">
      {children}
    </div>
  );
}
