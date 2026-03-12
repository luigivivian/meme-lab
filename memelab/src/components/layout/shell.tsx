"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
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
        }, 250);
      }, 350);

      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);
      };
    }
  }, [pathname]);

  if (!loading && progress === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-[3px]">
      <div
        className="h-full bg-primary transition-all ease-out"
        style={{
          width: `${progress}%`,
          transitionDuration: progress === 100 ? "200ms" : "300ms",
          boxShadow: "0 0 10px rgba(124, 58, 237, 0.5), 0 0 5px rgba(124, 58, 237, 0.3)",
        }}
      />
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <CharacterProvider>
      <div className="flex h-screen overflow-hidden">
        <TopLoader />
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <AnimatePresence mode="wait">
            <motion.main
              key={pathname}
              className="flex-1 overflow-auto p-6"
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
      </div>
    </CharacterProvider>
  );
}
