"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { CharacterSummary } from "@/lib/api";
import { useCharacters } from "@/hooks/use-api";

interface CharacterContextType {
  characters: CharacterSummary[];
  activeSlug: string;
  setActiveSlug: (slug: string) => void;
  activeCharacter: CharacterSummary | null;
  isLoading: boolean;
}

const CharacterContext = createContext<CharacterContextType>({
  characters: [],
  activeSlug: "mago-mestre",
  setActiveSlug: () => {},
  activeCharacter: null,
  isLoading: true,
});

const STORAGE_KEY = "clip-flow-active-character";

export function CharacterProvider({ children }: { children: React.ReactNode }) {
  const [activeSlug, setActiveSlugState] = useState("mago-mestre");
  const { data, isLoading } = useCharacters();
  const characters = data?.characters ?? [];

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setActiveSlugState(stored);
  }, []);

  const setActiveSlug = useCallback((slug: string) => {
    setActiveSlugState(slug);
    localStorage.setItem(STORAGE_KEY, slug);
  }, []);

  const activeCharacter =
    characters.find((c) => c.slug === activeSlug) ?? characters[0] ?? null;

  return (
    <CharacterContext.Provider
      value={{
        characters,
        activeSlug,
        setActiveSlug,
        activeCharacter,
        isLoading,
      }}
    >
      {children}
    </CharacterContext.Provider>
  );
}

export function useCharacterContext() {
  return useContext(CharacterContext);
}
