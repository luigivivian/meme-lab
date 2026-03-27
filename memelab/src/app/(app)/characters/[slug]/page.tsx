"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { mutate as globalMutate } from "swr";
import {
  ArrowLeft,
  Save,
  Trash2,
  User,
  Palette,
  MessageSquare,
  Eye,
  Check,
  Loader2,
  Plus,
  X,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Sparkles,
  Image as ImageIcon,
  Wand2,
} from "lucide-react";
import { useCharacter, useCharacterValidation, useRenderingPresets } from "@/hooks/use-api";
import {
  updateCharacter,
  deleteCharacter,
  testCharacterPhrases,
  testCharacterVisual,
  testCharacterCompose,
  refImageUrl,
  imageUrl,
} from "@/lib/api";
import type {
  CharacterDetail,
  ValidationResult,
  PhraseValidation,
  TestVisualResult,
  TestComposeResult,
  RenderingConfig,
  RenderingPresetsResponse,
} from "@/lib/api";

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string }
> = {
  draft: {
    label: "Rascunho",
    color: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  },
  refining: {
    label: "Refinando",
    color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
  ready: {
    label: "Pronto",
    color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  },
};

const TABS = [
  { key: "overview", label: "Visao Geral", icon: Eye },
  { key: "persona", label: "Personalidade", icon: MessageSquare },
  { key: "visual", label: "Visual", icon: Palette },
  { key: "branding", label: "Branding", icon: User },
  { key: "validacao", label: "Validacao", icon: ShieldCheck },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const inputClass =
  "w-full rounded-xl border bg-secondary/50 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";
const labelClass = "text-sm font-medium text-muted-foreground";

// ── EditableList ─────────────────────────────────────────────────────────────

function EditableList({
  items,
  onChange,
  placeholder,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  function add() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onChange([...items, trimmed]);
    setDraft("");
  }

  function remove(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          className={inputClass}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={add}
          className="shrink-0 rounded-xl border bg-secondary/50 px-3 py-3 text-sm hover:bg-secondary transition-colors"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {items.map((item, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 rounded-full border bg-secondary/50 px-3 py-1 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => remove(i)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-12">
      <div className="flex items-center gap-3">
        <div className="h-4 w-24 rounded bg-secondary animate-pulse" />
      </div>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-8 w-56 rounded bg-secondary animate-pulse" />
          <div className="h-5 w-32 rounded bg-secondary animate-pulse" />
        </div>
        <div className="h-10 w-24 rounded-xl bg-secondary animate-pulse" />
      </div>
      <div className="flex gap-1 border-b">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="h-10 w-28 rounded-t bg-secondary animate-pulse"
          />
        ))}
      </div>
      <div className="rounded-2xl border bg-card p-6 space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-secondary animate-pulse" />
        ))}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = typeof params.slug === "string" ? params.slug : "";
  const { data, isLoading, mutate } = useCharacter(slug || null);
  const { data: validation, mutate: revalidate } = useCharacterValidation(slug || null);
  const { data: presets } = useRenderingPresets();

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // ── Persona form state ──────────────────────────────────────────────────
  const [personaForm, setPersonaForm] = useState({
    system_prompt: "",
    humor_style: "",
    tone: "",
    catchphrases: [] as string[],
    max_chars: 120,
    forbidden: [] as string[],
  });

  // ── Visual form state ───────────────────────────────────────────────────
  const [visualForm, setVisualForm] = useState({
    character_dna: "",
    negative_traits: "",
    composition: "",
    rendering: {} as RenderingConfig,
  });

  // ── Info form state (overview) ──────────────────────────────────────────
  const [infoForm, setInfoForm] = useState({
    name: "",
    handle: "",
    watermark: "",
  });

  // ── Branding form state ─────────────────────────────────────────────────
  const [brandingForm, setBrandingForm] = useState({
    watermark: "",
    branded_hashtags: [] as string[],
    caption_prompt: "",
  });

  // ── Initialize form state from data ─────────────────────────────────────
  useEffect(() => {
    if (!data) return;
    setPersonaForm({
      system_prompt: data.persona.system_prompt ?? "",
      humor_style: data.persona.humor_style ?? "",
      tone: data.persona.tone ?? "",
      catchphrases: data.persona.catchphrases ?? [],
      max_chars: data.persona.rules?.max_chars ?? 120,
      forbidden: data.persona.rules?.forbidden ?? [],
    });
    setVisualForm({
      character_dna: data.visual.character_dna ?? "",
      negative_traits: data.visual.negative_traits ?? "",
      composition: data.visual.composition ?? "",
      rendering: data.visual.rendering ?? {},
    });
    setInfoForm({
      name: data.name ?? "",
      handle: data.handle ?? "",
      watermark: data.watermark ?? "",
    });
    setBrandingForm({
      watermark: data.watermark ?? "",
      branded_hashtags: data.branding.branded_hashtags ?? [],
      caption_prompt: data.branding.caption_prompt ?? "",
    });
  }, [data]);

  // ── Save info (overview) ────────────────────────────────────────────────
  async function saveInfo() {
    if (!slug) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateCharacter(slug, {
        name: infoForm.name,
        handle: infoForm.handle,
        watermark: infoForm.watermark,
      });
      setSaveSuccess(true);
      mutate();
      globalMutate("characters");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  // ── Clear save success after delay ──────────────────────────────────────
  useEffect(() => {
    if (!saveSuccess) return;
    const timer = setTimeout(() => setSaveSuccess(false), 2500);
    return () => clearTimeout(timer);
  }, [saveSuccess]);

  // ── Save handlers ───────────────────────────────────────────────────────

  async function savePersona() {
    if (!slug) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateCharacter(slug, {
        persona: {
          system_prompt: personaForm.system_prompt,
          humor_style: personaForm.humor_style,
          tone: personaForm.tone,
          catchphrases: personaForm.catchphrases,
          rules: {
            max_chars: personaForm.max_chars,
            forbidden: personaForm.forbidden,
          },
        },
      });
      await mutate();
      setSaveSuccess(true);
    } catch (err: unknown) {
      setSaveError(
        err instanceof Error ? err.message : "Erro ao salvar personalidade"
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveVisual() {
    if (!slug) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateCharacter(slug, {
        visual: {
          character_dna: visualForm.character_dna,
          negative_traits: visualForm.negative_traits,
          composition: visualForm.composition,
          rendering: visualForm.rendering,
        },
      });
      await mutate();
      setSaveSuccess(true);
    } catch (err: unknown) {
      setSaveError(
        err instanceof Error ? err.message : "Erro ao salvar visual"
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveBranding() {
    if (!slug) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateCharacter(slug, {
        watermark: brandingForm.watermark,
        branding: {
          branded_hashtags: brandingForm.branded_hashtags,
          caption_prompt: brandingForm.caption_prompt,
        },
      });
      await mutate();
      setSaveSuccess(true);
    } catch (err: unknown) {
      setSaveError(
        err instanceof Error ? err.message : "Erro ao salvar branding"
      );
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(newStatus: "draft" | "refining" | "ready") {
    if (!slug) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateCharacter(slug, { status: newStatus });
      await mutate();
      setSaveSuccess(true);
    } catch (err: unknown) {
      setSaveError(
        err instanceof Error ? err.message : "Erro ao alterar status"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!slug) return;
    setDeleting(true);
    try {
      await deleteCharacter(slug);
      globalMutate("characters");
      router.push("/characters");
    } catch (err: unknown) {
      setSaveError(
        err instanceof Error ? err.message : "Erro ao deletar personagem"
      );
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  // ── Loading / error state ───────────────────────────────────────────────

  if (isLoading || !data) return <LoadingSkeleton />;

  const status = STATUS_CONFIG[data.status] ?? STATUS_CONFIG.draft;
  const refsTotal = data.refs.approved + data.refs.pending + data.refs.rejected;
  const refsProgress = data.refs.ideal > 0
    ? Math.min(100, (data.refs.approved / data.refs.ideal) * 100)
    : 0;

  // ── Tab renderers ───────────────────────────────────────────────────────

  function renderOverview() {
    return (
      <div className="space-y-6">
        {/* Info card — editable */}
        <div className="rounded-xl border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-primary">Informacoes</h3>
            <button
              onClick={saveInfo}
              disabled={saving}
              className="flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
              Salvar
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Nome</label>
              <input className={inputClass} value={infoForm.name} onChange={(e) => setInfoForm((p) => ({ ...p, name: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Handle</label>
              <input className={inputClass} value={infoForm.handle} onChange={(e) => setInfoForm((p) => ({ ...p, handle: e.target.value }))} placeholder="@handle" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Watermark</label>
              <input className={inputClass} value={infoForm.watermark} onChange={(e) => setInfoForm((p) => ({ ...p, watermark: e.target.value }))} placeholder="@handle" />
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Slug</p>
              <p className="text-sm font-medium font-mono px-4 py-3">{data!.slug}</p>
            </div>
          </div>
        </div>

        {/* Refs stats */}
        <div className="rounded-xl border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-primary">Referencias</h3>
            <Link
              href={`/characters/${slug}/refs`}
              className="text-xs text-primary hover:underline"
            >
              Gerenciar
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-emerald-500/10 px-3 py-3 text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {data!.refs.approved}
              </p>
              <p className="text-xs text-muted-foreground">Aprovadas</p>
            </div>
            <div className="rounded-lg bg-amber-500/10 px-3 py-3 text-center">
              <p className="text-2xl font-bold text-amber-400">
                {data!.refs.pending}
              </p>
              <p className="text-xs text-muted-foreground">Pendentes</p>
            </div>
            <div className="rounded-lg bg-red-500/10 px-3 py-3 text-center">
              <p className="text-2xl font-bold text-red-400">
                {data!.refs.rejected}
              </p>
              <p className="text-xs text-muted-foreground">Rejeitadas</p>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
              <span>Progresso</span>
              <span>
                {data!.refs.approved}/{data!.refs.ideal} (minimo:{" "}
                {data!.refs.min_required})
              </span>
            </div>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  data!.refs.is_ready ? "bg-emerald-500" : "bg-primary"
                }`}
                style={{ width: `${refsProgress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Themes count */}
        <div className="rounded-xl border bg-card p-5 space-y-2">
          <h3 className="text-sm font-semibold text-primary">Temas</h3>
          <p className="text-2xl font-bold">{data!.themes_count}</p>
          <p className="text-xs text-muted-foreground">
            temas visuais configurados
          </p>
        </div>

        {/* Status change */}
        <div className="rounded-xl border bg-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-primary">Status</h3>
          <div className="flex gap-2">
            {(["draft", "refining", "ready"] as const).map((s) => {
              const cfg = STATUS_CONFIG[s];
              const isActive = data!.status === s;
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => !isActive && changeStatus(s)}
                  disabled={saving || isActive}
                  className={`inline-flex items-center gap-1.5 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                    isActive
                      ? `${cfg.color} ring-2 ring-offset-1 ring-offset-background`
                      : "border-border bg-secondary/50 text-muted-foreground hover:bg-secondary"
                  } disabled:cursor-not-allowed`}
                >
                  {isActive && <Check className="h-3.5 w-3.5" />}
                  {cfg.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  function renderPersona() {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <label className={labelClass}>System prompt</label>
          <textarea
            className={`${inputClass} min-h-[140px] resize-y`}
            value={personaForm.system_prompt}
            onChange={(e) =>
              setPersonaForm((p) => ({ ...p, system_prompt: e.target.value }))
            }
            placeholder="Descreva a personalidade do personagem..."
          />
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass}>Estilo de humor</label>
            <input
              className={inputClass}
              value={personaForm.humor_style}
              onChange={(e) =>
                setPersonaForm((p) => ({ ...p, humor_style: e.target.value }))
              }
              placeholder="Ex: zoeiro relatable"
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Tom</label>
            <input
              className={inputClass}
              value={personaForm.tone}
              onChange={(e) =>
                setPersonaForm((p) => ({ ...p, tone: e.target.value }))
              }
              placeholder="Ex: leve, engracado, viral"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Bordoes / Catchphrases</label>
          <EditableList
            items={personaForm.catchphrases}
            onChange={(v) =>
              setPersonaForm((p) => ({ ...p, catchphrases: v }))
            }
            placeholder="Adicionar bordao..."
          />
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass}>Max caracteres por frase</label>
            <input
              type="number"
              className={inputClass}
              value={personaForm.max_chars}
              onChange={(e) =>
                setPersonaForm((p) => ({
                  ...p,
                  max_chars: parseInt(e.target.value) || 120,
                }))
              }
              min={40}
              max={300}
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Topicos proibidos</label>
            <EditableList
              items={personaForm.forbidden}
              onChange={(v) =>
                setPersonaForm((p) => ({ ...p, forbidden: v }))
              }
              placeholder="Ex: politica"
            />
          </div>
        </div>

        {saveError && activeTab === "persona" && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {saveError}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={savePersona}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Salvar
          </button>
          {saveSuccess && activeTab === "persona" && (
            <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400">
              <Check className="h-4 w-4" />
              Salvo com sucesso
            </span>
          )}
        </div>
      </div>
    );
  }

  function renderVisual() {
    const r = visualForm.rendering || {};
    const selectClass =
      "w-full rounded-xl border bg-secondary/50 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary appearance-none cursor-pointer";

    function setRendering(patch: Partial<RenderingConfig>) {
      setVisualForm((p) => ({
        ...p,
        rendering: { ...p.rendering, ...patch },
      }));
    }

    return (
      <div className="space-y-6">
        {/* ── Estilo de Rendering ─────────────────────────────── */}
        <div className="rounded-xl border bg-secondary/20 p-4 space-y-5">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Estilo de Rendering
          </h3>

          {/* Art Style */}
          <div className="space-y-2">
            <label className={labelClass}>Estilo Artistico</label>
            <select
              className={selectClass}
              value={r.art_style || "photorealistic"}
              onChange={(e) =>
                setRendering({ art_style: e.target.value, art_style_custom: "" })
              }
            >
              {presets?.art_style
                ? Object.entries(presets.art_style).map(([key, val]) => (
                    <option key={key} value={key}>
                      {val.label}
                    </option>
                  ))
                : (
                  <>
                    <option value="photorealistic">Fotorrealista</option>
                    <option value="cartoon_3d">Cartoon 3D (Pixar/Nintendo)</option>
                    <option value="cartoon_2d">Cartoon 2D</option>
                    <option value="anime">Anime / Manga</option>
                    <option value="watercolor">Aquarela</option>
                    <option value="oil_painting">Pintura a Oleo</option>
                    <option value="comic_book">HQ / Comic Book</option>
                    <option value="pixel_art">Pixel Art</option>
                  </>
                )}
              <option value="custom">Customizado</option>
            </select>
            {presets?.art_style?.[r.art_style || "photorealistic"] && (
              <p className="text-xs text-muted-foreground px-1">
                {presets.art_style[r.art_style || "photorealistic"].prompt.slice(0, 120)}...
              </p>
            )}
            {r.art_style === "custom" && (
              <textarea
                className={`${inputClass} min-h-[80px] resize-y mt-2`}
                value={r.art_style_custom || ""}
                onChange={(e) => setRendering({ art_style_custom: e.target.value })}
                placeholder="Descreva o estilo artistico desejado em ingles..."
              />
            )}
          </div>

          {/* Lighting */}
          <div className="space-y-2">
            <label className={labelClass}>Iluminacao</label>
            <select
              className={selectClass}
              value={r.lighting || "cinematic"}
              onChange={(e) =>
                setRendering({ lighting: e.target.value, lighting_custom: "" })
              }
            >
              {presets?.lighting
                ? Object.entries(presets.lighting).map(([key, val]) => (
                    <option key={key} value={key}>
                      {val.label}
                    </option>
                  ))
                : (
                  <>
                    <option value="cinematic">Cinematico</option>
                    <option value="studio">Estudio</option>
                    <option value="natural">Natural</option>
                    <option value="dramatic">Dramatico</option>
                    <option value="flat">Flat / Uniforme</option>
                    <option value="neon">Neon / Cyberpunk</option>
                    <option value="golden_hour">Golden Hour</option>
                  </>
                )}
              <option value="custom">Customizado</option>
            </select>
            {r.lighting === "custom" && (
              <textarea
                className={`${inputClass} min-h-[60px] resize-y mt-2`}
                value={r.lighting_custom || ""}
                onChange={(e) => setRendering({ lighting_custom: e.target.value })}
                placeholder="Descreva a iluminacao desejada..."
              />
            )}
          </div>

          {/* Camera */}
          <div className="space-y-2">
            <label className={labelClass}>Camera / Enquadramento</label>
            <select
              className={selectClass}
              value={r.camera || "portrait_85mm"}
              onChange={(e) =>
                setRendering({ camera: e.target.value, camera_custom: "" })
              }
            >
              {presets?.camera
                ? Object.entries(presets.camera).map(([key, val]) => (
                    <option key={key} value={key}>
                      {val.label}
                    </option>
                  ))
                : (
                  <>
                    <option value="portrait_85mm">Retrato 85mm</option>
                    <option value="wide_angle">Grande Angular</option>
                    <option value="close_up">Close-up</option>
                    <option value="full_body">Corpo Inteiro</option>
                    <option value="dynamic">Dinamico</option>
                  </>
                )}
              <option value="custom">Customizado</option>
            </select>
            {r.camera === "custom" && (
              <textarea
                className={`${inputClass} min-h-[60px] resize-y mt-2`}
                value={r.camera_custom || ""}
                onChange={(e) => setRendering({ camera_custom: e.target.value })}
                placeholder="Descreva o enquadramento desejado..."
              />
            )}
          </div>

          {/* Extra Instructions */}
          <div className="space-y-2">
            <label className={labelClass}>Instrucoes extras (opcional)</label>
            <textarea
              className={`${inputClass} min-h-[60px] resize-y`}
              value={r.extra_instructions || ""}
              onChange={(e) => setRendering({ extra_instructions: e.target.value })}
              placeholder="Instrucoes adicionais para o modelo de imagem..."
            />
          </div>
        </div>

        {/* ── Character DNA ──────────────────────────────────── */}
        <div className="space-y-2">
          <label className={labelClass}>
            Character DNA (descricao visual detalhada)
          </label>
          <textarea
            className={`${inputClass} min-h-[160px] resize-y`}
            value={visualForm.character_dna}
            onChange={(e) =>
              setVisualForm((p) => ({ ...p, character_dna: e.target.value }))
            }
            placeholder="Descricao visual detalhada do personagem..."
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Negative traits</label>
          <textarea
            className={`${inputClass} min-h-[100px] resize-y`}
            value={visualForm.negative_traits}
            onChange={(e) =>
              setVisualForm((p) => ({
                ...p,
                negative_traits: e.target.value,
              }))
            }
            placeholder="O que NAO deve aparecer na imagem..."
          />
          <p className="text-xs text-muted-foreground px-1">
            Negatives do estilo selecionado sao adicionados automaticamente. Aqui coloque negatives especificos do personagem.
          </p>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Notas de composicao</label>
          <textarea
            className={`${inputClass} min-h-[100px] resize-y`}
            value={visualForm.composition}
            onChange={(e) =>
              setVisualForm((p) => ({ ...p, composition: e.target.value }))
            }
            placeholder="Ex: personagem centralizado, 4:5, terco inferior livre para texto..."
          />
        </div>

        {saveError && activeTab === "visual" && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {saveError}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={saveVisual}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Salvar
          </button>
          {saveSuccess && activeTab === "visual" && (
            <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400">
              <Check className="h-4 w-4" />
              Salvo com sucesso
            </span>
          )}
        </div>
      </div>
    );
  }

  function renderBranding() {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <label className={labelClass}>Texto do watermark</label>
          <input
            className={inputClass}
            value={brandingForm.watermark}
            onChange={(e) =>
              setBrandingForm((p) => ({ ...p, watermark: e.target.value }))
            }
            placeholder="@handle"
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Hashtags branded</label>
          <EditableList
            items={brandingForm.branded_hashtags}
            onChange={(v) =>
              setBrandingForm((p) => ({ ...p, branded_hashtags: v }))
            }
            placeholder="Ex: #MagoMestre"
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Prompt de legenda (caption)</label>
          <textarea
            className={`${inputClass} min-h-[120px] resize-y`}
            value={brandingForm.caption_prompt}
            onChange={(e) =>
              setBrandingForm((p) => ({
                ...p,
                caption_prompt: e.target.value,
              }))
            }
            placeholder="Ex: Escreva uma legenda curta e engracada para Instagram, com CTA..."
          />
        </div>

        {saveError && activeTab === "branding" && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {saveError}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={saveBranding}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Salvar
          </button>
          {saveSuccess && activeTab === "branding" && (
            <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400">
              <Check className="h-4 w-4" />
              Salvo com sucesso
            </span>
          )}
        </div>
      </div>
    );
  }

  // ── Validacao tab ──────────────────────────────────────────────────

  function ValidationTab() {
    const [testTopic, setTestTopic] = useState("segunda-feira");
    const [testPose, setTestPose] = useState(
      "front-facing portrait, neutral expression, looking directly at camera"
    );
    const [testSituacao, setTestSituacao] = useState("sabedoria");

    const [phrasesLoading, setPhrasesLoading] = useState(false);
    const [phrasesResult, setPhrasesResult] = useState<PhraseValidation[] | null>(null);
    const [phrasesError, setPhrasesError] = useState<string | null>(null);

    const [visualLoading, setVisualLoading] = useState(false);
    const [visualResult, setVisualResult] = useState<TestVisualResult | null>(null);
    const [visualError, setVisualError] = useState<string | null>(null);

    const [composeLoading, setComposeLoading] = useState(false);
    const [composeResult, setComposeResult] = useState<TestComposeResult | null>(null);
    const [composeError, setComposeError] = useState<string | null>(null);

    async function runTestPhrases() {
      setPhrasesLoading(true);
      setPhrasesError(null);
      setPhrasesResult(null);
      try {
        const res = await testCharacterPhrases(slug, testTopic, 3);
        setPhrasesResult(res.phrases);
      } catch (err: unknown) {
        setPhrasesError(err instanceof Error ? err.message : "Erro ao testar frases");
      } finally {
        setPhrasesLoading(false);
      }
    }

    async function runTestVisual() {
      setVisualLoading(true);
      setVisualError(null);
      setVisualResult(null);
      try {
        const res = await testCharacterVisual(slug, testPose);
        setVisualResult(res);
      } catch (err: unknown) {
        setVisualError(err instanceof Error ? err.message : "Erro ao testar visual");
      } finally {
        setVisualLoading(false);
      }
    }

    async function runTestCompose() {
      setComposeLoading(true);
      setComposeError(null);
      setComposeResult(null);
      try {
        const res = await testCharacterCompose(slug, testTopic, testSituacao);
        setComposeResult(res);
      } catch (err: unknown) {
        setComposeError(err instanceof Error ? err.message : "Erro ao gerar preview");
      } finally {
        setComposeLoading(false);
      }
    }

    const AREA_LABELS: Record<string, string> = {
      identidade: "Identidade",
      persona: "Persona",
      visual: "Visual",
      refs: "Referencias",
      branding: "Branding",
      temas: "Temas",
    };

    const AREA_ORDER = ["identidade", "persona", "visual", "refs", "branding", "temas"];

    return (
      <div className="space-y-8">
        {/* ── Checklist de Prontidao ── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              Checklist de Prontidao
            </h3>
            <button
              type="button"
              onClick={() => revalidate()}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Atualizar
            </button>
          </div>

          {validation ? (
            <>
              {/* Score geral */}
              <div className="flex items-center gap-4 rounded-xl border bg-card p-4">
                <div className="relative h-16 w-16 shrink-0">
                  <svg className="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      className="text-secondary"
                    />
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      strokeWidth="3"
                      strokeDasharray={`${validation.overall_score}, 100`}
                      className={
                        validation.overall_score >= 80
                          ? "stroke-emerald-500"
                          : validation.overall_score >= 50
                          ? "stroke-amber-500"
                          : "stroke-red-500"
                      }
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
                    {validation.overall_score}%
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {validation.total_ok}/{validation.total_checks} criterios atendidos
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {validation.is_production_ready ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Pronto para producao
                      </span>
                    ) : (
                      <span className="text-amber-400 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Campos pendentes — complete para usar no pipeline
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* Checks por area */}
              <div className="space-y-3">
                {AREA_ORDER.map((area) => {
                  const areaChecks = validation.checks.filter((c) => c.area === area);
                  if (areaChecks.length === 0) return null;
                  const score = validation.area_scores[area] ?? 0;
                  return (
                    <div key={area} className="rounded-xl border bg-card overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-3 border-b bg-secondary/30">
                        <span className="text-sm font-medium">
                          {AREA_LABELS[area] || area}
                        </span>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            score === 100
                              ? "bg-emerald-500/20 text-emerald-400"
                              : score >= 50
                              ? "bg-amber-500/20 text-amber-400"
                              : "bg-red-500/20 text-red-400"
                          }`}
                        >
                          {score}%
                        </span>
                      </div>
                      <div className="divide-y">
                        {areaChecks.map((check, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-3 px-4 py-2.5 text-sm"
                          >
                            {check.ok ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                            )}
                            <span className="flex-1">{check.item}</span>
                            <span className="text-xs text-muted-foreground">
                              {check.detail}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="rounded-xl border bg-card p-6 text-center text-sm text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
              Carregando validacao...
            </div>
          )}
        </div>

        {/* ── Testar Persona ── */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Testar Persona
          </h3>
          <div className="rounded-xl border bg-card p-4 space-y-4">
            <div className="flex gap-2">
              <input
                className={inputClass}
                value={testTopic}
                onChange={(e) => setTestTopic(e.target.value)}
                placeholder="Tema para teste..."
              />
              <button
                type="button"
                onClick={runTestPhrases}
                disabled={phrasesLoading}
                className="shrink-0 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {phrasesLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Gerar
              </button>
            </div>

            {phrasesError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                {phrasesError}
              </div>
            )}

            {phrasesResult && (
              <div className="space-y-2">
                {phrasesResult.map((p, i) => (
                  <div
                    key={i}
                    className={`rounded-lg border px-3 py-2.5 text-sm ${
                      p.ok
                        ? "border-emerald-500/20 bg-emerald-500/5"
                        : "border-red-500/20 bg-red-500/5"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {p.ok ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="break-words">{p.phrase}</p>
                        <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                          <span
                            className={
                              p.over_limit ? "text-red-400" : ""
                            }
                          >
                            {p.chars} chars
                          </span>
                          {p.forbidden_found.length > 0 && (
                            <span className="text-red-400">
                              Proibido: {p.forbidden_found.join(", ")}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Testar Visual ── */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
            <ImageIcon className="h-4 w-4" />
            Testar Visual
          </h3>
          <div className="rounded-xl border bg-card p-4 space-y-4">
            <div className="flex gap-2">
              <input
                className={inputClass}
                value={testPose}
                onChange={(e) => setTestPose(e.target.value)}
                placeholder="Descreva a pose..."
              />
              <button
                type="button"
                onClick={runTestVisual}
                disabled={visualLoading}
                className="shrink-0 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {visualLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ImageIcon className="h-4 w-4" />
                )}
                Gerar
              </button>
            </div>

            {visualError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                {visualError}
              </div>
            )}

            {visualLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
                <Loader2 className="h-5 w-5 animate-spin" />
                Gerando imagem de teste via Gemini...
              </div>
            )}

            {visualResult && (
              <div className="space-y-2">
                <div className="rounded-xl overflow-hidden border max-w-xs mx-auto">
                  <img
                    src={refImageUrl(slug, visualResult.filename)}
                    alt="Teste visual"
                    className="w-full h-auto"
                  />
                </div>
                <p className="text-xs text-center text-muted-foreground">
                  Imagem salva em pending — aprove em{" "}
                  <a
                    href={`/characters/${slug}/refs`}
                    className="text-primary hover:underline"
                  >
                    Refs
                  </a>{" "}
                  se ficou boa
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── Preview Composicao ── */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
            <Wand2 className="h-4 w-4" />
            Preview Composicao (End-to-End)
          </h3>
          <div className="rounded-xl border bg-card p-4 space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className={labelClass}>Tema</label>
                <input
                  className={inputClass}
                  value={testTopic}
                  onChange={(e) => setTestTopic(e.target.value)}
                  placeholder="Tema..."
                />
              </div>
              <div className="space-y-1.5">
                <label className={labelClass}>Situacao visual</label>
                <input
                  className={inputClass}
                  value={testSituacao}
                  onChange={(e) => setTestSituacao(e.target.value)}
                  placeholder="Ex: sabedoria, cafe, tecnologia..."
                />
              </div>
            </div>
            <button
              type="button"
              onClick={runTestCompose}
              disabled={composeLoading}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {composeLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}
              Gerar Meme Completo
            </button>

            {composeError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                {composeError}
              </div>
            )}

            {composeLoading && (
              <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground py-6">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p>Gerando frase + background + composicao...</p>
                <p className="text-xs">Isso pode levar ate 30s</p>
              </div>
            )}

            {composeResult && (
              <div className="space-y-3">
                <div className="rounded-xl overflow-hidden border max-w-sm mx-auto">
                  <img
                    src={imageUrl(composeResult.image_path.split(/[/\\]/).pop() || "")}
                    alt="Meme completo"
                    className="w-full h-auto"
                  />
                </div>
                <div className="rounded-lg bg-secondary/50 px-3 py-2 text-sm space-y-1">
                  <p>
                    <span className="text-muted-foreground">Frase:</span>{" "}
                    {composeResult.phrase}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Tema:</span>{" "}
                    {composeResult.topic}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Situacao:</span>{" "}
                    {composeResult.situacao}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  function renderValidacao() {
    return <ValidationTab />;
  }

  const tabRenderers: Record<TabKey, () => React.JSX.Element> = {
    overview: renderOverview,
    persona: renderPersona,
    visual: renderVisual,
    branding: renderBranding,
    validacao: renderValidacao,
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-12">
      {/* Back link */}
      <Link
        href="/characters"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar para personagens
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{data.name}</h1>
            <span
              className={`text-xs px-2.5 py-1 rounded-full border ${status.color}`}
            >
              {status.label}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{data.handle}</p>
        </div>

        {/* Delete */}
        <div className="shrink-0">
          {confirmDelete ? (
            <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5">
              <span className="text-sm text-red-400 mr-1">Tem certeza?</span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                {deleting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Check className="h-3.5 w-3.5" />
                )}
                Confirmar
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
                className="inline-flex items-center gap-1.5 rounded-lg border bg-secondary/50 px-3 py-1.5 text-xs font-medium hover:bg-secondary transition-colors"
              >
                <X className="h-3.5 w-3.5" />
                Cancelar
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              Deletar
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b">
        <div className="flex gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => {
                  setActiveTab(tab.key);
                  setSaveError(null);
                  setSaveSuccess(false);
                }}
                className={`relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {isActive && (
                  <span className="absolute inset-x-0 -bottom-px h-0.5 bg-primary rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Global error (overview/status changes) */}
      {saveError && activeTab === "overview" && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {saveError}
        </div>
      )}

      {/* Global success (overview/status changes) */}
      {saveSuccess && activeTab === "overview" && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400 inline-flex items-center gap-1.5">
          <Check className="h-4 w-4" />
          Status atualizado com sucesso
        </div>
      )}

      {/* Tab content */}
      <div className="rounded-2xl border bg-card p-6">
        {tabRenderers[activeTab]()}
      </div>
    </div>
  );
}
