"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  CreditCard,
  CheckCircle2,
  Crown,
  Zap,
  Building2,
  Loader2,
  ExternalLink,
  Infinity,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useBillingStatus } from "@/hooks/use-api";
import { createCheckoutSession, createPortalSession } from "@/lib/api";

// ---------------------------------------------------------------------------
// Plan definitions (D-16)
// ---------------------------------------------------------------------------
const PLANS = [
  {
    key: "free",
    name: "Free",
    price: "R$0",
    period: "/mes",
    icon: Zap,
    features: [
      "50 memes/dia",
      "5 videos/dia",
      "500 chamadas texto/dia",
      "Suporte comunidade",
    ],
    highlighted: false,
  },
  {
    key: "pro",
    name: "Pro",
    price: "R$99",
    period: "/mes",
    icon: Crown,
    features: [
      "500 memes/dia",
      "50 videos/dia",
      "5.000 chamadas texto/dia",
      "Suporte prioritario",
    ],
    highlighted: true,
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "R$249",
    period: "/mes",
    icon: Building2,
    features: [
      "Memes ilimitados",
      "Videos ilimitados",
      "Chamadas ilimitadas",
      "Suporte dedicado",
    ],
    highlighted: false,
  },
] as const;

// Tier ordering for upgrade / downgrade logic
const TIER_ORDER: Record<string, number> = { free: 0, pro: 1, enterprise: 2 };

// Progress bar colour based on usage percentage
function usageColor(pct: number): string {
  if (pct > 95) return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
  if (pct > 80) return "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.3)]";
  if (pct > 60) return "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]";
  return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]";
}

// Service display name mapping
function serviceLabel(service: string): string {
  const map: Record<string, string> = {
    gemini_image: "Imagens Gemini",
    gemini_text: "Texto Gemini",
    video: "Videos",
    pipeline: "Pipeline",
    compose: "Composicao",
  };
  return map[service] ?? service;
}

