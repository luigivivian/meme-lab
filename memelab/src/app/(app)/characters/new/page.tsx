"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { mutate } from "swr";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Plus,
  X,
  Sparkles,
  User,
  Palette,
  MessageSquare,
  Eye,
  Wand2,
} from "lucide-react";
import { createCharacter, generateProfile } from "@/lib/api";
import type { CharacterCreateParams, GeneratedProfile } from "@/lib/api";

// ── Helpers ──────────────────────────────────────────────────────────────────

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function ensureHandle(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return trimmed.startsWith("@") ? trimmed : `@${trimmed}`;
}

// ── Types ────────────────────────────────────────────────────────────────────

interface FormState {
  // Step 1 — Identidade
  name: string;
  handle: string;
  description: string;
  // Step 2 — Personalidade
  system_prompt: string;
  humor_style: string;
  tone: string;
  catchphrases: string[];
  max_chars: number;
  forbidden: string[];
  // Step 3 — Aparencia Visual
  character_dna: string;
  negative_traits: string;
  composition: string;
  // Step 4 — Branding
  watermark: string;
  branded_hashtags: string[];
  caption_prompt: string;
}

const INITIAL_STATE: FormState = {
  name: "",
  handle: "",
  description: "",
  system_prompt: "",
  humor_style: "",
  tone: "",
  catchphrases: [],
  max_chars: 120,
  forbidden: [],
  character_dna: "",
  negative_traits: "",
  composition: "",
  watermark: "",
  branded_hashtags: [],
  caption_prompt: "",
};

const STEPS = [
  { label: "Identidade", icon: User },
  { label: "Personalidade", icon: MessageSquare },
  { label: "Visual", icon: Palette },
  { label: "Branding", icon: Sparkles },
  { label: "Resumo", icon: Eye },
] as const;

// ── Animation variants ───────────────────────────────────────────────────────

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 80 : -80,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction > 0 ? -80 : 80,
    opacity: 0,
  }),
};

// ── Reusable sub-components ─────────────────────────────────────────────────

const inputClass =
  "w-full rounded-xl border bg-secondary/50 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";
const labelClass = "text-sm font-medium text-muted-foreground";

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

function AiGeneratedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-[11px] font-medium text-primary">
      <Sparkles className="h-3 w-3" />
      Gerado por IA
    </span>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function NewCharacterPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // AI generation state
  const [generatingProfile, setGeneratingProfile] = useState(false);
  const [aiGenerated, setAiGenerated] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // ── Form updaters ────────────────────────────────────────────────────────

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  function goNext() {
    if (step >= STEPS.length - 1) return;
    setDirection(1);
    setStep((s) => s + 1);
  }

  function goBack() {
    if (step <= 0) return;
    setDirection(-1);
    setStep((s) => s - 1);
  }

  const canNext =
    step === 0 ? form.name.trim().length > 0 && form.description.trim().length > 0 : true;

  // ── Generate Full Profile ──────────────────────────────────────────────

  async function handleGenerateProfile() {
    if (!form.name.trim() || !form.description.trim()) return;
    setGeneratingProfile(true);
    setAiError(null);

    try {
      const { profile } = await generateProfile(
        form.name.trim(),
        form.description.trim(),
        form.handle.trim() || undefined,
      );
      applyProfile(profile);
      setAiGenerated(true);
      // Auto-advance to step 2
      setDirection(1);
      setStep(1);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao gerar perfil";
      setAiError(msg);
    } finally {
      setGeneratingProfile(false);
    }
  }

  function applyProfile(profile: GeneratedProfile) {
    setForm((prev) => ({
      ...prev,
      system_prompt: profile.system_prompt || prev.system_prompt,
      humor_style: profile.humor_style || prev.humor_style,
      tone: profile.tone || prev.tone,
      catchphrases: profile.catchphrases?.length ? profile.catchphrases : prev.catchphrases,
      max_chars: profile.max_chars || prev.max_chars,
      forbidden: profile.forbidden?.length ? profile.forbidden : prev.forbidden,
      character_dna: profile.character_dna || prev.character_dna,
      negative_traits: profile.negative_traits || prev.negative_traits,
      composition: profile.composition || prev.composition,
      branded_hashtags: profile.branded_hashtags?.length
        ? profile.branded_hashtags
        : prev.branded_hashtags,
      caption_prompt: profile.caption_prompt || prev.caption_prompt,
      watermark: profile.watermark || prev.watermark,
    }));
  }

  // ── Submit ───────────────────────────────────────────────────────────────

  async function handleCreate() {
    setCreating(true);
    setError(null);

    const params: CharacterCreateParams = {
      name: form.name.trim(),
      handle: form.handle ? ensureHandle(form.handle) : undefined,
      watermark: form.watermark.trim() || undefined,
      persona: {
        system_prompt: form.system_prompt || undefined,
        humor_style: form.humor_style || undefined,
        tone: form.tone || undefined,
        catchphrases: form.catchphrases.length ? form.catchphrases : undefined,
        rules:
          form.max_chars !== 120 || form.forbidden.length
            ? { max_chars: form.max_chars, forbidden: form.forbidden }
            : undefined,
      },
      visual: {
        character_dna: form.character_dna || undefined,
        negative_traits: form.negative_traits || undefined,
        composition: form.composition || undefined,
      },
      branding: {
        branded_hashtags: form.branded_hashtags.length
          ? form.branded_hashtags
          : undefined,
        caption_prompt: form.caption_prompt || undefined,
      },
    };

    try {
      await createCharacter(params);
      mutate("characters");
      router.push("/characters");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao criar personagem";
      setError(message);
    } finally {
      setCreating(false);
    }
  }

  // ── Step renderers ───────────────────────────────────────────────────────

  function renderStep1() {
    const slug = slugify(form.name);
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <label className={labelClass}>
            Nome do personagem <span className="text-red-400">*</span>
          </label>
          <input
            className={inputClass}
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="Ex: O Mago Mestre"
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Handle Instagram</label>
          <input
            className={inputClass}
            value={form.handle}
            onChange={(e) => update("handle", e.target.value)}
            placeholder="@magomestre420"
          />
        </div>

        {slug && (
          <div className="space-y-2">
            <label className={labelClass}>Slug (auto-gerado)</label>
            <div className="rounded-xl border bg-secondary/30 px-4 py-3 text-sm text-muted-foreground">
              {slug}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <label className={labelClass}>
            Descricao do personagem <span className="text-red-400">*</span>
          </label>
          <textarea
            className={`${inputClass} min-h-[100px] resize-y`}
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
            placeholder="Descreva o personagem em poucas palavras. Ex: 'Um mago velho e sabio estilo Gandalf que faz memes zoeiros sobre o dia a dia dos brasileiros. Tem barba longa cinza, chapeu pontudo e cajado de madeira.'"
          />
          <p className="text-xs text-muted-foreground">
            A IA usara essa descricao para gerar automaticamente: personalidade, DNA visual, branding e muito mais.
          </p>
        </div>

        {/* Generate Profile Button */}
        <div className="rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            <h3 className="text-sm font-semibold">Engenharia de prompt automatica</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Preencha nome e descricao acima. A IA gera tudo: persona, visual DNA, branding, hashtags, caption prompt — tudo editavel nos proximos passos.
          </p>
          <button
            type="button"
            onClick={handleGenerateProfile}
            disabled={generatingProfile || !form.name.trim() || !form.description.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generatingProfile ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Gerando perfil completo...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Gerar perfil com IA
              </>
            )}
          </button>
          {aiError && (
            <p className="text-xs text-red-400">{aiError}</p>
          )}
        </div>
      </div>
    );
  }

  function renderStep2() {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Personalidade</h3>
          {aiGenerated && <AiGeneratedBadge />}
        </div>

        <div className="space-y-2">
          <label className={labelClass}>System prompt</label>
          <textarea
            className={`${inputClass} min-h-[120px] resize-y`}
            value={form.system_prompt}
            onChange={(e) => update("system_prompt", e.target.value)}
            placeholder="Ex: Voce eh o Mago Mestre, um bruxo sabio e zoeiro..."
          />
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass}>Estilo de humor</label>
            <input
              className={inputClass}
              value={form.humor_style}
              onChange={(e) => update("humor_style", e.target.value)}
              placeholder="Ex: zoeiro relatable"
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Tom</label>
            <input
              className={inputClass}
              value={form.tone}
              onChange={(e) => update("tone", e.target.value)}
              placeholder="Ex: leve, engracado, viral"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Bordoes / Catchphrases</label>
          <EditableList
            items={form.catchphrases}
            onChange={(v) => update("catchphrases", v)}
            placeholder="Adicionar bordao..."
          />
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass}>Max caracteres por frase</label>
            <input
              type="number"
              className={inputClass}
              value={form.max_chars}
              onChange={(e) =>
                update("max_chars", parseInt(e.target.value) || 120)
              }
              min={40}
              max={300}
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Topicos proibidos</label>
            <EditableList
              items={form.forbidden}
              onChange={(v) => update("forbidden", v)}
              placeholder="Ex: politica"
            />
          </div>
        </div>
      </div>
    );
  }

  function renderStep3() {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Aparencia Visual</h3>
          {aiGenerated && <AiGeneratedBadge />}
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Character DNA (descricao visual detalhada)</label>
          <textarea
            className={`${inputClass} min-h-[160px] resize-y`}
            value={form.character_dna}
            onChange={(e) => update("character_dna", e.target.value)}
            placeholder="Ex: An old wizard with a long grey beard, wearing a tattered blue robe..."
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Negative traits</label>
          <textarea
            className={`${inputClass} min-h-[80px] resize-y`}
            value={form.negative_traits}
            onChange={(e) => update("negative_traits", e.target.value)}
            placeholder="NOT cartoon, NOT stylized, NOT anime, NOT text, NOT letters..."
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Notas de composicao</label>
          <textarea
            className={`${inputClass} min-h-[80px] resize-y`}
            value={form.composition}
            onChange={(e) => update("composition", e.target.value)}
            placeholder="Ex: personagem centralizado, iluminacao cinematica..."
          />
        </div>
      </div>
    );
  }

  function renderStep4() {
    const defaultWatermark = form.handle
      ? ensureHandle(form.handle)
      : form.name
        ? `@${slugify(form.name)}`
        : "";

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Branding</h3>
          {aiGenerated && <AiGeneratedBadge />}
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Texto do watermark</label>
          <input
            className={inputClass}
            value={form.watermark}
            onChange={(e) => update("watermark", e.target.value)}
            placeholder={defaultWatermark || "@handle"}
          />
          {!form.watermark && defaultWatermark && (
            <p className="text-xs text-muted-foreground">
              Padrao: {defaultWatermark}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Hashtags branded</label>
          <EditableList
            items={form.branded_hashtags}
            onChange={(v) => update("branded_hashtags", v)}
            placeholder="Ex: #MagoMestre"
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Prompt de legenda (caption)</label>
          <textarea
            className={`${inputClass} min-h-[100px] resize-y`}
            value={form.caption_prompt}
            onChange={(e) => update("caption_prompt", e.target.value)}
            placeholder="Ex: Escreva uma legenda curta e engracada para Instagram..."
          />
        </div>
      </div>
    );
  }

  function renderStep5() {
    const sections = [
      {
        title: "Identidade",
        items: [
          { label: "Nome", value: form.name },
          { label: "Handle", value: form.handle ? ensureHandle(form.handle) : "---" },
          { label: "Slug", value: slugify(form.name) || "---" },
          { label: "Descricao", value: form.description || "---" },
        ],
      },
      {
        title: "Personalidade",
        items: [
          { label: "System prompt", value: form.system_prompt || "---" },
          { label: "Humor", value: form.humor_style || "---" },
          { label: "Tom", value: form.tone || "---" },
          {
            label: "Bordoes",
            value: form.catchphrases.length
              ? form.catchphrases.join(", ")
              : "---",
          },
          { label: "Max chars", value: String(form.max_chars) },
          {
            label: "Proibidos",
            value: form.forbidden.length ? form.forbidden.join(", ") : "---",
          },
        ],
      },
      {
        title: "Visual",
        items: [
          { label: "Character DNA", value: form.character_dna || "---" },
          { label: "Negative traits", value: form.negative_traits || "---" },
          { label: "Composicao", value: form.composition || "---" },
        ],
      },
      {
        title: "Branding",
        items: [
          { label: "Watermark", value: form.watermark || "---" },
          {
            label: "Hashtags",
            value: form.branded_hashtags.length
              ? form.branded_hashtags.join(", ")
              : "---",
          },
          { label: "Caption prompt", value: form.caption_prompt || "---" },
        ],
      },
    ];

    return (
      <div className="space-y-6">
        {aiGenerated && (
          <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            <p className="text-sm text-primary">
              Perfil gerado por IA — revise os campos antes de criar.
            </p>
          </div>
        )}
        {sections.map((section) => (
          <div
            key={section.title}
            className="rounded-xl border bg-card p-4 space-y-3"
          >
            <h3 className="text-sm font-semibold text-primary">
              {section.title}
            </h3>
            <div className="space-y-2">
              {section.items.map((item) => (
                <div key={item.label} className="flex gap-3">
                  <span className="shrink-0 text-xs font-medium text-muted-foreground w-28">
                    {item.label}
                  </span>
                  <span className="text-sm break-all whitespace-pre-wrap">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}
      </div>
    );
  }

  const stepRenderers = [renderStep1, renderStep2, renderStep3, renderStep4, renderStep5];

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-2xl space-y-8 pb-12">
      {/* Header */}
      <div>
        <button
          type="button"
          onClick={() => router.push("/characters")}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para personagens
        </button>
        <h1 className="text-2xl font-bold">Novo personagem</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Descreva seu personagem e a IA faz a engenharia de prompt completa.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-between">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = i === step;
          const isDone = i < step;
          return (
            <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
              <div className="flex items-center w-full">
                {i > 0 && (
                  <div
                    className={`h-px flex-1 transition-colors ${
                      isDone ? "bg-primary" : "bg-border"
                    }`}
                  />
                )}
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                    isActive
                      ? "border-primary bg-primary text-primary-foreground"
                      : isDone
                        ? "border-primary bg-primary/20 text-primary"
                        : "border-border bg-secondary/50 text-muted-foreground"
                  }`}
                >
                  {isDone ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`h-px flex-1 transition-colors ${
                      isDone ? "bg-primary" : "bg-border"
                    }`}
                  />
                )}
              </div>
              <span
                className={`text-[11px] font-medium transition-colors ${
                  isActive
                    ? "text-primary"
                    : isDone
                      ? "text-primary/70"
                      : "text-muted-foreground"
                }`}
              >
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <div className="rounded-2xl border bg-card p-6 min-h-[360px] overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            {stepRenderers[step]()}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        {step > 0 ? (
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-2 rounded-xl border bg-secondary/50 px-5 py-2.5 text-sm font-medium hover:bg-secondary transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </button>
        ) : (
          <div />
        )}

        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={goNext}
            disabled={!canNext}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Proximo
            <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleCreate}
            disabled={creating || !form.name.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Criando...
              </>
            ) : (
              <>
                <Check className="h-4 w-4" />
                Criar Personagem
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
