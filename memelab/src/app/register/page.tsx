"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: "#09090b" }}
      >
        <div
          className="h-8 w-8 rounded-full border-4 border-t-transparent animate-spin"
          style={{ borderColor: "#7C3AED", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (email.trim() === "") {
      errors.email = "Campo obrigatorio.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = "Informe um email valido.";
    }

    if (password === "") {
      errors.password = "Campo obrigatorio.";
    }

    if (confirmPassword === "") {
      errors.confirmPassword = "Campo obrigatorio.";
    } else if (password !== confirmPassword) {
      errors.confirmPassword = "As senhas nao coincidem.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await register(email, password);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      if (message.includes("Email already registered")) {
        setError("Esse email ja esta em uso.");
      } else if (message.includes("Failed to fetch") || err instanceof TypeError) {
        setError("Sem conexao com o servidor. Verifique sua internet.");
      } else {
        setError("Erro no servidor. Tente novamente em alguns instantes.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="max-w-[400px] w-full animate-fade-in">
        <CardHeader className="text-center">
          <CardTitle className="text-xl font-semibold">
            <span className="text-gradient">memeLab</span>
          </CardTitle>
          <CardDescription>Criar uma nova conta</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email field */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-semibold">Email</label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                disabled={isSubmitting}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
                className={fieldErrors.email ? "border-destructive" : ""}
              />
              {fieldErrors.email && (
                <p id="email-error" role="alert" className="text-sm text-destructive mt-1">{fieldErrors.email}</p>
              )}
            </div>

            {/* Password field with show/hide toggle */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-semibold">Senha</label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                  className={fieldErrors.password ? "border-destructive pr-10" : "pr-10"}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {fieldErrors.password && (
                <p id="password-error" role="alert" className="text-sm text-destructive mt-1">{fieldErrors.password}</p>
              )}
            </div>

            {/* Confirm password field with show/hide toggle */}
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-semibold">Confirmar senha</label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  aria-describedby={fieldErrors.confirmPassword ? "confirm-error" : undefined}
                  className={fieldErrors.confirmPassword ? "border-destructive pr-10" : "pr-10"}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Ocultar senha" : "Mostrar senha"}
                  tabIndex={-1}
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {fieldErrors.confirmPassword && (
                <p id="confirm-error" role="alert" className="text-sm text-destructive mt-1">{fieldErrors.confirmPassword}</p>
              )}
            </div>

            {/* Server error area */}
            {error && (
              <p role="alert" className="text-sm text-destructive animate-fade-in">{error}</p>
            )}

            {/* Submit button */}
            <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Criando conta...
                </>
              ) : (
                "Criar conta"
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <p className="text-sm text-muted-foreground">
            Ja tem conta?{" "}
            <Link href="/login" className="text-primary hover:underline underline-offset-4">
              Entrar
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
