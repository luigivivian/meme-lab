"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MessageSquareQuote, Sparkles, Copy, Check, Image, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { IndeterminateProgress } from "@/components/ui/progress";
import { generatePhrases } from "@/lib/api";

export default function PhrasesPage() {
  return (
    <Suspense>
      <PhrasesContent />
    </Suspense>
  );
}

function PhrasesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [phrases, setPhrases] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  useEffect(() => {
    const t = searchParams.get("topic");
    if (t) setTopic(t);
  }, [searchParams]);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await generatePhrases({ topic, count });
      setPhrases(result.phrases ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao gerar frases");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (phrase: string, idx: number) => {
    navigator.clipboard.writeText(phrase);
    setCopied(idx);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="space-y-6 max-w-3xl animate-page-in">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquareQuote className="h-5 w-5 text-primary" />
            Gerar Frases
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <Input
              placeholder="Tema (ex: segunda-feira, cafe, tecnologia...)"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
              className="flex-1"
            />
            <Input
              type="number"
              min={1}
              max={20}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-20"
            />
            <Button
              onClick={handleGenerate}
              disabled={loading || !topic.trim()}
              className={`gap-2 ${loading ? "pulse-glow" : ""}`}
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? "Gerando..." : "Gerar"}
            </Button>
          </div>
          {loading && (
            <div className="space-y-2 animate-fade-in">
              <IndeterminateProgress />
              <p className="text-xs text-muted-foreground text-center">Gerando frases via Gemini...</p>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2 animate-fade-in">
              <div className="h-2 w-2 rounded-full bg-destructive" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {phrases.length > 0 && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-base">{phrases.length} frases geradas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {phrases.map((phrase, idx) => (
              <div
                key={`${phrase.slice(0, 20)}-${idx}`}
                className="stagger-item group flex items-start justify-between gap-3 rounded-xl bg-secondary/50 px-4 py-3 transition-colors duration-200 hover:bg-secondary/70"
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                <p className="flex-1 text-sm leading-relaxed">{phrase}</p>
                <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleCopy(phrase, idx)}
                  >
                    {copied === idx ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => router.push("/gallery")}
                    title="Compor imagem"
                  >
                    <Image className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
