"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

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

function PageContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [displayed, setDisplayed] = useState(children);
  const [animating, setAnimating] = useState(false);
  const prevPathname = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathname.current) {
      prevPathname.current = pathname;
      setAnimating(true);
      const t = setTimeout(() => {
        setDisplayed(children);
        setAnimating(false);
      }, 150);
      return () => clearTimeout(t);
    } else {
      setDisplayed(children);
    }
  }, [pathname, children]);

  return (
    <main
      className="flex-1 overflow-auto p-6"
      style={{
        opacity: animating ? 0 : 1,
        transform: animating ? "translateY(6px)" : "translateY(0)",
        transition: "opacity 0.2s ease-out, transform 0.2s ease-out",
      }}
    >
      {displayed}
    </main>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <TopLoader />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <PageContent>{children}</PageContent>
      </div>
    </div>
  );
}
