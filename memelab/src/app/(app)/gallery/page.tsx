"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Wand2, RotateCcw, Sparkles, Loader2, CheckCircle2, Video, DollarSign, Package } from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { SOURCE_COLORS } from "@/lib/constants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { IndeterminateProgress } from "@/components/ui/progress";
import { useDriveImages, useDriveThemes, useThemes, useContentPackages, useVideoBudget, useVideoStatus } from "@/hooks/use-api";
import {
  imageUrl,
  composeMeme,
  generateSingle,
  refineImage,
  generateVideo,
  type ImageInfo,
  type ContentPackageDB,
} from "@/lib/api";

function inferSource(filename: string): string {
  const f = filename.toLowerCase();
  if (f.includes("gemini")) return "gemini";
  if (f.includes("comfyui") || f.includes("flux")) return "comfyui";
  return "static";
}

export default function GalleryPage() {
  const [themeFilter, setThemeFilter] = useState<string>("");
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<"" | "background" | "meme">("");
  const [page, setPage] = useState(0);
  const limit = 12;

  const { data: driveData, isLoading, mutate: mutateDrive } = useDriveImages({
    theme: themeFilter || undefined,
    category: categoryFilter || undefined,
    limit,
    offset: page * limit,
  });
  const { data: driveThemesData } = useDriveThemes();
  const { data: themesData } = useThemes();

  const rawImages = driveData?.images ?? [];
  const images = sourceFilter
    ? rawImages.filter((img) => inferSource(img.filename) === sourceFilter)
    : rawImages;
  const totalImages = driveData?.total ?? 0;

  // Compose dialog
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [composePhrase, setComposePhrase] = useState("");
  const [composeSituacao, setComposeSituacao] = useState("");
  const [composeRefine, setComposeRefine] = useState(false);
  const [composePasses, setComposePasses] = useState(1);
  const [composing, setComposing] = useState(false);
  const [composeResult, setComposeResult] = useState<string | null>(null);
  const [composeError, setComposeError] = useState<string | null>(null);
  const [composeStep, setComposeStep] = useState("");

  // Single generation dialog
  const [showGenerate, setShowGenerate] = useState(false);
  const [genTheme, setGenTheme] = useState("");
  const [genAcao, setGenAcao] = useState("");
  const [genCenario, setGenCenario] = useState("");
  const [genRefine, setGenRefine] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  // Refine dialog
  const [refineTarget, setRefineTarget] = useState<string | null>(null);
  const [refineInstrucao, setRefineInstrucao] = useState("");
  const [refinePasses, setRefinePasses] = useState(1);
  const [refining, setRefining] = useState(false);
  const [refineResult, setRefineResult] = useState<string | null>(null);
  const [refineError, setRefineError] = useState<string | null>(null);

  // Content packages + video generation
  const { data: contentData, mutate: mutateContent } = useContentPackages(50);
  const [videoTarget, setVideoTarget] = useState<ContentPackageDB | null>(null);
  const [videoDuration, setVideoDuration] = useState<10 | 15>(10);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoSuccess, setVideoSuccess] = useState(false);
  const { data: budgetData } = useVideoBudget();
  const { data: pollingStatus } = useVideoStatus(videoTarget?.id ?? null, videoGenerating);

  if (videoGenerating && pollingStatus?.video_status && pollingStatus.video_status !== "generating") {
    setVideoGenerating(false);
    if (pollingStatus.video_status === "success") {
      setVideoSuccess(true);
      mutateContent();
    } else {
      setVideoError("Geracao de video falhou");
    }
  }

  const handleGenerateVideo = async () => {
    if (!videoTarget) return;
    setVideoGenerating(true);
    setVideoError(null);
    setVideoSuccess(false);
    try {
      await generateVideo({ content_package_id: videoTarget.id, duration: videoDuration });
    } catch (err) {
      setVideoGenerating(false);
      setVideoError(err instanceof Error ? err.message : "Erro ao gerar video");
    }
  };

  const allPackages = contentData?.packages ?? [];

  const driveThemeList = driveThemesData?.themes ?? [];
  const situacaoThemes = themesData?.themes ?? [];

  const handleCompose = async () => {
    if (!composePhrase.trim()) return;
    setComposing(true);
    setComposeResult(null);
    setComposeError(null);
    setComposeStep("Compondo imagem com a frase...");
    try {
      const result = await composeMeme({
        phrase: composePhrase,
        background_filename: selectedImage || undefined,
        situacao: composeSituacao || undefined,
        auto_refine: composeRefine,
        refinement_passes: composePasses,
        use_phrase_context: !selectedImage,
      });
      if (result.success && result.image_path) {
        const filename = result.image_path.split(/[/\\]/).pop() ?? result.image_path;
        setComposeResult(filename);
        setComposeStep("");
        mutateDrive();
      } else {
        setComposeError("Falha ao gerar imagem");
        setComposeStep("");
      }
    } catch (err) {
      setComposeError(err instanceof Error ? err.message : "Erro ao compor");
      setComposeStep("");
    } finally {
      setComposing(false);
    }
  };

  const handleGenSingle = async () => {
    if (!genTheme) return;
    setGenerating(true);
    setGenResult(null);
    setGenError(null);
    try {
      const result = await generateSingle({
        theme_key: genTheme,
        acao_custom: genAcao || undefined,
        cenario_custom: genCenario || undefined,
        auto_refine: genRefine,
      });
      if (result.success) {
        setGenResult(result.file);
        mutateDrive();
      } else {
        setGenError("Falha ao gerar");
      }
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Erro ao gerar");
    } finally {
      setGenerating(false);
    }
  };

  const handleRefine = async () => {
    if (!refineTarget || !refineInstrucao.trim()) return;
    setRefining(true);
    setRefineResult(null);
    setRefineError(null);
    try {
      const result = await refineImage({
        filename: refineTarget,
        instrucao: refineInstrucao,
        passes: refinePasses,
      });
      if (result.success && result.final_file) {
        setRefineResult(result.final_file);
        mutateDrive();
      } else {
        setRefineError("Falha no refinamento");
      }
    } catch (err) {
      setRefineError(err instanceof Error ? err.message : "Erro ao refinar");
    } finally {
      setRefining(false);
    }
  };

  const hasMore = images.length >= limit && (page + 1) * limit < totalImages;

  return (
    <div className="space-y-6">
      {/* Filters + Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={themeFilter || "all"} onValueChange={(v) => { setThemeFilter(v === "all" ? "" : v); setPage(0); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filtrar por tema" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os temas</SelectItem>
            {driveThemeList.map((t) => (
              <SelectItem key={t} value={t}>
                {t} {driveThemesData?.counts[t] != null && `(${driveThemesData.counts[t]})`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sourceFilter || "all"} onValueChange={(v) => { setSourceFilter(v === "all" ? "" : v); setPage(0); }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filtrar por fonte" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as fontes</SelectItem>
            <SelectItem value="gemini">Gemini</SelectItem>
            <SelectItem value="comfyui">ComfyUI</SelectItem>
            <SelectItem value="static">Estatico</SelectItem>
          </SelectContent>
        </Select>

        <Select value={categoryFilter || "all"} onValueChange={(v) => { setCategoryFilter(v === "all" ? "" : v as "" | "background" | "meme"); setPage(0); }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            <SelectItem value="background">Backgrounds</SelectItem>
            <SelectItem value="meme">Memes prontos</SelectItem>
          </SelectContent>
        </Select>

        <Badge variant="secondary" className="text-xs">
          {totalImages} imagens
        </Badge>

        <Button variant="outline" size="sm" onClick={() => setShowGenerate(true)} className="gap-2">
          <Sparkles className="h-3.5 w-3.5" />
          Gerar Background
        </Button>

        <div className="flex items-center gap-2 ml-auto">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
            Anterior
          </Button>
          <span className="text-sm text-muted-foreground">Pagina {page + 1}</span>
          <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={!hasMore}>
            Proxima
          </Button>
        </div>
      </div>

      {/* Image Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-[4/5] rounded-xl" />
          ))}
        </div>
      ) : images.length > 0 ? (
        <motion.div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4" variants={staggerContainer} initial="initial" animate="animate">
          {images.map((img: ImageInfo) => (
            <motion.div
              key={img.filename}
              className="group relative aspect-[4/5] overflow-hidden rounded-xl border bg-secondary cursor-pointer transition-all duration-200 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
              variants={staggerItem}
              whileHover={{ y: -4 }}
              onClick={() => setPreviewImage(img.filename)}
            >
              <img
                src={imageUrl(img.filename)}
                alt={img.filename}
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
              <div className="absolute top-2 left-2 flex gap-1">
                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold backdrop-blur-sm ${SOURCE_COLORS[inferSource(img.filename)] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"}`}>
                  {inferSource(img.filename)}
                </span>
                {img.category === "meme" && (
                  <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold backdrop-blur-sm bg-amber-500/20 text-amber-400 border-amber-500/30">
                    meme
                  </span>
                )}
              </div>
              <div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 transition-all duration-200 group-hover:opacity-100">
                <div className="flex w-full items-center justify-between p-3">
                  <div className="min-w-0">
                    <p className="truncate text-xs text-white/80">{img.filename}</p>
                    <p className="text-[10px] text-white/50">{img.theme} | {img.size_kb.toFixed(0)}kb</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    {img.category !== "meme" && (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 text-xs"
                          onClick={(e) => { e.stopPropagation(); setRefineTarget(img.filename); }}
                        >
                          <RotateCcw className="mr-1 h-3 w-3" /> Refinar
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 text-xs"
                          onClick={(e) => { e.stopPropagation(); setSelectedImage(img.filename); }}
                        >
                          <Wand2 className="mr-1 h-3 w-3" /> Compor
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">Nenhuma imagem encontrada</p>
          </CardContent>
        </Card>
      )}

      {/* Preview Dialog */}
      <Dialog open={!!previewImage} onOpenChange={() => setPreviewImage(null)}>
        <DialogContent className="max-w-3xl p-0 overflow-hidden">
          {previewImage && (
            <img src={imageUrl(previewImage)} alt={previewImage} className="w-full animate-fade-in" />
          )}
        </DialogContent>
      </Dialog>

      {/* Compose Dialog */}
      <Dialog open={!!selectedImage} onOpenChange={() => { setSelectedImage(null); setComposeResult(null); setComposeError(null); setComposeStep(""); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Compor Meme</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="aspect-[4/5] overflow-hidden rounded-xl bg-secondary relative">
              {(composeResult || selectedImage) && (
                <img
                  src={imageUrl(composeResult ?? selectedImage ?? "")}
                  alt="Preview"
                  className="h-full w-full object-cover transition-opacity duration-300"
                  key={composeResult ?? selectedImage}
                />
              )}
              {composing && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="mt-2 text-sm text-white/80">Compondo...</p>
                </div>
              )}
              {composeResult && !composing && (
                <div className="absolute top-3 right-3 animate-fade-in">
                  <div className="flex items-center gap-1 rounded-full bg-emerald-500/90 px-2.5 py-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-white" />
                    <span className="text-xs font-medium text-white">Pronto</span>
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Frase</label>
                <Textarea
                  placeholder="Digite a frase do meme..."
                  value={composePhrase}
                  onChange={(e) => setComposePhrase(e.target.value)}
                  rows={4}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Situacao (opcional)</label>
                <Select value={composeSituacao || "auto"} onValueChange={(v) => setComposeSituacao(v === "auto" ? "" : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecionar situacao" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Automatico</SelectItem>
                    {situacaoThemes.map((t) => (
                      <SelectItem key={t.key} value={t.key}>{t.label || t.key}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={composeRefine}
                    onChange={(e) => setComposeRefine(e.target.checked)}
                    className="h-4 w-4 rounded accent-primary"
                  />
                  <span className="text-sm">Auto-refinar</span>
                </label>
                {composeRefine && (
                  <Input
                    type="number"
                    min={1}
                    max={3}
                    value={composePasses}
                    onChange={(e) => setComposePasses(Number(e.target.value))}
                    className="w-16"
                  />
                )}
              </div>
              <Button
                onClick={handleCompose}
                disabled={composing || !composePhrase.trim()}
                className={`w-full gap-2 ${composing ? "pulse-glow" : ""}`}
              >
                {composing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )}
                {composing ? "Gerando..." : "Gerar Meme"}
              </Button>
              {composing && (
                <div className="space-y-2 animate-fade-in">
                  <IndeterminateProgress />
                  <p className="text-xs text-muted-foreground text-center">{composeStep}</p>
                </div>
              )}
              {composeResult && !composing && (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-emerald-400">Imagem gerada com sucesso!</p>
                </div>
              )}
              {composeError && (
                <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                  <div className="h-2 w-2 rounded-full bg-destructive" />
                  <p className="text-sm text-destructive">{composeError}</p>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Single Generation Dialog */}
      <Dialog open={showGenerate} onOpenChange={() => { setShowGenerate(false); setGenResult(null); setGenError(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Gerar Background</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Tema</label>
              <Select value={genTheme || "none"} onValueChange={(v) => setGenTheme(v === "none" ? "" : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecionar tema" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Selecionar...</SelectItem>
                  {situacaoThemes.map((t) => (
                    <SelectItem key={t.key} value={t.key}>{t.label || t.key}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Acao custom (opcional, English)</label>
              <Textarea placeholder="Override da acao do tema..." value={genAcao} onChange={(e) => setGenAcao(e.target.value)} rows={2} />
            </div>
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">Cenario custom (opcional, English)</label>
              <Textarea placeholder="Override do cenario..." value={genCenario} onChange={(e) => setGenCenario(e.target.value)} rows={2} />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={genRefine} onChange={(e) => setGenRefine(e.target.checked)} className="h-4 w-4 rounded accent-primary" />
              <span className="text-sm">Auto-refinar</span>
            </label>
            <Button onClick={handleGenSingle} disabled={generating || !genTheme} className={`w-full gap-2 ${generating ? "pulse-glow" : ""}`}>
              {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {generating ? "Gerando..." : "Gerar Background"}
            </Button>
            {generating && (
              <div className="space-y-2 animate-fade-in">
                <IndeterminateProgress />
                <p className="text-xs text-muted-foreground text-center">Gerando background via Gemini...</p>
              </div>
            )}
            {genResult && (
              <div className="space-y-2 animate-fade-in">
                <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-emerald-400">Background gerado!</p>
                </div>
                <div className="aspect-[4/5] overflow-hidden rounded-xl bg-secondary">
                  <img src={imageUrl(genResult)} alt="Generated" className="h-full w-full object-cover" />
                </div>
              </div>
            )}
            {genError && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                <div className="h-2 w-2 rounded-full bg-destructive" />
                <p className="text-sm text-destructive">{genError}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Refine Dialog */}
      <Dialog open={!!refineTarget} onOpenChange={() => { setRefineTarget(null); setRefineResult(null); setRefineError(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Refinar Imagem</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="aspect-[4/5] overflow-hidden rounded-xl bg-secondary relative">
              {(refineResult || refineTarget) && (
                <img src={imageUrl(refineResult ?? refineTarget ?? "")} alt="Refine preview" className="h-full w-full object-cover transition-opacity duration-300" key={refineResult ?? refineTarget} />
              )}
              {refining && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="mt-2 text-sm text-white/80">Refinando...</p>
                </div>
              )}
            </div>
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground font-mono">{refineTarget}</p>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Instrucao de refinamento (English)</label>
                <Textarea placeholder="Make the wizard more dramatic, add magical particles..." value={refineInstrucao} onChange={(e) => setRefineInstrucao(e.target.value)} rows={3} />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Passes</label>
                <Input type="number" min={1} max={3} value={refinePasses} onChange={(e) => setRefinePasses(Number(e.target.value))} />
              </div>
              <Button onClick={handleRefine} disabled={refining || !refineInstrucao.trim()} className={`w-full gap-2 ${refining ? "pulse-glow" : ""}`}>
                {refining ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                {refining ? "Refinando..." : "Refinar"}
              </Button>
              {refining && (
                <div className="space-y-2 animate-fade-in">
                  <IndeterminateProgress />
                  <p className="text-xs text-muted-foreground text-center">Processando refinamento...</p>
                </div>
              )}
              {refineResult && (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-emerald-400">Refinamento concluido!</p>
                </div>
              )}
              {refineError && (
                <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                  <div className="h-2 w-2 rounded-full bg-destructive" />
                  <p className="text-sm text-destructive">{refineError}</p>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Conteudo Aprovado — Video Generation */}
      {allPackages.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Package className="h-4 w-4 text-primary" />
              Conteudo Gerado
              <Badge variant="secondary" className="text-xs ml-auto">{allPackages.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <motion.div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4" variants={staggerContainer} initial="initial" animate="animate">
              {allPackages.map((pkg) => {
                const filename = pkg.image_path.split(/[/\\]/).pop() ?? "";
                return (
                  <motion.div
                    key={pkg.id}
                    className="group relative overflow-hidden rounded-xl border bg-secondary"
                    variants={staggerItem}
                  >
                    <div className="relative aspect-[4/5] overflow-hidden">
                      <img src={imageUrl(filename)} alt={pkg.phrase} className="h-full w-full object-cover" />
                      {/* Video status badge */}
                      {pkg.video_status && (
                        <div className="absolute top-2 right-2">
                          <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-sm ${
                            pkg.video_status === "generating" ? "bg-amber-500/80 animate-pulse"
                            : pkg.video_status === "success" ? "bg-cyan-500/80"
                            : pkg.video_status === "failed" ? "bg-rose-500/80"
                            : "bg-zinc-500/80"
                          }`}>
                            <Video className="h-2.5 w-2.5" />
                            {pkg.video_status === "generating" ? "Gerando..." : pkg.video_status === "success" ? "Video pronto" : pkg.video_status === "failed" ? "Falhou" : pkg.video_status}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="p-2.5 space-y-2">
                      <p className="line-clamp-2 text-xs leading-snug">{pkg.phrase}</p>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground">{pkg.topic}</span>
                        <span className="text-[10px] text-muted-foreground tabular-nums">{(pkg.quality_score * 100).toFixed(0)}%</span>
                      </div>
                      {/* Video action button */}
                      {!pkg.video_status ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className={`w-full h-7 text-xs gap-1 ${pkg.approval_status !== "approved" ? "opacity-60" : ""}`}
                          onClick={() => {
                            if (pkg.approval_status !== "approved") {
                              setVideoTarget(pkg);
                              setVideoError("Aprove o conteudo antes de gerar video");
                              setVideoSuccess(false);
                              return;
                            }
                            setVideoTarget(pkg);
                            setVideoError(null);
                            setVideoSuccess(false);
                            setVideoDuration(10);
                          }}
                        >
                          <Video className="h-3 w-3" />
                          Gerar Video
                        </Button>
                      ) : pkg.video_status === "generating" ? (
                        <div className="flex items-center justify-center gap-1 h-7 text-xs text-amber-400">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Gerando...
                        </div>
                      ) : pkg.video_status === "failed" ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="w-full h-7 text-xs gap-1 text-rose-400 border-rose-500/20"
                          onClick={() => {
                            setVideoTarget(pkg);
                            setVideoError(null);
                            setVideoSuccess(false);
                            setVideoDuration(10);
                          }}
                        >
                          <Video className="h-3 w-3" />
                          Tentar novamente
                        </Button>
                      ) : null}
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          </CardContent>
        </Card>
      )}

      {/* Video Generation Dialog */}
      <Dialog
        open={!!videoTarget}
        onOpenChange={() => { if (!videoGenerating) { setVideoTarget(null); setVideoError(null); setVideoSuccess(false); } }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Video className="h-4 w-4 text-primary" />
              Gerar Video
            </DialogTitle>
          </DialogHeader>
          {videoTarget && (
            <div className="space-y-4">
              <div className="flex gap-3 items-start">
                <div className="w-20 aspect-[4/5] overflow-hidden rounded-lg bg-secondary shrink-0">
                  <img src={imageUrl(videoTarget.image_path.split(/[/\\]/).pop() ?? "")} alt={videoTarget.phrase} className="h-full w-full object-cover" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm line-clamp-2">{videoTarget.phrase}</p>
                  <p className="text-xs text-muted-foreground mt-1">{videoTarget.topic}</p>
                </div>
              </div>
              {budgetData && (
                <div className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Orcamento hoje</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-medium tabular-nums">${budgetData.remaining_usd.toFixed(2)} restante</span>
                    <span className="text-[10px] text-muted-foreground ml-1">(~{budgetData.videos_remaining_estimate} videos)</span>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Duracao</label>
                <div className="flex gap-2">
                  <Button variant={videoDuration === 10 ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setVideoDuration(10)} disabled={videoGenerating}>10s — $0.15</Button>
                  <Button variant={videoDuration === 15 ? "default" : "outline"} size="sm" className="flex-1" onClick={() => setVideoDuration(15)} disabled={videoGenerating}>15s — $0.23</Button>
                </div>
              </div>
              <Button onClick={handleGenerateVideo} disabled={videoGenerating || videoSuccess} className={`w-full gap-2 ${videoGenerating ? "pulse-glow" : ""}`}>
                {videoGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : videoSuccess ? <CheckCircle2 className="h-4 w-4" /> : <Video className="h-4 w-4" />}
                {videoGenerating ? "Gerando video..." : videoSuccess ? "Video gerado!" : "Gerar Video"}
              </Button>
              {videoGenerating && (
                <div className="space-y-2 animate-fade-in">
                  <IndeterminateProgress />
                  <p className="text-xs text-muted-foreground text-center">Processando via Kie.ai Sora 2 (30-120s)...</p>
                </div>
              )}
              {videoSuccess && (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-emerald-400">Video gerado com sucesso!</p>
                </div>
              )}
              {videoError && (
                <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
                  <div className="h-2 w-2 rounded-full bg-destructive" />
                  <p className="text-sm text-destructive">{videoError}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
