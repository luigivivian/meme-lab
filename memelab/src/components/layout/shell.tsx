"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { VideoProgressBar } from "./video-progress";
import { pageVariants, pageTransition } from "@/lib/animations";
import { CharacterProvider } from "@/contexts/character-context";

function TopLoader() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const prevPathname = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathname.current) {
      prevPathname.current = pathname;
      setLoading(true);
      setProgress(30);

      const t1 = setTimeout(() => setProgress(60), 80);
      const t2 = setTimeout(() => setProgress(90), 200);
      const t3 = setTimeout(() => {
        setProgress(100);
        setTimeout(() => {
          setLoading(false);
          setProgress(0);
        }, 300);
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
    <div className="fixed top-0 left-0 right-0 z-50 h-[2px]">
      <div
        className="h-full bg-gradient-to-r from-primary via-primary to-violet-400 transition-all"
        style={{
          width: `${progress}%`,
          transitionDuration: progress === 100 ? "250ms" : "350ms",
          transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
          boxShadow: "0 0 16px rgba(139, 92, 246, 0.6), 0 0 4px rgba(139, 92, 246, 0.4)",
        }}
      />
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleMobileClose = useCallback(() => {
    setMobileOpen(false);
  }, []);

  const handleMenuClick = useCallback(() => {
    setMobileOpen(true);
  }, []);

  return (
    <CharacterProvider>
      <div className="flex h-screen overflow-hidden bg-[var(--color-surface-0)]">
        <TopLoader />
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={handleToggleSidebar}
          mobileOpen={mobileOpen}
          onMobileClose={handleMobileClose}
        />
        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          <Header onMenuClick={handleMenuClick} />
          <AnimatePresence mode="wait">
            <motion.main
              key={pathname}
              className="flex-1 overflow-auto p-4 md:p-6"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={pageTransition}
            >
              {children}
            </motion.main>
          </AnimatePresence>
        </div>
        <VideoProgressBar />
      </div>
    </CharacterProvider>
  );
}
