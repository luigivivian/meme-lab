"use client";

import Link from "next/link";
import { Users, Plus, ImageIcon } from "lucide-react";
import { useCharacters } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import type { CharacterSummary } from "@/lib/api";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: "Rascunho", color: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
  refining: { label: "Refinando", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  ready: { label: "Pronto", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
};

function CharacterCard({ character }: { character: CharacterSummary }) {
  const status = STATUS_CONFIG[character.status] ?? STATUS_CONFIG.draft;

  return (
    <Link
      href={`/characters/${character.slug}`}
      className="group rounded-2xl border bg-card p-5 transition-all duration-200 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
    >
      <div className="flex items-start gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/20 text-primary text-xl font-bold shrink-0">
          {character.name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-lg truncate group-hover:text-primary transition-colors">
            {character.name}
          </h3>
          <p className="text-sm text-muted-foreground truncate">{character.handle}</p>
        </div>
        <span className={cn("text-xs px-2.5 py-1 rounded-full border", status.color)}>
          {status.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
          <p className="text-lg font-semibold">{character.refs.approved}</p>
          <p className="text-[11px] text-muted-foreground">Refs</p>
        </div>
        <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
          <p className="text-lg font-semibold">{character.themes_count}</p>
          <p className="text-[11px] text-muted-foreground">Temas</p>
        </div>
        <div className="rounded-lg bg-secondary/50 px-3 py-2 text-center">
          <p className="text-lg font-semibold">{character.refs.pending}</p>
          <p className="text-[11px] text-muted-foreground">Pendentes</p>
        </div>
      </div>

      {/* Refs progress */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
          <span>Referencias aprovadas</span>
          <span>{character.refs.approved}/{character.refs.ideal}</span>
        </div>
        <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              character.refs.is_ready ? "bg-emerald-500" : "bg-primary"
            )}
            style={{ width: `${Math.min(100, (character.refs.approved / character.refs.ideal) * 100)}%` }}
          />
        </div>
      </div>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
        <ImageIcon className="h-8 w-8 text-primary" />
      </div>
      <h3 className="text-lg font-semibold mb-2">Nenhum personagem encontrado</h3>
      <p className="text-sm text-muted-foreground max-w-md">
        Crie seu primeiro personagem para comecar a gerar memes com identidade unica.
      </p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-2xl border bg-card p-5 animate-pulse">
          <div className="flex items-start gap-4">
            <div className="h-14 w-14 rounded-xl bg-secondary" />
            <div className="flex-1 space-y-2">
              <div className="h-5 w-32 rounded bg-secondary" />
              <div className="h-4 w-24 rounded bg-secondary" />
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3">
            {[1, 2, 3].map((j) => (
              <div key={j} className="h-14 rounded-lg bg-secondary" />
            ))}
          </div>
          <div className="mt-3 h-1.5 rounded-full bg-secondary" />
        </div>
      ))}
    </div>
  );
}

export default function CharactersPage() {
  const { data, isLoading } = useCharacters();
  const characters = data?.characters ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Users className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Personagens</h1>
            <p className="text-sm text-muted-foreground">
              {data ? `${data.total} personagem${data.total !== 1 ? "s" : ""}` : "Carregando..."}
            </p>
          </div>
        </div>
        <Link
          href="/characters/new"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Novo Personagem
        </Link>
      </div>

      {/* Grid */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : !characters.length ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {characters.map((char) => (
            <CharacterCard key={char.slug} character={char} />
          ))}
        </div>
      )}
    </div>
  );
}
