"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Sparkles, Bot, Workflow, Image, TrendingUp, Zap,
  Play, ArrowRight, ChevronRight, Layers, Send,
  Clock, Shield, BarChart3, Globe, Cpu, Palette,
  CheckCircle2, Star, Menu, X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Animated counter ────────────────────────────────────────────
function AnimatedNumber({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const duration = 1500;
          const start = Date.now();
          const animate = () => {
            const elapsed = Date.now() - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setValue(Math.round(target * eased));
            if (progress < 1) requestAnimationFrame(animate);
          };
          animate();
        }
      },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);

  return <span ref={ref} className="tabular-nums">{value}{suffix}</span>;
}

// ── Feature card for bento grid ─────────────────────────────────
function FeatureCard({
  icon: Icon,
  title,
  description,
  accent,
  className,
}: {
  icon: typeof Sparkles;
  title: string;
  description: string;
  accent: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "group relative rounded-2xl border border-white/5 bg-[#0f0f14] p-6",
        "transition-all duration-300 hover:border-white/10 hover:bg-[#131318]",
        "overflow-hidden",
        className
      )}
    >
      {/* Hover glow */}
      <div
        className={cn(
          "absolute -top-20 -right-20 h-40 w-40 rounded-full blur-3xl",
          "opacity-0 group-hover:opacity-20 transition-opacity duration-500",
          accent
        )}
      />
      <div className="relative space-y-3">
        <div className={cn(
          "flex h-10 w-10 items-center justify-center rounded-xl",
          "transition-transform duration-300 group-hover:scale-110",
          accent.replace("bg-", "bg-").replace("/40", "/15")
        )}>
          <Icon className="h-5 w-5" style={{ color: accent.includes("violet") ? "#8b5cf6" : accent.includes("blue") ? "#3b82f6" : accent.includes("emerald") ? "#10b981" : accent.includes("amber") ? "#f59e0b" : accent.includes("rose") ? "#f43f5e" : accent.includes("cyan") ? "#06b6d4" : "#7c3aed" }} />
        </div>
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

// ── Step card for "how it works" ────────────────────────────────
function StepCard({
  step,
  title,
  description,
  icon: Icon,
}: {
  step: number;
  title: string;
  description: string;
  icon: typeof Sparkles;
}) {
  return (
    <div className="relative flex flex-col items-center text-center space-y-4 p-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20">
        <Icon className="h-6 w-6 text-primary" />
      </div>
      <div className="absolute -top-2 -right-2 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
        {step}
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">{description}</p>
    </div>
  );
}

// ── Stat item ───────────────────────────────────────────────────
function StatItem({ value, suffix, label }: { value: number; suffix?: string; label: string }) {
  return (
    <div className="text-center space-y-1">
      <p className="text-4xl font-bold text-primary">
        <AnimatedNumber target={value} suffix={suffix} />
      </p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

// ── Navbar ──────────────────────────────────────────────────────
function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-background/80 backdrop-blur-xl border-b border-white/5 shadow-lg shadow-black/20"
          : "bg-transparent"
      )}
    >
      <div className="mx-auto max-w-6xl flex items-center justify-between px-6 h-16">
        <Link href="/landing" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold">
            meme<span className="text-primary">Lab</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Features
          </a>
          <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Como Funciona
          </a>
          <a href="#stats" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Resultados
          </a>
          <a href="#pipeline" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Pipeline
          </a>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/25"
          >
            Abrir Dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden flex h-9 w-9 items-center justify-center rounded-lg hover:bg-secondary transition-colors cursor-pointer"
          aria-label="Menu"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/5 bg-background/95 backdrop-blur-xl">
          <div className="flex flex-col px-6 py-4 space-y-3">
            <a href="#features" onClick={() => setMobileOpen(false)} className="text-sm py-2">Features</a>
            <a href="#how-it-works" onClick={() => setMobileOpen(false)} className="text-sm py-2">Como Funciona</a>
            <a href="#stats" onClick={() => setMobileOpen(false)} className="text-sm py-2">Resultados</a>
            <a href="#pipeline" onClick={() => setMobileOpen(false)} className="text-sm py-2">Pipeline</a>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white"
            >
              Abrir Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

