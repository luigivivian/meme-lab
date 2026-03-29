"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  Sparkles,
  Package,
  Target,
  Palette,
  Volume2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { createAdJob, type AdCreateRequest } from "@/lib/api";

// ── Section wrapper ───────────────────────────────────────────────

function Section({
  title,
  icon: Icon,
  step,
  open,
  onToggle,
  filled,
  children,
}: {
  title: string;
  icon: typeof Package;
  step: number;
  open: boolean;
  onToggle: () => void;
  filled: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <button
        type="button"
        className="w-full flex items-center gap-3 p-4 text-left"
        onClick={onToggle}
      >
        <span className="flex items-center justify-center h-7 w-7 rounded-full bg-purple-500/20 text-purple-400 text-xs font-bold">
          {step}
        </span>
        <Icon className="h-5 w-5 text-purple-400" />
        <span className="font-medium flex-1">{title}</span>
        {filled && !open && (
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-xs">
            Preenchido
          </Badge>
        )}
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && <CardContent className="pt-0 space-y-4">{children}</CardContent>}
    </Card>
  );
}

// ── Style descriptions ────────────────────────────────────────────

const STYLES = [
  {
    value: "cinematic" as const,
    label: "Cinematico",
    desc: "Camera em movimento, iluminacao dramatica, sem narrador",
  },
  {
    value: "narrated" as const,
    label: "Narrado",
    desc: "Narracao em voz over com imagens do produto",
  },
  {
    value: "lifestyle" as const,
    label: "Lifestyle",
    desc: "Pessoa usando o produto em cenario real",
  },
];

const NICHES = [
  { value: "moda", label: "Moda" },
  { value: "tech", label: "Tecnologia" },
  { value: "food", label: "Alimentacao" },
  { value: "beauty", label: "Beleza" },
  { value: "fitness", label: "Fitness" },
  { value: "outros", label: "Outros" },
];

const TONES = [
  { value: "premium", label: "Premium" },
  { value: "energetico", label: "Energetico" },
  { value: "divertido", label: "Divertido" },
  { value: "minimalista", label: "Minimalista" },
  { value: "profissional", label: "Profissional" },
  { value: "natural", label: "Natural" },
];

const AUDIO_MODES = [
  { value: "mute", label: "Mudo" },
  { value: "music", label: "So trilha" },
  { value: "narrated", label: "TTS + trilha" },
  { value: "ambient", label: "Ambiente + trilha" },
];

// ── AdWizard ──────────────────────────────────────────────────────

