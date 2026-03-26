"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Palette, Plus, Trash2, Sparkles, Wand2, RefreshCw, Loader2, CheckCircle2 } from "lucide-react";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { IndeterminateProgress } from "@/components/ui/progress";
import { useThemes } from "@/hooks/use-api";
import {
  addTheme,
  deleteTheme,
  generateThemes,
  enhanceTheme,
  type ThemeInfo,
  type EnhanceResponse,
} from "@/lib/api";

export default function ThemesPage() {
  const { data: themesData, isLoading, mutate } = useThemes();
  const themes = themesData?.themes ?? [];

  const [showAdd, setShowAdd] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newAcao, setNewAcao] = useState("");
  const [newCenario, setNewCenario] = useState("");
  const [adding, setAdding] = useState(false);

  const [enhanceInput, setEnhanceInput] = useState("");
  const [enhancing, setEnhancing] = useState(false);
  const [enhanceResult, setEnhanceResult] = useState<EnhanceResponse | null>(null);

  const [generating, setGenerating] = useState(false);
  const [genCount, setGenCount] = useState(5);
  const [genSuccess, setGenSuccess] = useState<string | null>(null);

  const [selectedTheme, setSelectedTheme] = useState<ThemeInfo | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!newKey.trim()) return;
    setAdding(true);
    try {
      await addTheme({
        key: newKey.trim(),
        label: newLabel.trim() || newKey.trim(),
        acao: newAcao.trim() || undefined,
        cenario: newCenario.trim() || undefined,
        count: 1,
      });
      mutate();
      setShowAdd(false);
      setNewKey(""); setNewLabel(""); setNewAcao(""); setNewCenario("");
    } catch {
      // handle silently
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (key: string) => {
    setDeleting(key);
    try {
      await deleteTheme(key);
      mutate();
    } catch {
      // handle silently
    } finally {
      setDeleting(null);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setGenSuccess(null);
    try {
      const result = await generateThemes({ count: genCount, save_to_db: true });
      setGenSuccess(`${result.generated} temas gerados e salvos`);
      mutate();
    } catch {
      // handle silently
    } finally {
      setGenerating(false);
    }
  };

  const handleEnhance = async () => {
    if (!enhanceInput.trim()) return;
    setEnhancing(true);
    setEnhanceResult(null);
    try {
      const result = await enhanceTheme(enhanceInput, true);
      setEnhanceResult(result);
      mutate();
    } catch {
      // handle silently
    } finally {
      setEnhancing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Temas Visuais</h2>
          <p className="text-sm text-muted-foreground">
            {themesData?.total ?? themes.length} temas
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => mutate()} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Atualizar
          </Button>
          <Button size="sm" onClick={() => setShowAdd(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Novo Tema
          </Button>
        </div>
      </div>

      {/* AI Tools */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wand2 className="h-4 w-4 text-primary" />
              Enhance (IA)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="Ex: mago cozinhando sopa magica..."
                value={enhanceInput}
                onChange={(e) => setEnhanceInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleEnhance()}
              />
              <Button
                onClick={handleEnhance}
                disabled={enhancing || !enhanceInput.trim()}
                className={`gap-2 shrink-0 ${enhancing ? "pulse-glow" : ""}`}
              >
                {enhancing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                {enhancing ? "..." : "Enhance"}
              </Button>
            </div>
            {enhancing && <IndeterminateProgress />}
            {enhanceResult && (
              <div className="rounded-xl bg-secondary/50 p-3 space-y-1 text-sm animate-fade-in">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <p className="font-medium">{enhanceResult.enhanced_theme.label}</p>
                </div>
                <p className="text-xs text-muted-foreground">{enhanceResult.enhanced_theme.acao}</p>
                <p className="text-xs text-muted-foreground">{enhanceResult.enhanced_theme.cenario}</p>
                <Badge variant="secondary" className="text-[10px] mt-1">
                  {enhanceResult.saved_to_db ? "Salvo" : "Nao salvo"}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              Gerar Temas (IA)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input type="number" min={1} max={20} value={genCount} onChange={(e) => setGenCount(Number(e.target.value))} className="w-20" />
              <Button
                onClick={handleGenerate}
                disabled={generating}
                className={`gap-2 flex-1 ${generating ? "pulse-glow" : ""}`}
              >
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {generating ? "Gerando..." : `Gerar ${genCount} Temas`}
              </Button>
            </div>
            {generating && <IndeterminateProgress />}
            {genSuccess && (
              <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 animate-fade-in">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <p className="text-sm text-emerald-400">{genSuccess}</p>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Usa Gemini para criar temas visuais diversos e salvar no banco de dados
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Theme Grid */}
      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
      ) : themes.length > 0 ? (
        <motion.div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" variants={staggerContainer} initial="initial" animate="animate">
          {themes.map((theme) => (
            <motion.div key={theme.key} variants={staggerItem} whileHover={{ y: -3 }}>
            <Card
              className="group cursor-pointer transition-all duration-200 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
              onClick={() => setSelectedTheme(theme)}
            >
              <CardContent className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Palette className="h-4 w-4 text-primary shrink-0" />
                    <h3 className="text-sm font-medium">{theme.label || theme.key}</h3>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => { e.stopPropagation(); handleDelete(theme.key); }}
                    disabled={deleting === theme.key}
                  >
                    {deleting === theme.key ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-destructive" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    )}
                  </Button>
                </div>
                <Badge variant="secondary" className="text-[10px]">{theme.key}</Badge>
                {theme.acao && (
                  <p className="text-xs text-muted-foreground line-clamp-2">{theme.acao}</p>
                )}
              </CardContent>
            </Card>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Palette className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">Nenhum tema encontrado</p>
          </CardContent>
        </Card>
      )}

      {/* Add Theme Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo Tema</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Key</label>
                <Input placeholder="mago_cozinhando" value={newKey} onChange={(e) => setNewKey(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Label</label>
                <Input placeholder="Mago Cozinhando" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Acao (English)</label>
              <Textarea placeholder="The wizard stirs a magical cauldron..." value={newAcao} onChange={(e) => setNewAcao(e.target.value)} rows={2} />
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Cenario (English)</label>
              <Textarea placeholder="A mystical kitchen with stone walls..." value={newCenario} onChange={(e) => setNewCenario(e.target.value)} rows={2} />
            </div>
            <Button
              onClick={handleAdd}
              disabled={adding || !newKey.trim()}
              className={`w-full gap-2 ${adding ? "pulse-glow" : ""}`}
            >
              {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {adding ? "Adicionando..." : "Adicionar Tema"}
            </Button>
            {adding && <IndeterminateProgress />}
          </div>
        </DialogContent>
      </Dialog>

      {/* Theme Detail Dialog */}
      <Dialog open={!!selectedTheme} onOpenChange={() => setSelectedTheme(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5 text-primary" />
              {selectedTheme?.label || selectedTheme?.key}
            </DialogTitle>
          </DialogHeader>
          {selectedTheme && (
            <div className="space-y-3 animate-fade-in">
              <div className="flex gap-2">
                <Badge variant="secondary">{selectedTheme.key}</Badge>
                {selectedTheme.count > 0 && (
                  <Badge variant="outline">count: {selectedTheme.count}</Badge>
                )}
              </div>
              {selectedTheme.acao && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Acao</p>
                  <p className="text-sm rounded-lg bg-secondary/50 p-3">{selectedTheme.acao}</p>
                </div>
              )}
              {selectedTheme.cenario && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Cenario</p>
                  <p className="text-sm rounded-lg bg-secondary/50 p-3">{selectedTheme.cenario}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
