"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Clapperboard,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Settings,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Wand2,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { useReelJobs, useReelStatus, useReelsConfig, useReelsPresets } from "@/hooks/use-reels";
import { useCharacters } from "@/hooks/use-api";
import {
  generateReel,
  createInteractiveReel,
  saveReelsConfig,
  type ReelGenerateRequest,
  type ReelJob,
  type ReelsConfig,
} from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  images: "Gerando imagens...",
  script: "Criando roteiro...",
  tts: "Gerando narracao...",
  transcription: "Transcrevendo...",
  assembly: "Montando video...",
  upload: "Fazendo upload...",
};

const STATUS_BADGE: Record<string, { color: string; label: string }> = {
  queued: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "Na fila" },
  generating: { color: "bg-blue-500/20 text-blue-400 border-blue-500/30", label: "Gerando" },
  interactive: { color: "bg-purple-500/20 text-purple-400 border-purple-500/30", label: "Interativo" },
  complete: { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", label: "Completo" },
  failed: { color: "bg-red-500/20 text-red-400 border-red-500/30", label: "Falhou" },
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function formatCost(brl: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(brl);
}

// ── Generation Form ────────────────────────────────────────────────

function GenerationForm() {
  const router = useRouter();
  const [tema, setTema] = useState("");
  const [characterId, setCharacterId] = useState<string>("auto");
  const [tone, setTone] = useState("inspiracional");
  const [duration, setDuration] = useState("30");
  const [niche, setNiche] = useState("lifestyle");
  const [preset, setPreset] = useState("clean");
  const [showAjustes, setShowAjustes] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submittingInteractive, setSubmittingInteractive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: presets } = useReelsPresets();
  const { data: characters } = useCharacters();
  const { data: jobStatus } = useReelStatus(activeJobId);

  const isComplete = jobStatus?.status === "complete";
  const isFailed = jobStatus?.status === "failed";
  const isGenerating = activeJobId && !isComplete && !isFailed;

  async function handleGenerate() {
    if (!tema.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const req: ReelGenerateRequest = {
        tema: tema.trim(),
        tone,
        target_duration: parseInt(duration),
        niche,
        ...(characterId === "none"
          ? { no_character: true }
          : characterId !== "auto"
            ? { character_slug: characterId }
            : {}),
      };
      const res = await generateReel(req);
      setActiveJobId(res.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao gerar reel");
    } finally {
      setSubmitting(false);
    }
  }

  function handleReset() {
    setActiveJobId(null);
    setTema("");
    setError(null);
  }

  async function handleInteractive() {
    if (!tema.trim()) return;
    setSubmittingInteractive(true);
    setError(null);
    try {
      const res = await createInteractiveReel({
        tema: tema.trim(),
        target_duration: parseInt(duration),
        ...(characterId === "none"
          ? { no_character: true }
          : characterId !== "auto"
            ? { character_slug: characterId }
            : {}),
      });
      router.push(`/reels/${res.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar reel interativo");
    } finally {
      setSubmittingInteractive(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clapperboard className="h-5 w-5 text-purple-400" />
          Gerar Reel
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress display */}
        {isGenerating && jobStatus && (
          <div className="space-y-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-center gap-2 text-sm text-blue-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              {STEP_LABELS[jobStatus.current_step ?? ""] ?? "Processando..."}
            </div>
            <Progress value={jobStatus.progress_pct} className="h-2" />
            <p className="text-xs text-muted-foreground">{jobStatus.progress_pct}% completo</p>
          </div>
        )}

        {/* Complete state */}
        {isComplete && jobStatus && (
          <div className="space-y-3 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">Reel pronto!</span>
            </div>
            {jobStatus.video_url && (
              <a
                href={jobStatus.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-purple-400 hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                Ver video
              </a>
            )}
            {jobStatus.caption && (
              <p className="text-xs text-muted-foreground">{jobStatus.caption}</p>
            )}
            <Button variant="outline" size="sm" onClick={handleReset}>
              Novo Reel
            </Button>
          </div>
        )}

        {/* Failed state */}
        {isFailed && jobStatus && (
          <div className="space-y-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 text-red-400">
              <XCircle className="h-5 w-5" />
              <span className="font-medium">Falha na geracao</span>
            </div>
            <p className="text-xs text-red-300">{jobStatus.error_message ?? "Erro desconhecido"}</p>
            <Button variant="outline" size="sm" onClick={handleReset}>
              Tentar Novamente
            </Button>
          </div>
        )}

        {/* Form (hidden while generating) */}
        {!isGenerating && !isComplete && !isFailed && (
          <>
            {/* Character selector */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Personagem</label>
              <Select value={characterId} onValueChange={setCharacterId}>
                <SelectTrigger><SelectValue placeholder="Selecionar personagem" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Automatico (primeiro personagem)</SelectItem>
                  <SelectItem value="none">Sem personagem (generico)</SelectItem>
                  {(characters?.characters ?? []).map((c) => (
                    <SelectItem key={c.slug} value={c.slug}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Textarea
              placeholder="Ex: 3 habitos matinais que mudaram minha produtividade"
              value={tema}
              onChange={(e) => setTema(e.target.value)}
              rows={3}
            />

            {/* Collapsible settings */}
            <button
              type="button"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setShowAjustes(!showAjustes)}
            >
              {showAjustes ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              Ajustes
            </button>

            {showAjustes && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Tom</label>
                  <Select value={tone} onValueChange={setTone}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="inspiracional">Inspiracional</SelectItem>
                      <SelectItem value="humor">Humor</SelectItem>
                      <SelectItem value="educativo">Educativo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Duracao</label>
                  <Select value={duration} onValueChange={setDuration}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="15">15 segundos</SelectItem>
                      <SelectItem value="30">30 segundos</SelectItem>
                      <SelectItem value="60">60 segundos</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Nicho</label>
                  <Input value={niche} onChange={(e) => setNiche(e.target.value)} />
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Preset</label>
                  <Select value={preset} onValueChange={setPreset}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {presets?.presets ? (
                        Object.keys(presets.presets).map((k) => (
                          <SelectItem key={k} value={k}>{k.charAt(0).toUpperCase() + k.slice(1)}</SelectItem>
                        ))
                      ) : (
                        <>
                          <SelectItem value="clean">Clean</SelectItem>
                          <SelectItem value="bold">Bold</SelectItem>
                          <SelectItem value="minimal">Minimal</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {error && <p className="text-sm text-red-400">{error}</p>}

            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={handleGenerate}
                disabled={!tema.trim() || submitting || submittingInteractive}
              >
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Gerar Reel
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleInteractive}
                disabled={!tema.trim() || submitting || submittingInteractive}
              >
                {submittingInteractive ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="mr-2 h-4 w-4" />
                )}
                Criar Reel Interativo
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ── Job History ────────────────────────────────────────────────────

function JobHistory() {
  const { data: jobs, isLoading } = useReelJobs();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-purple-400" />
            Historico
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 rounded-lg bg-secondary animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-purple-400" />
            Historico
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhum reel gerado ainda. Comece criando o primeiro!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-purple-400" />
          Historico
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {jobs.map((job: ReelJob) => {
            const badge = STATUS_BADGE[job.status] ?? STATUS_BADGE.queued;
            return (
              <div
                key={job.job_id}
                className="rounded-lg border bg-card p-4 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium line-clamp-2">{job.tema}</p>
                  <Badge variant="outline" className={badge.color}>
                    {job.status === "generating" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    {badge.label}
                  </Badge>
                </div>

                {job.status === "interactive" && (
                  <a
                    href={`/reels/${job.job_id}`}
                    className="inline-flex items-center gap-1 text-xs text-purple-400 hover:underline"
                  >
                    <ArrowRight className="h-3 w-3" />
                    Continuar
                  </a>
                )}

                {job.status === "complete" && job.video_url && (
                  <a
                    href={job.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-purple-400 hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Ver video
                  </a>
                )}

                {job.status === "failed" && job.error_message && (
                  <p className="text-xs text-red-400 line-clamp-2">{job.error_message}</p>
                )}

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{job.created_at ? formatDate(job.created_at) : ""}</span>
                  <span>{formatCost(job.cost_brl ?? 0)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Config Panel ───────────────────────────────────────────────────

function ConfigPanel() {
  const { data: configs } = useReelsConfig();
  const config = configs?.[0];

  const [ttsVoice, setTtsVoice] = useState(config?.tts_voice ?? "nova");
  const [ttsSpeed, setTtsSpeed] = useState(String(config?.tts_speed ?? 1.1));
  const [imageCount, setImageCount] = useState(String(config?.image_count ?? 5));
  const [imageDuration, setImageDuration] = useState(String(config?.image_duration ?? 4));
  const [transitionType, setTransitionType] = useState(config?.transition_type ?? "fade");
  const [subtitleFontSize, setSubtitleFontSize] = useState(String(config?.subtitle_font_size ?? 52));
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await saveReelsConfig({
        tts_voice: ttsVoice,
        tts_speed: parseFloat(ttsSpeed),
        image_count: parseInt(imageCount),
        image_duration: parseFloat(imageDuration),
        transition_type: transitionType,
        subtitle_font_size: parseInt(subtitleFontSize),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // silently fail for now
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader
        className="cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-purple-400" />
          Configuracoes do Pipeline
          {expanded ? <ChevronUp className="h-4 w-4 ml-auto" /> : <ChevronDown className="h-4 w-4 ml-auto" />}
        </CardTitle>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Voz TTS</label>
              <Select value={ttsVoice} onValueChange={setTtsVoice}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="nova">Nova</SelectItem>
                  <SelectItem value="shimmer">Shimmer</SelectItem>
                  <SelectItem value="alloy">Alloy</SelectItem>
                  <SelectItem value="echo">Echo</SelectItem>
                  <SelectItem value="fable">Fable</SelectItem>
                  <SelectItem value="onyx">Onyx</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Velocidade TTS ({ttsSpeed}x)</label>
              <input
                type="range"
                min="0.8"
                max="1.5"
                step="0.1"
                value={ttsSpeed}
                onChange={(e) => setTtsSpeed(e.target.value)}
                className="w-full accent-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Imagens ({imageCount})</label>
              <input
                type="range"
                min="5"
                max="10"
                step="1"
                value={imageCount}
                onChange={(e) => setImageCount(e.target.value)}
                className="w-full accent-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Duracao por imagem ({imageDuration}s)</label>
              <input
                type="range"
                min="3"
                max="6"
                step="0.5"
                value={imageDuration}
                onChange={(e) => setImageDuration(e.target.value)}
                className="w-full accent-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Transicao</label>
              <Select value={transitionType} onValueChange={setTransitionType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="fade">Fade</SelectItem>
                  <SelectItem value="cut">Cut</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Fonte legendas ({subtitleFontSize}px)</label>
              <input
                type="range"
                min="36"
                max="72"
                step="2"
                value={subtitleFontSize}
                onChange={(e) => setSubtitleFontSize(e.target.value)}
                className="w-full accent-purple-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={handleSave} disabled={saving} size="sm">
              {saving ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : null}
              Salvar
            </Button>
            {saved && (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Salvo
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────

export default function ReelsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reels</h1>
        <p className="text-muted-foreground">
          Gere Instagram Reels automaticamente a partir de um tema
        </p>
      </div>

      <GenerationForm />
      <JobHistory />
      <ConfigPanel />
    </div>
  );
}