export function AdWizard() {
  const router = useRouter();

  // Section visibility
  const [openSection, setOpenSection] = useState(1);

  // Section 1: Produto
  const [productName, setProductName] = useState("");

  // Section 2: Contexto
  const [niche, setNiche] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  // Section 3: Estilo
  const [style, setStyle] = useState<"cinematic" | "narrated" | "lifestyle">("cinematic");
  const [sceneDescription, setSceneDescription] = useState("");
  const [withHuman, setWithHuman] = useState(false);
  const [duration, setDuration] = useState("15");

  // Section 4: Audio & Formato
  const [audioMode, setAudioMode] = useState<"mute" | "music" | "narrated" | "ambient">("music");
  const [formats, setFormats] = useState<string[]>(["9:16"]);
  const [videoModel, setVideoModel] = useState("kling-v2");

  // Submit state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleSection(n: number) {
    setOpenSection(openSection === n ? 0 : n);
  }

  function toggleFormat(fmt: string) {
    setFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  }

  async function handleAnalyze() {
    if (!productName.trim()) return;
    setAnalyzing(true);
    try {
      const res = await fetch("/api/ads/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_name: productName }),
      });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      if (result.niche && !niche) setNiche(result.niche);
      if (result.tone && !tone) setTone(result.tone);
      if (result.audience && !audience) setAudience(result.audience);
      if (result.scene_suggestions?.length && !sceneDescription) {
        setSceneDescription(result.scene_suggestions[0]);
      }
    } catch {
      // silently fail — user can fill manually
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSubmit() {
    if (!productName.trim() || formats.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const req: AdCreateRequest = {
        product_name: productName.trim(),
        style,
        audio_mode: audioMode,
        output_formats: formats,
        target_duration: parseInt(duration),
        ...(tone ? { tone } : {}),
        ...(niche ? { niche } : {}),
        ...(audience ? { audience } : {}),
        ...(sceneDescription ? { scene_description: sceneDescription } : {}),
        ...(style === "lifestyle" ? { with_human: withHuman } : {}),
        video_model: videoModel,
      };
      const job = await createAdJob(req);
      router.push(`/ads/${job.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar video ad");
    } finally {
      setSubmitting(false);
    }
  }

  const section1Filled = !!productName.trim();
  const section2Filled = !!(niche || audience || tone);
  const section3Filled = !!style;
  const section4Filled = formats.length > 0;

  const estimatedCost = style === "cinematic" ? 2.5 : style === "narrated" ? 3.0 : 2.0;

  return (
    <div className="space-y-3 max-w-2xl">
      {/* Section 1: Produto */}
      <Section
        title="Produto"
        icon={Package}
        step={1}
        open={openSection === 1}
        onToggle={() => toggleSection(1)}
        filled={section1Filled}
      >
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Nome do produto</label>
          <Input
            placeholder="Ex: Tenis Runner Pro X"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
        </div>

        {section1Filled && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => { toggleSection(2); }}
            className="mt-2"
          >
            Proximo
          </Button>
        )}
      </Section>

      {/* Section 2: Contexto */}
      <Section
        title="Contexto"
        icon={Target}
        step={2}
        open={openSection === 2}
        onToggle={() => toggleSection(2)}
        filled={section2Filled}
      >
        <Button
          variant="outline"
          size="sm"
          onClick={handleAnalyze}
          disabled={!productName.trim() || analyzing}
        >
          {analyzing ? (
            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-3 w-3" />
          )}
          Analisar com IA
        </Button>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Nicho</label>
            <Select value={niche} onValueChange={setNiche}>
              <SelectTrigger><SelectValue placeholder="Selecionar" /></SelectTrigger>
              <SelectContent>
                {NICHES.map((n) => (
                  <SelectItem key={n.value} value={n.value}>{n.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Tom</label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger><SelectValue placeholder="Selecionar" /></SelectTrigger>
              <SelectContent>
                {TONES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Publico-alvo</label>
          <Input
            placeholder="Ex: Mulheres 25-35, fitness, classe A/B"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          />
        </div>
      </Section>

      {/* Section 3: Estilo */}
      <Section
        title="Estilo"
        icon={Palette}
        step={3}
        open={openSection === 3}
        onToggle={() => toggleSection(3)}
        filled={section3Filled}
      >
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">Tipo de video</label>
          <div className="grid grid-cols-1 gap-2">
            {STYLES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setStyle(s.value)}
                className={`text-left rounded-lg border p-3 transition-colors ${
                  style === s.value
                    ? "border-purple-500 bg-purple-500/10"
                    : "border-border hover:border-purple-500/50"
                }`}
              >
                <p className="text-sm font-medium">{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Descricao da cena</label>
          <Textarea
            placeholder="Ex: Produto em mesa de marmore com luz natural lateral"
            value={sceneDescription}
            onChange={(e) => setSceneDescription(e.target.value)}
            rows={3}
          />
        </div>

        {style === "lifestyle" && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={withHuman}
              onChange={(e) => setWithHuman(e.target.checked)}
              className="accent-purple-500"
            />
            Incluir pessoa no video
          </label>
        )}

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Duracao</label>
          <Select value={duration} onValueChange={setDuration}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="8">8 segundos</SelectItem>
              <SelectItem value="15">15 segundos</SelectItem>
              <SelectItem value="30">30 segundos</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Section>

      {/* Section 4: Audio & Formato */}
      <Section
        title="Audio & Formato"
        icon={Volume2}
        step={4}
        open={openSection === 4}
        onToggle={() => toggleSection(4)}
        filled={section4Filled}
      >
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Audio</label>
          <Select value={audioMode} onValueChange={(v) => setAudioMode(v as typeof audioMode)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {AUDIO_MODES.map((a) => (
                <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Formatos de saida</label>
          <div className="flex gap-2">
            {["9:16", "16:9", "1:1"].map((fmt) => (
              <button
                key={fmt}
                type="button"
                onClick={() => toggleFormat(fmt)}
                className={`px-3 py-1.5 rounded-md border text-sm transition-colors ${
                  formats.includes(fmt)
                    ? "border-purple-500 bg-purple-500/10 text-purple-400"
                    : "border-border text-muted-foreground hover:border-purple-500/50"
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
          {formats.length === 0 && (
            <p className="text-xs text-red-400">Selecione ao menos um formato</p>
          )}
        </div>

        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Modelo de video</label>
          <Select value={videoModel} onValueChange={setVideoModel}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="kling-v2">Kling v2</SelectItem>
              <SelectItem value="kling-v1.6">Kling v1.6</SelectItem>
              <SelectItem value="runway-gen3">Runway Gen3</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Section>

      {/* Cost estimate + Submit */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Custo estimado:</span>
            <span className="text-sm font-medium text-purple-400">
              {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(estimatedCost)}
            </span>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button
            className="w-full"
            onClick={handleSubmit}
            disabled={!productName.trim() || formats.length === 0 || submitting}
          >
            {submitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Film className="mr-2 h-4 w-4" />
            )}
            Criar Video Ad
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
