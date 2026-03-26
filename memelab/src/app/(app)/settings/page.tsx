"use client";

import { useState, useEffect, useCallback } from "react";
import { Settings, Instagram, Loader2, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useInstagramStatus } from "@/hooks/use-api";
import { getInstagramAuthUrl, disconnectInstagram } from "@/lib/api";
import { useSWRConfig } from "swr";

export default function SettingsPage() {
  const { data: igStatus, isLoading, error, mutate } = useInstagramStatus();
  const { mutate: globalMutate } = useSWRConfig();
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Listen for OAuth popup postMessage
  const handleMessage = useCallback(
    async (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "instagram_oauth") return;

      const code = event.data.code;
      if (!code) return;

      setConnecting(true);
      setActionError(null);
      try {
        const { instagramCallback } = await import("@/lib/api");
        await instagramCallback(code);
        await mutate();
        globalMutate("instagram-status");
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Erro ao conectar Instagram");
      } finally {
        setConnecting(false);
      }
    },
    [mutate, globalMutate]
  );

  useEffect(() => {
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [handleMessage]);

  const handleConnect = async () => {
    setActionError(null);
    setConnecting(true);
    try {
      const { auth_url, state } = await getInstagramAuthUrl();
      sessionStorage.setItem("ig_oauth_state", state);
      const w = 600;
      const h = 700;
      const left = window.screenX + (window.innerWidth - w) / 2;
      const top = window.screenY + (window.innerHeight - h) / 2;
      window.open(
        auth_url,
        "instagram_oauth",
        `width=${w},height=${h},left=${left},top=${top},popup=yes`
      );
      // connecting state stays true until postMessage arrives
    } catch (err) {
      setConnecting(false);
      setActionError(err instanceof Error ? err.message : "Erro ao obter URL de autorizacao");
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm("Deseja desconectar sua conta Instagram?")) return;
    setDisconnecting(true);
    setActionError(null);
    try {
      await disconnectInstagram();
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erro ao desconectar");
    } finally {
      setDisconnecting(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const statusBadge = (status?: string) => {
    if (status === "active")
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-400">
          <CheckCircle2 className="h-3 w-3" />
          Ativo
        </span>
      );
    if (status === "expired")
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400">
          <XCircle className="h-3 w-3" />
          Expirado
        </span>
      );
    if (status === "error")
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-400">
          <AlertTriangle className="h-3 w-3" />
          Erro
        </span>
      );
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Configuracoes
        </h1>
        <p className="text-sm text-muted-foreground/70 mt-1">
          Gerencie conexoes e preferencias da plataforma
        </p>
      </div>

      {/* Instagram Connection Card */}
      <Card className="relative overflow-hidden">
        {/* Gradient accent border */}
        <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500" />

        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Instagram className="h-5 w-5 text-pink-400" />
            Instagram Business
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Loading state */}
          {isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-36" />
            </div>
          )}

          {/* Error state */}
          {error && !isLoading && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2">
                <div className="h-2 w-2 rounded-full bg-destructive" />
                <p className="text-sm text-destructive">
                  Erro ao carregar status: {error.message || "API indisponivel"}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => mutate()}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Tentar novamente
              </Button>
            </div>
          )}

          {/* Disconnected state */}
          {!isLoading && !error && igStatus && !igStatus.connected && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Conecte sua conta Instagram Business para publicar memes automaticamente
              </p>
              <Button
                onClick={handleConnect}
                disabled={connecting}
                className="gap-2 rounded-lg bg-gradient-to-r from-pink-500 to-purple-600 px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition"
              >
                {connecting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Instagram className="h-4 w-4" />
                )}
                {connecting ? "Conectando..." : "Conectar Instagram"}
              </Button>
            </div>
          )}

          {/* Connected state */}
          {!isLoading && !error && igStatus && igStatus.connected && (
            <div className="space-y-4">
              {/* Account info */}
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600">
                  <Instagram className="h-5 w-5 text-white" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">@{igStatus.ig_username}</span>
                    <span className="relative flex h-2 w-2">
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Conectado em {formatDate(igStatus.connected_at)}
                  </p>
                </div>
              </div>

              {/* Token status */}
              <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Status do token</span>
                  {statusBadge(igStatus.status)}
                </div>
                {igStatus.token_expires_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Expira em</span>
                    <span className="text-xs font-medium">{formatDate(igStatus.token_expires_at)}</span>
                  </div>
                )}
              </div>

              {/* Disconnect button */}
              <Button
                onClick={handleDisconnect}
                disabled={disconnecting}
                variant="outline"
                className="gap-2 rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition"
              >
                {disconnecting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {disconnecting ? "Desconectando..." : "Desconectar"}
              </Button>
            </div>
          )}

          {/* Action error */}
          {actionError && (
            <div className="mt-3 flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 px-3 py-2">
              <div className="h-2 w-2 rounded-full bg-destructive" />
              <p className="text-sm text-destructive">{actionError}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
