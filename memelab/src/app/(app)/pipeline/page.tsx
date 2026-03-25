"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Play,
  List,
  Image,
  Loader2,
  CheckCircle2,
  X,
  Copy,
  Check,
  Info,
  Plus,
  Upload,
} from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { PipelineDiagram } from "@/components/panels/pipeline-diagram";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { usePipeline } from "@/hooks/use-pipeline";
import { useManualPipeline } from "@/hooks/use-pipeline";
import { usePipelineRuns } from "@/hooks/use-api";
import {
  imageUrl,
  getThemesWithColors,
  listBackgrounds,
  uploadBackground,
  deleteBackground,
  backgroundImageUrl,
  type ContentPackage,
  type ThemeWithColors,
  type BackgroundFile,
} from "@/lib/api";
import { useCharacterContext } from "@/contexts/character-context";
import { SOURCE_COLORS } from "@/lib/constants";

// ── Utility Components (preserved from original) ─────────────────────────────

function QualityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score < 0.4
      ? "bg-red-500"
      : score < 0.7
        ? "bg-yellow-500"
        : "bg-emerald-500";
  return (
    <div
      className="w-full h-1.5 rounded-full bg-secondary overflow-hidden"
      title={`Qualidade: ${pct}%`}
    >
      <div
        className={`h-full rounded-full ${color} transition-all`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function SourceBadge({ source }: { source?: string }) {
  if (!source) return null;
  const colors =
    SOURCE_COLORS[source] ??
    "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${colors}`}
    >
      {source}
    </span>
  );
}

function ContentDetailDialog({
  pkg,
  open,
  onOpenChange,
}: {
  pkg: ContentPackage | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  if (!pkg) return null;

  const filename = pkg.image_path.split(/[/\\]/).pop() ?? pkg.image_path;
  const meta = pkg.image_metadata;
  const fullCaption = [pkg.caption, pkg.hashtags].filter(Boolean).join("\n\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullCaption);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-[#1c1c22] border-white/10">
        <DialogHeader>
          <DialogTitle className="text-base">
            Detalhes do Conteudo
          </DialogTitle>
          <DialogDescription className="sr-only">
            Metadados e preview do conteudo gerado
          </DialogDescription>
        </DialogHeader>

        <div className="aspect-[4/5] overflow-hidden rounded-lg bg-secondary">
          <img
            src={imageUrl(filename)}
            alt={pkg.topic}
            className="h-full w-full object-cover"
          />
        </div>

        <p className="text-lg font-semibold leading-snug">{pkg.phrase}</p>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="text-[11px]">
            {pkg.topic}
          </Badge>
          <SourceBadge source={pkg.background_source} />
          {meta?.theme_key && (
            <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/20 text-amber-400 px-2 py-0.5 text-[10px] font-semibold">
              {meta.theme_key.replace(/_/g, " ")}
            </span>
          )}
        </div>

        {pkg.quality_score > 0 && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Qualidade</span>
              <span className="text-xs font-normal">
                {(pkg.quality_score * 100).toFixed(0)}%
              </span>
            </div>
            <QualityBar score={pkg.quality_score} />
          </div>
        )}

        {pkg.caption && (
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground font-normal">
              Caption
            </span>
            <div className="rounded-lg bg-secondary/50 p-3 text-sm max-h-32 overflow-y-auto whitespace-pre-wrap">
              {pkg.caption}
            </div>
          </div>
        )}

        {pkg.hashtags && (
          <div className="space-y-1.5">
            <span className="text-xs text-muted-foreground font-normal">
              Hashtags
            </span>
            <div className="flex flex-wrap gap-1.5">
              {pkg.hashtags
                .split(/\s+/)
                .filter(Boolean)
                .map((tag, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-normal"
                  >
                    {tag}
                  </span>
                ))}
            </div>
          </div>
        )}

        {meta && (
          <div className="space-y-3 rounded-lg border border-white/5 bg-secondary/30 p-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-semibold">
                Metadados da Imagem
              </span>
            </div>

            <div className="grid gap-2 text-sm">
              {meta.pose && (
                <div>
                  <span className="text-xs text-muted-foreground">
                    Pose / Acao
                  </span>
                  <p className="text-[13px]">{meta.pose}</p>
                </div>
              )}
              {meta.scene && (
                <div>
                  <span className="text-xs text-muted-foreground">
                    Cenario
                  </span>
                  <p className="text-[13px]">{meta.scene}</p>
                </div>
              )}
              {meta.theme_key && (
                <div>
                  <span className="text-xs text-muted-foreground">
                    Theme Key
                  </span>
                  <p className="text-[13px]">{meta.theme_key}</p>
                </div>
              )}
              {pkg.background_source && (
                <div>
                  <span className="text-xs text-muted-foreground">
                    Background Source
                  </span>
                  <div className="mt-0.5">
                    <SourceBadge source={pkg.background_source} />
                  </div>
                </div>
              )}
              {meta.rendering_config &&
                Object.keys(meta.rendering_config).length > 0 && (
                  <div>
                    <span className="text-xs text-muted-foreground">
                      Rendering Config
                    </span>
                    <div className="mt-1 rounded bg-secondary/50 p-2 text-[12px] font-mono space-y-0.5">
                      {Object.entries(meta.rendering_config).map(([k, v]) => (
                        <div key={k}>
                          <span className="text-muted-foreground">{k}:</span>{" "}
                          <span>{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              {meta.reference_images &&
                meta.reference_images.length > 0 && (
                  <div>
                    <span className="text-xs text-muted-foreground">
                      Imagens de referencia
                    </span>
                    <p className="text-[13px]">
                      {meta.reference_images.length} imagem(ns)
                    </p>
                  </div>
                )}
              <div className="flex flex-wrap gap-2 pt-1">
                {meta.phrase_context_used != null && (
                  <span
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                      meta.phrase_context_used
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                        : "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                    }`}
                  >
                    Contexto frase:{" "}
                    {meta.phrase_context_used ? "Sim" : "Nao"}
                  </span>
                )}
                {meta.character_dna_used != null && (
                  <span
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                      meta.character_dna_used
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                        : "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                    }`}
                  >
                    DNA personagem:{" "}
                    {meta.character_dna_used ? "Sim" : "Nao"}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {fullCaption && (
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-4 w-4 text-emerald-400" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
            {copied ? "Copiado!" : "Copiar Caption"}
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── MemeCard ──────────────────────────────────────────────────────────────────

function MemeCard({
  pkg,
  onApprove,
  onReject,
  onUnreject,
  onClick,
}: {
  pkg: ContentPackage;
  onApprove: () => void;
  onReject: () => void;
  onUnreject: () => void;
  onClick: () => void;
}) {
  const filename = pkg.image_path.split(/[/\\]/).pop() ?? pkg.image_path;
  const status = pkg.approval_status ?? "pending";
  const isApproved = status === "approved";
  const isRejected = status === "rejected";

  return (
    <Card
      className={`overflow-hidden transition-all duration-200 ${
        isApproved ? "border-l-[3px] border-l-emerald-500" : ""
      }`}
    >
      {/* Image */}
      <div
        className="relative cursor-pointer"
        onClick={onClick}
      >
        <img
          src={imageUrl(filename)}
          alt={pkg.topic}
          className={`w-full aspect-[4/5] object-cover rounded-t-lg transition-opacity ${
            isRejected ? "opacity-40" : ""
          }`}
        />
        {/* Status badges */}
        <div className="absolute top-2 left-2 flex flex-wrap gap-1">
          {isApproved && (
            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              aprovado
            </Badge>
          )}
          {isRejected && (
            <Badge
              className="bg-zinc-500/20 text-zinc-400 line-through cursor-pointer border-zinc-500/30"
              onClick={(e) => {
                e.stopPropagation();
                onUnreject();
              }}
            >
              rejeitado
            </Badge>
          )}
        </div>
      </div>

      <CardContent className="p-3 space-y-2">
        {/* Quality bar */}
        {pkg.quality_score > 0 && <QualityBar score={pkg.quality_score} />}

        {/* Phrase */}
        <p className="text-sm font-normal line-clamp-2">{pkg.phrase}</p>

        {/* Actions */}
        <div className="flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className={`min-w-[44px] min-h-[44px] ${
                    isApproved ? "text-emerald-500" : "hover:text-emerald-500"
                  }`}
                  aria-label="Aprovar meme"
                  onClick={() => onApprove()}
                >
                  <CheckCircle2 className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Aprovar meme</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className={`min-w-[44px] min-h-[44px] ${
                    isRejected ? "text-red-500" : "hover:text-red-500"
                  }`}
                  aria-label="Rejeitar meme"
                  onClick={() => onReject()}
                >
                  <X className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Rejeitar meme</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardContent>
    </Card>
  );
}

// ── ResultsGrid ───────────────────────────────────────────────────────────────

function ResultsGrid({
  results,
  isRunning,
  skeletonCount,
  onApprove,
  onReject,
  onUnreject,
  onBulkApprove,
  onBulkReject,
  onCardClick,
}: {
  results: ContentPackage[];
  isRunning: boolean;
  skeletonCount: number;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onUnreject: (id: number) => void;
  onBulkApprove: () => void;
  onBulkReject: () => void;
  onCardClick: (pkg: ContentPackage) => void;
}) {
  // Loading skeleton state
  if (isRunning && results.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-base font-semibold">Gerando memes...</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: skeletonCount }).map((_, i) => (
            <Card key={i} className="overflow-hidden">
              <Skeleton className="w-full aspect-[4/5]" />
              <CardContent className="p-3 space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
                <div className="flex gap-1">
                  <Skeleton className="h-10 w-10 rounded" />
                  <Skeleton className="h-10 w-10 rounded" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (!isRunning && results.length === 0) {
    return (
      <div className="text-center py-12 space-y-2">
        <Image className="h-12 w-12 mx-auto text-muted-foreground/50" />
        <h3 className="text-base font-semibold">
          Nenhum meme gerado ainda
        </h3>
        <p className="text-sm text-muted-foreground">
          Configure as opcoes acima e clique em &apos;Gerar Memes&apos; para
          comecar.
        </p>
      </div>
    );
  }

  // Results
  return (
    <div className="space-y-4">
      {/* Header with bulk actions */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">
          Memes Gerados ({results.length})
        </h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
            onClick={onBulkApprove}
          >
            Aprovar Todos
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-red-400 border-red-500/30 hover:bg-red-500/10"
            onClick={onBulkReject}
          >
            Rejeitar Todos
          </Button>
        </div>
      </div>

      {/* Grid */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        {results.map((pkg, i) => (
          <motion.div key={pkg.id ?? i} variants={staggerItem}>
            <MemeCard
              pkg={pkg}
              onApprove={() => pkg.id != null && onApprove(pkg.id)}
              onReject={() => pkg.id != null && onReject(pkg.id)}
              onUnreject={() => pkg.id != null && onUnreject(pkg.id)}
              onClick={() => onCardClick(pkg)}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

// ── ManualRunForm ─────────────────────────────────────────────────────────────

function ManualRunForm({
  isRunning,
  progress,
  error,
  onSubmit,
}: {
  isRunning: boolean;
  progress: number;
  error: string | null;
  onSubmit: (params: {
    input_mode: "topic" | "phrase";
    topic: string;
    phrases: string[];
    count: number;
    theme_key: string;
    background_image: string;
    enable_l5: boolean;
    use_gemini_image: boolean;
  }) => void;
}) {
  const { activeCharacter } = useCharacterContext();
  const characterSlug = activeCharacter?.slug ?? "mago-mestre";

  const [inputMode, setInputMode] = useState<"topic" | "phrase">("topic");
  const [topicValue, setTopicValue] = useState("");
  const [phraseValue, setPhraseValue] = useState("");
  const [count, setCount] = useState(3);
  const [themeKey, setThemeKey] = useState("sabedoria");
  const [backgroundImage, setBackgroundImage] = useState("");
  const [enableL5, setEnableL5] = useState(true);
  const [useGeminiImage, setUseGeminiImage] = useState(false);

  // Theme data
  const [themes, setThemes] = useState<ThemeWithColors[]>([]);
  const [backgrounds, setBackgrounds] = useState<BackgroundFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load themes on mount
  useEffect(() => {
    getThemesWithColors()
      .then((r) => setThemes(r.themes))
      .catch(() => {});
  }, []);

  // Load backgrounds on mount and when character changes
  useEffect(() => {
    if (characterSlug) {
      listBackgrounds(characterSlug)
        .then((r) => setBackgrounds(r.backgrounds))
        .catch(() => setBackgrounds([]));
    }
  }, [characterSlug]);

  const handleUpload = async (file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      alert("Arquivo excede o limite de 5MB.");
      return;
    }
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(file.type)) {
      alert("Formato nao suportado. Use JPG, PNG ou WebP.");
      return;
    }
    try {
      await uploadBackground(file, characterSlug);
      // Refresh backgrounds list
      const r = await listBackgrounds(characterSlug);
      setBackgrounds(r.backgrounds);
    } catch {
      // Silently handle
    }
  };

  const handleRemoveBackground = async (filename: string) => {
    try {
      await deleteBackground(filename, characterSlug);
      if (backgroundImage === filename) setBackgroundImage("");
      const r = await listBackgrounds(characterSlug);
      setBackgrounds(r.backgrounds);
    } catch {
      // Silently handle
    }
  };

  const handleSubmit = () => {
    onSubmit({
      input_mode: inputMode,
      topic: topicValue,
      phrases: phraseValue
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean),
      count,
      theme_key: themeKey,
      background_image: backgroundImage,
      enable_l5: enableL5,
      use_gemini_image: useGeminiImage,
    });
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Pipeline Manual
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Input Mode Tabs */}
        <Tabs
          value={inputMode}
          onValueChange={(v) => setInputMode(v as "topic" | "phrase")}
        >
          <TabsList className="w-full">
            <TabsTrigger value="topic" className="flex-1 font-semibold">
              Gerar do tema
            </TabsTrigger>
            <TabsTrigger value="phrase" className="flex-1 font-semibold">
              Usar minha frase
            </TabsTrigger>
          </TabsList>
          <TabsContent value="topic" className="mt-3">
            <Input
              placeholder="Ex: segunda-feira, cafe, namoro..."
              value={topicValue}
              onChange={(e) => setTopicValue(e.target.value)}
              className="font-normal"
            />
          </TabsContent>
          <TabsContent value="phrase" className="mt-3">
            <Textarea
              placeholder="Uma frase por linha... (cada linha vira um meme)"
              value={phraseValue}
              onChange={(e) => setPhraseValue(e.target.value)}
              rows={4}
              className="font-normal"
            />
          </TabsContent>
        </Tabs>

        {/* Theme Select */}
        <div className="space-y-2">
          <label className="text-sm font-normal text-muted-foreground">
            Tema
          </label>
          <Select value={themeKey} onValueChange={(v) => { setThemeKey(v); setBackgroundImage(""); }}>
            <SelectTrigger>
              <SelectValue placeholder="Selecionar tema..." />
            </SelectTrigger>
            <SelectContent>
              {themes.map((t) => (
                <SelectItem key={t.key} value={t.key}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Background Image Picker */}
        {(
          <div className="space-y-2">
            <label className="text-sm font-normal text-muted-foreground">
              Background image
            </label>
            <ScrollArea className="w-full whitespace-nowrap">
              <div className="flex gap-2 pb-2">
                {backgrounds.map((bg) => (
                  <div key={bg.filename} className="relative shrink-0 group">
                    <button
                      type="button"
                      onClick={() => setBackgroundImage(bg.filename)}
                      className={`block rounded overflow-hidden transition-all ${
                        backgroundImage === bg.filename
                          ? "border-2 border-[#8B5CF6] scale-105"
                          : "border border-white/10 hover:border-white/20"
                      }`}
                    >
                      <img
                        src={backgroundImageUrl(bg.filename, characterSlug)}
                        alt={bg.filename}
                        className="w-16 h-20 object-cover"
                      />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleRemoveBackground(bg.filename); }}
                      className="absolute top-0.5 right-0.5 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-black/70 hover:bg-red-600 transition-colors"
                    >
                      <X className="w-3 h-3 text-white" />
                    </button>
                  </div>
                ))}
                {/* Upload button */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        className="shrink-0 w-16 h-20"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <Plus className="h-5 w-5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Adicionar background</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                    e.target.value = "";
                  }}
                />
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </div>
        )}

        {/* Meme Count */}
        <div className="space-y-2">
          <label className="text-sm font-normal text-muted-foreground">
            Quantidade de memes
          </label>
          <Input
            type="number"
            min={1}
            max={10}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="font-normal"
          />
        </div>

        {/* Gemini Image Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={useGeminiImage}
            onChange={(e) => setUseGeminiImage(e.target.checked)}
            className="h-4 w-4 rounded accent-[#8B5CF6]"
          />
          <div className="text-sm font-normal">
            Gerar background via Gemini
            <span className="text-muted-foreground text-xs ml-1">(consome API)</span>
          </div>
        </label>

        {/* L5 Toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={enableL5}
            onChange={(e) => setEnableL5(e.target.checked)}
            className="h-4 w-4 rounded accent-[#8B5CF6]"
          />
          <span className="text-sm font-normal">
            Gerar caption e hashtags
          </span>
        </label>

        {/* Submit CTA */}
        <Button
          onClick={handleSubmit}
          disabled={isRunning}
          className={`w-full gap-2 font-semibold bg-[#8B5CF6] hover:bg-[#7C3AED] text-white ${
            isRunning ? "pulse-glow" : ""
          }`}
        >
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isRunning ? "Gerando..." : "Gerar Memes"}
        </Button>

        {/* Progress bar */}
        {isRunning && (
          <div className="space-y-1">
            <Progress value={progress} />
            <p className="text-[10px] text-muted-foreground text-right">
              {progress}%
            </p>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg p-3">
            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
            Erro ao gerar memes: {error}. Tente novamente ou verifique os
            logs.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  return (
    <Suspense fallback={null}>
      <PipelinePageInner />
    </Suspense>
  );
}

function PipelinePageInner() {
  const searchParams = useSearchParams();
  const { activeCharacter } = useCharacterContext();
  const characterSlug = activeCharacter?.slug ?? "mago-mestre";

  const pipeline = usePipeline();
  const manualPipeline = useManualPipeline();
  const { data: runs } = usePipelineRuns();
  const runEntries = runs?.runs ?? [];

  const [selectedPkg, setSelectedPkg] = useState<ContentPackage | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const handleCardClick = (pkg: ContentPackage) => {
    setSelectedPkg(pkg);
    setDetailOpen(true);
  };

  const handleSubmit = (params: {
    input_mode: "topic" | "phrase";
    topic: string;
    phrases: string[];
    count: number;
    theme_key: string;
    background_image: string;
    enable_l5: boolean;
    use_gemini_image: boolean;
  }) => {
    manualPipeline.run({
      input_mode: params.input_mode,
      topic: params.topic,
      phrases: params.phrases,
      count: params.count,
      theme_key: params.theme_key,
      background_type: "image",
      background_color: "",
      background_image: params.background_image,
      layout: "bottom",
      enable_l5: params.enable_l5,
      use_gemini_image: params.use_gemini_image,
      character_slug: characterSlug,
    });
  };

  return (
    <div className="space-y-6">
      {/* Pipeline Diagram */}
      <div className="rounded-[14px] overflow-hidden border border-border/50">
        <PipelineDiagram
          layers={pipeline.status?.layers}
          currentLayer={pipeline.status?.current_layer}
          pipelineStatus={pipeline.status}
          isRunning={pipeline.isRunning}
        />
      </div>

      {/* Form + History Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Manual Run Form */}
        <ManualRunForm
          isRunning={manualPipeline.isRunning}
          progress={manualPipeline.progress}
          error={manualPipeline.error}
          onSubmit={handleSubmit}
        />

        {/* Execucoes Anteriores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <List className="h-4 w-4" />
              Execucoes Anteriores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {runEntries.length > 0 ? (
              <motion.div
                className="space-y-2 max-h-80 overflow-auto"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
              >
                {runEntries.map((info) => (
                  <motion.div
                    key={info.run_id}
                    className="flex items-center justify-between rounded-lg bg-secondary/50 px-3 py-2 transition-colors duration-200 hover:bg-secondary/70"
                    variants={staggerItem}
                  >
                    <div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {info.run_id}
                      </span>
                      <span className="text-xs text-muted-foreground ml-2">
                        ({info.packages_produced} pacotes)
                      </span>
                    </div>
                    <Badge
                      variant={
                        info.status === "completed" ? "success" : "secondary"
                      }
                    >
                      {info.status}
                    </Badge>
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Nenhuma execucao registrada
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Results Grid */}
      <ResultsGrid
        results={manualPipeline.results}
        isRunning={manualPipeline.isRunning}
        skeletonCount={3}
        onApprove={manualPipeline.approve}
        onReject={manualPipeline.reject}
        onUnreject={manualPipeline.unreject}
        onBulkApprove={manualPipeline.bulkApprove}
        onBulkReject={manualPipeline.bulkReject}
        onCardClick={handleCardClick}
      />

      {/* Detail Dialog */}
      <ContentDetailDialog
        pkg={selectedPkg}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