export default function BillingPage() {
  const { data: billing, isLoading, error, mutate } = useBillingStatus();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [alert, setAlert] = useState<{
    type: "success" | "warning";
    message: string;
  } | null>(null);

  // Handle success / cancel URL params on mount
  useEffect(() => {
    if (searchParams.get("success") === "true") {
      setAlert({
        type: "success",
        message: "Assinatura ativada com sucesso!",
      });
      mutate();
      router.replace("/billing");
    } else if (searchParams.get("canceled") === "true") {
      setAlert({ type: "warning", message: "Checkout cancelado" });
      router.replace("/billing");
    }
  }, [searchParams, router, mutate]);

  // Dismiss alert after 6 seconds
  useEffect(() => {
    if (!alert) return;
    const t = setTimeout(() => setAlert(null), 6000);
    return () => clearTimeout(t);
  }, [alert]);

  // ------- handlers -------
  const handleUpgrade = async (planKey: string) => {
    setCheckoutLoading(planKey);
    try {
      const res = await createCheckoutSession(
        planKey,
        `${window.location.origin}/billing?success=true`,
        `${window.location.origin}/billing?canceled=true`
      );
      window.location.href = res.checkout_url;
    } catch (err) {
      setAlert({
        type: "warning",
        message:
          err instanceof Error
            ? err.message
            : "Erro ao iniciar checkout",
      });
      setCheckoutLoading(null);
    }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const res = await createPortalSession(
        `${window.location.origin}/billing`
      );
      window.location.href = res.portal_url;
    } catch (err) {
      setAlert({
        type: "warning",
        message:
          err instanceof Error
            ? err.message
            : "Erro ao abrir portal",
      });
      setPortalLoading(false);
    }
  };

  const currentTier = billing?.plan ?? "free";

  return (
    <div className="space-y-8">
      {/* Alert banner */}
      {alert && (
        <div
          className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium ${
            alert.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          }`}
        >
          {alert.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <CreditCard className="h-4 w-4 shrink-0" />
          )}
          {alert.message}
        </div>
      )}

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <CreditCard className="h-6 w-6" />
          Planos e Cobranca
        </h1>
        <p className="text-sm text-muted-foreground/70 mt-1 flex items-center gap-2">
          Gerencie sua assinatura e acompanhe o uso
          {billing && (
            <Badge variant="secondary" className="text-xs">
              {billing.plan_name}
            </Badge>
          )}
        </p>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid gap-6 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-24" />
              </CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-9 w-28" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-full" />
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">
              Erro ao carregar dados de cobranca:{" "}
              {error.message || "API indisponivel"}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => mutate()}
            >
              Tentar novamente
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Plan cards (D-16) */}
      {billing && !isLoading && (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            {PLANS.map((plan) => {
              const isCurrent = currentTier === plan.key;
              const tierDiff =
                TIER_ORDER[plan.key] - TIER_ORDER[currentTier];
              const Icon = plan.icon;

              return (
                <Card
                  key={plan.key}
                  className={`relative flex flex-col ${
                    plan.highlighted
                      ? "ring-1 ring-primary/40 border-primary/20"
                      : ""
                  } ${isCurrent ? "ring-1 ring-emerald-500/40 border-emerald-500/20" : ""}`}
                >
                  {/* Highlighted badge */}
                  {plan.highlighted && !isCurrent && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-primary/90 text-xs">
                        Recomendado
                      </Badge>
                    </div>
                  )}

                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Icon className="h-5 w-5 text-primary" />
                      {plan.name}
                      {isCurrent && (
                        <Badge variant="success" className="ml-auto text-xs">
                          Plano atual
                        </Badge>
                      )}
                    </CardTitle>
                  </CardHeader>

                  <CardContent className="flex-1 space-y-4">
                    {/* Price */}
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold tracking-tight">
                        {plan.price}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {plan.period}
                      </span>
                    </div>

                    {/* Features */}
                    <ul className="space-y-2">
                      {plan.features.map((f) => (
                        <li
                          key={f}
                          className="flex items-center gap-2 text-sm text-muted-foreground"
                        >
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </CardContent>

                  <CardFooter>
                    {isCurrent ? (
                      <div className="w-full text-center text-xs text-muted-foreground">
                        Voce esta neste plano
                      </div>
                    ) : plan.key === "free" ? (
                      // Can't subscribe to free via Stripe
                      <div className="w-full text-center text-xs text-muted-foreground">
                        Plano padrao
                      </div>
                    ) : tierDiff > 0 ? (
                      <Button
                        className="w-full"
                        disabled={checkoutLoading === plan.key || !billing.stripe_configured}
                        onClick={() => handleUpgrade(plan.key)}
                      >
                        {checkoutLoading === plan.key ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : null}
                        Upgrade para {plan.name}
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        className="w-full"
                        disabled={checkoutLoading === plan.key || !billing.stripe_configured}
                        onClick={() => handleUpgrade(plan.key)}
                      >
                        {checkoutLoading === plan.key ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : null}
                        Mudar para {plan.name}
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              );
            })}
          </div>

          {/* Usage section (D-17) */}
          {billing.services.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Zap className="h-5 w-5 text-primary" />
                  Uso do Plano
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  Renovacao em{" "}
                  {new Date(billing.resets_at).toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </CardHeader>
              <CardContent className="space-y-5">
                {billing.services.map((svc) => {
                  const isUnlimited = svc.limit === 0;
                  const pct = isUnlimited
                    ? 100
                    : svc.limit > 0
                      ? Math.min(100, Math.round((svc.used / svc.limit) * 100))
                      : 0;

                  return (
                    <div key={`${svc.service}-${svc.tier}`} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">
                          {serviceLabel(svc.service)}
                          {svc.tier !== "free" && svc.tier !== svc.service && (
                            <span className="ml-1.5 text-xs text-muted-foreground">
                              ({svc.tier})
                            </span>
                          )}
                        </span>
                        <span className="tabular-nums text-muted-foreground">
                          {isUnlimited ? (
                            <span className="flex items-center gap-1">
                              {svc.used}
                              <span className="text-muted-foreground/50">/</span>
                              <Infinity className="h-4 w-4 text-emerald-500" />
                            </span>
                          ) : (
                            `${svc.used} / ${svc.limit}`
                          )}
                        </span>
                      </div>
                      <Progress
                        value={pct}
                        className="h-2"
                        indicatorClassName={
                          isUnlimited
                            ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]"
                            : usageColor(pct)
                        }
                      />
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Manage subscription section (D-18) */}
          {billing.stripe_configured ? (
            billing.subscription_status && currentTier !== "free" ? (
              <Card>
                <CardContent className="flex items-center justify-between py-5">
                  <div>
                    <p className="text-sm font-medium">
                      Gerenciar Assinatura
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Alterar forma de pagamento, ver faturas ou cancelar
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handlePortal}
                    disabled={portalLoading}
                    className="gap-2"
                  >
                    {portalLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ExternalLink className="h-4 w-4" />
                    )}
                    Gerenciar Assinatura
                  </Button>
                </CardContent>
              </Card>
            ) : null
          ) : (
            <div className="text-center text-xs text-muted-foreground/50 py-2">
              Cobranca nao configurada neste servidor
            </div>
          )}
        </>
      )}
    </div>
  );
}