// ── Main Landing Page ───────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      <LandingNav />

      {/* ══════════════════════════════════════════════════════════
          HERO
         ══════════════════════════════════════════════════════════ */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-28">
        {/* Background effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-primary/10 rounded-full blur-[120px]" />
          <div className="absolute top-40 left-1/4 w-[400px] h-[400px] bg-violet-500/5 rounded-full blur-[100px]" />
          <div className="absolute top-60 right-1/4 w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[80px]" />
        </div>

        <div className="relative mx-auto max-w-6xl px-6 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 mb-8">
            <Zap className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-medium text-primary">Pipeline Multi-Agente Automatizado</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            Memes virais no{" "}
            <span className="relative">
              <span className="bg-gradient-to-r from-primary via-violet-400 to-blue-400 bg-clip-text text-transparent">
                piloto automatico
              </span>
              <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none">
                <path d="M2 10C50 2 250 2 298 10" stroke="url(#grad)" strokeWidth="3" strokeLinecap="round" />
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="300" y2="0">
                    <stop offset="0%" stopColor="#7C3AED" />
                    <stop offset="100%" stopColor="#3B82F6" />
                  </linearGradient>
                </defs>
              </svg>
            </span>
          </h1>

          <p className="mx-auto max-w-2xl text-lg md:text-xl text-muted-foreground leading-relaxed mb-10">
            De trending topic a post pronto em minutos. 9 agentes de IA coletam trends,
            geram frases virais, criam backgrounds cinematicos e compoem imagens 1080x1350
            prontas para Instagram.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-white transition-all duration-200 hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/25 hover:-translate-y-0.5"
            >
              <Play className="h-5 w-5" />
              Comecar Agora
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-8 py-3.5 text-base font-medium transition-all duration-200 hover:bg-secondary hover:border-white/20"
            >
              Como Funciona
              <ChevronRight className="h-4 w-4" />
            </a>
          </div>

          {/* Hero mockup */}
          <div className="relative mt-16 mx-auto max-w-4xl">
            <div className="rounded-2xl border border-white/10 bg-card/50 backdrop-blur-sm p-1 shadow-2xl shadow-primary/5">
              <div className="rounded-xl bg-[#0f0f14] overflow-hidden">
                {/* Fake browser bar */}
                <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
                  <div className="flex gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-red-500/60" />
                    <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
                    <div className="h-3 w-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="flex items-center gap-2 rounded-lg bg-secondary/50 px-3 py-1 text-[11px] text-muted-foreground">
                      <Shield className="h-3 w-3" />
                      localhost:3000/dashboard
                    </div>
                  </div>
                </div>
                {/* Dashboard preview */}
                <div className="p-4 space-y-4">
                  {/* Stats row */}
                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { label: "Imagens", value: "247", color: "text-primary" },
                      { label: "Agentes", value: "9/14", color: "text-emerald-400" },
                      { label: "Runs", value: "52", color: "text-blue-400" },
                      { label: "Backgrounds", value: "183", color: "text-amber-400" },
                    ].map((stat) => (
                      <div key={stat.label} className="rounded-xl border border-white/5 bg-secondary/30 p-3">
                        <p className="text-[10px] text-muted-foreground">{stat.label}</p>
                        <p className={cn("text-xl font-bold", stat.color)}>{stat.value}</p>
                      </div>
                    ))}
                  </div>
                  {/* Content grid preview */}
                  <div className="grid grid-cols-3 gap-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="rounded-xl bg-secondary/30 aspect-[4/5] border border-white/5 flex items-end p-2">
                        <div className="space-y-1 w-full">
                          <div className="h-2 w-3/4 rounded bg-white/10" />
                          <div className="h-1.5 w-1/2 rounded bg-white/5" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Floating badges */}
            <div className="absolute -left-4 top-1/4 hidden lg:flex items-center gap-2 rounded-xl border border-white/10 bg-card px-3 py-2 shadow-xl animate-float-slow">
              <Bot className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-medium">9 Agentes Ativos</span>
            </div>
            <div className="absolute -right-4 top-1/3 hidden lg:flex items-center gap-2 rounded-xl border border-white/10 bg-card px-3 py-2 shadow-xl animate-float-slow-delay">
              <TrendingUp className="h-4 w-4 text-blue-400" />
              <span className="text-xs font-medium">227+ Trends/run</span>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          STATS BAR
         ══════════════════════════════════════════════════════════ */}
      <section id="stats" className="border-y border-white/5 bg-[#0a0a0f] py-16">
        <div className="mx-auto max-w-4xl px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          <StatItem value={9} label="Agentes de IA" />
          <StatItem value={227} suffix="+" label="Trends por run" />
          <StatItem value={5} label="Camadas pipeline" />
          <StatItem value={13} suffix="+" label="Temas visuais" />
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          FEATURES — Bento Grid
         ══════════════════════════════════════════════════════════ */}
      <section id="features" className="py-20 md:py-28">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-primary uppercase tracking-wider mb-3">Features</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
              Tudo que voce precisa para escalar memes
            </h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              Pipeline completo de trending topic a post publicado. Cada camada otimizada para qualidade e velocidade.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Globe}
              title="9 Fontes de Trends"
              description="Google Trends, Reddit, YouTube, BlueSky, HackerNews, Lemmy, Gemini Web Search e mais. Cobertura total do que esta viralizando no Brasil."
              accent="bg-blue-500/40"
            />
            <FeatureCard
              icon={Bot}
              title="Curadoria por IA"
              description="Gemini analisa e seleciona os melhores temas, mapeia situacoes visuais e gera WorkOrders otimizados para engagement."
              accent="bg-violet-500/40"
            />
            <FeatureCard
              icon={Sparkles}
              title="Frases Virais"
              description="Gerador de frases estilo 'tio sabio zoeiro'. Tom leve, relatable e viral. A/B testing com scoring automatico."
              accent="bg-amber-500/40"
            />
            <FeatureCard
              icon={Image}
              title="Backgrounds Cinematicos"
              description="Gemini Image API com refs visuais do personagem. 13+ situacoes tematicas. Fallback inteligente para ComfyUI e estaticos."
              accent="bg-emerald-500/40"
            />
            <FeatureCard
              icon={Layers}
              title="Composicao Pillow"
              description="Overlay, vinheta, glow, texto com stroke, watermark. Formato 1080x1350 otimizado para feed do Instagram."
              accent="bg-rose-500/40"
            />
            <FeatureCard
              icon={Send}
              title="Auto-Publicacao"
              description="Agenda posts, escolhe melhores horarios, publica no Instagram automaticamente. Calendario visual e fila gerenciavel."
              accent="bg-cyan-500/40"
            />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          HOW IT WORKS
         ══════════════════════════════════════════════════════════ */}
      <section id="how-it-works" className="py-20 md:py-28 bg-[#0a0a0f] border-y border-white/5">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-primary uppercase tracking-wider mb-3">Como Funciona</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
              5 camadas, totalmente automatico
            </h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              De trend viral a post pronto em minutos. Cada camada processa em paralelo para maxima velocidade.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
            <StepCard
              step={1}
              icon={TrendingUp}
              title="Monitoring"
              description="9 agentes coletam trends em paralelo de multiplas fontes"
            />
            <StepCard
              step={2}
              icon={BarChart3}
              title="Broker"
              description="Deduplicacao, ranking por score e filtragem inteligente"
            />
            <StepCard
              step={3}
              icon={Cpu}
              title="Curator"
              description="Gemini seleciona temas e mapeia situacoes visuais"
            />
            <StepCard
              step={4}
              icon={Palette}
              title="Generation"
              description="Frases + backgrounds gerados em paralelo por WorkOrder"
            />
            <StepCard
              step={5}
              icon={CheckCircle2}
              title="Post-Prod"
              description="Caption, hashtags, quality score e composicao final"
            />
          </div>

          {/* Connection line */}
          <div className="hidden lg:block relative mt-[-140px] mb-8">
            <div className="absolute top-1/2 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          PIPELINE DETAIL
         ══════════════════════════════════════════════════════════ */}
      <section id="pipeline" className="py-20 md:py-28">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 items-center">
            <div>
              <p className="text-sm font-medium text-primary uppercase tracking-wider mb-3">Pipeline</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
                Multi-agente com degradacao graciosa
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-8">
                O pipeline nunca para. Quando a Gemini Image API atinge o limite, o sistema
                degrada graciosamente para ComfyUI local ou backgrounds estaticos.
                Conteudo sempre sai no prazo.
              </p>

              <div className="space-y-4">
                {[
                  { icon: Zap, text: "Semaphore GPU(1) + Gemini(5) para controle de concorrencia" },
                  { icon: Shield, text: "Fallback automatico: Gemini > ComfyUI > Estaticos" },
                  { icon: Clock, text: "Timeout por agent (30s), generation (300s), API (60s)" },
                  { icon: Star, text: "A/B testing de frases com scoring Gemini" },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                      <item.icon className="h-4 w-4 text-primary" />
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed pt-1.5">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Pipeline diagram mockup */}
            <div className="rounded-2xl border border-white/5 bg-[#0f0f14] p-6 space-y-4">
              {[
                { layer: "L1", name: "Monitoring", agents: "9 agents", color: "bg-blue-500", pct: 100 },
                { layer: "L2", name: "Broker", agents: "Dedup + Rank", color: "bg-violet-500", pct: 85 },
                { layer: "L3", name: "Curator", agents: "Gemini Analyzer", color: "bg-amber-500", pct: 70 },
                { layer: "L4", name: "Generation", agents: "Phrase + Image", color: "bg-emerald-500", pct: 90 },
                { layer: "L5", name: "Post-Prod", agents: "Caption + QA", color: "bg-rose-500", pct: 95 },
              ].map((layer) => (
                <div key={layer.layer} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={cn("flex h-7 w-7 items-center justify-center rounded-lg text-[10px] font-bold text-white", layer.color)}>
                        {layer.layer}
                      </span>
                      <div>
                        <p className="text-sm font-medium">{layer.name}</p>
                        <p className="text-[10px] text-muted-foreground">{layer.agents}</p>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground tabular-nums">{layer.pct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all duration-1000", layer.color)}
                      style={{ width: `${layer.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          CTA FINAL
         ══════════════════════════════════════════════════════════ */}
      <section className="py-20 md:py-28 border-t border-white/5">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 mb-8">
            <Workflow className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-medium text-primary">Open Source</span>
          </div>

          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
            Pronto para automatizar seus memes?
          </h2>
          <p className="text-lg text-muted-foreground mb-10 max-w-xl mx-auto">
            Configure em minutos. Basta uma API key do Google Gemini
            e o pipeline esta pronto para gerar conteudo viral.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-white transition-all duration-200 hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/25 hover:-translate-y-0.5"
            >
              <Play className="h-5 w-5" />
              Abrir Dashboard
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-8 py-3.5 text-base font-medium transition-all duration-200 hover:bg-secondary hover:border-white/20"
            >
              Ver no GitHub
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          FOOTER
         ══════════════════════════════════════════════════════════ */}
      <footer className="border-t border-white/5 py-8">
        <div className="mx-auto max-w-6xl px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <Sparkles className="h-3 w-3 text-white" />
            </div>
            <span className="text-sm font-semibold">
              meme<span className="text-primary">Lab</span>
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            clip-flow pipeline — Automacao de memes com IA
          </p>
        </div>
      </footer>
    </div>
  );
}
