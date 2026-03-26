"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"validating" | "relaying" | "redirecting" | "error">("validating");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code) {
      setStatus("error");
      setErrorMsg("Codigo de autorizacao nao encontrado");
      return;
    }

    // CSRF check: validate state matches sessionStorage
    const savedState = sessionStorage.getItem("ig_oauth_state");
    if (state && savedState && state !== savedState) {
      setStatus("error");
      setErrorMsg("Estado de autorizacao invalido (CSRF)");
      return;
    }

    // Clear saved state
    sessionStorage.removeItem("ig_oauth_state");

    // If opened as popup, relay code to opener
    if (window.opener) {
      setStatus("relaying");
      window.opener.postMessage(
        { type: "instagram_oauth", code },
        window.location.origin
      );
      // Auto-close popup after a brief delay
      setTimeout(() => {
        window.close();
      }, 1000);
    } else {
      // Direct navigation (not popup) — redirect to settings
      setStatus("redirecting");
      router.push("/settings");
    }
  }, [searchParams, router]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
      {status === "error" ? (
        <div className="text-center space-y-2">
          <p className="text-sm text-red-400">{errorMsg}</p>
          <button
            onClick={() => router.push("/settings")}
            className="text-xs text-muted-foreground underline hover:text-white transition"
          >
            Voltar para Configuracoes
          </button>
        </div>
      ) : (
        <>
          <Loader2 className="h-8 w-8 animate-spin text-pink-400" />
          <p className="text-sm text-muted-foreground">
            {status === "validating" && "Validando autorizacao..."}
            {status === "relaying" && "Conectando..."}
            {status === "redirecting" && "Redirecionando..."}
          </p>
        </>
      )}
    </div>
  );
}

export default function InstagramCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-pink-400" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
