type Preset = { value: string; label: string };
type NichePresets = Record<string, Preset[]>;

export function getPresetsForNiche(presetMap: NichePresets, niche: string): Preset[] {
  if (niche && presetMap[niche]) return presetMap[niche];
  return presetMap["outros"] ?? [];
}

// ── Backgrounds ──────────────────────────────────────────────────

export const NICHE_BACKGROUNDS: NichePresets = {
  food: [
    { value: "marmore-branco", label: "Marmore Branco" },
    { value: "mesa-madeira", label: "Mesa de Madeira" },
    { value: "superficie-chocolate", label: "Superficie Chocolate" },
    { value: "tecido-linho", label: "Tecido de Linho" },
    { value: "cozinha-rustica", label: "Cozinha Rustica" },
    { value: "pedra-natural", label: "Pedra Natural" },
    { value: "custom", label: "Personalizado" },
  ],
  beauty: [
    { value: "tecido-suave", label: "Tecido Suave" },
    { value: "studio-clean", label: "Studio Clean" },
    { value: "marmore-rosa", label: "Marmore Rosa" },
    { value: "petala-blur", label: "Petala Blur" },
    { value: "espelho-dourado", label: "Espelho Dourado" },
    { value: "custom", label: "Personalizado" },
  ],
  tech: [
    { value: "gradiente-escuro", label: "Gradiente Escuro" },
    { value: "neon-accent", label: "Neon Accent" },
    { value: "metal-escovado", label: "Metal Escovado" },
    { value: "circuito-abstrato", label: "Circuito Abstrato" },
    { value: "studio-minimal", label: "Studio Minimal" },
    { value: "holografico", label: "Holografico" },
    { value: "custom", label: "Personalizado" },
  ],
  moda: [
    { value: "passarela-blur", label: "Passarela Blur" },
    { value: "tecido-neutro", label: "Tecido Neutro" },
    { value: "espelho-fashion", label: "Espelho Fashion" },
    { value: "urban-concreto", label: "Urban Concreto" },
    { value: "studio-ciclorama", label: "Studio Ciclorama" },
    { value: "custom", label: "Personalizado" },
  ],
  fitness: [
    { value: "academia-blur", label: "Academia Blur" },
    { value: "natureza-verde", label: "Natureza Verde" },
    { value: "concreto-industrial", label: "Concreto Industrial" },
    { value: "quadra-esportiva", label: "Quadra Esportiva" },
    { value: "studio-escuro", label: "Studio Escuro" },
    { value: "custom", label: "Personalizado" },
  ],
  outros: [
    { value: "marmore-branco", label: "Marmore Branco" },
    { value: "gradiente-escuro", label: "Gradiente Escuro" },
    { value: "mesa-madeira", label: "Mesa de Madeira" },
    { value: "concreto-minimal", label: "Concreto Minimal" },
    { value: "studio-ciclorama", label: "Studio Ciclorama" },
    { value: "tecido-neutro", label: "Tecido Neutro" },
    { value: "natureza-blur", label: "Natureza Blur" },
    { value: "custom", label: "Personalizado" },
  ],
};

// ── Scene Lights ─────────────────────────────────────────────────

export const NICHE_SCENE_LIGHTS: NichePresets = {
  food: [
    { value: "natural-suave", label: "Natural Suave" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "zenital-difusa", label: "Zenital Difusa" },
    { value: "backlit-halo", label: "Backlit Halo" },
  ],
  beauty: [
    { value: "ring-light", label: "Ring Light" },
    { value: "soft-fill", label: "Soft Fill" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "contraluz", label: "Contraluz" },
  ],
  tech: [
    { value: "rim-light-dramatica", label: "Rim Light Dramatica" },
    { value: "neon-accent", label: "Neon Accent" },
    { value: "low-key", label: "Low Key" },
    { value: "studio-3pontos", label: "Studio 3 Pontos" },
  ],
  moda: [
    { value: "lateral-dramatica", label: "Lateral Dramatica" },
    { value: "studio-3pontos", label: "Studio 3 Pontos" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "high-key", label: "High Key" },
  ],
  fitness: [
    { value: "natural-dura", label: "Natural Dura" },
    { value: "dramatica-lateral", label: "Dramatica Lateral" },
    { value: "high-key", label: "High Key" },
    { value: "studio-rim", label: "Studio Rim" },
  ],
  outros: [
    { value: "natural-suave", label: "Natural Suave" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "studio-3pontos", label: "Studio 3 Pontos" },
    { value: "rim-light-dramatica", label: "Rim Light Dramatica" },
    { value: "high-key", label: "High Key" },
    { value: "low-key", label: "Low Key" },
  ],
};

// ── Camera Moves ─────────────────────────────────────────────────

export const NICHE_CAMERAS: NichePresets = {
  food: [
    { value: "orbital", label: "Orbital" },
    { value: "dolly-in", label: "Dolly In" },
    { value: "static", label: "Estatica" },
    { value: "crane-up", label: "Crane Up" },
    { value: "steadicam", label: "Steadicam" },
  ],
  beauty: [
    { value: "dolly-in", label: "Dolly In" },
    { value: "orbital", label: "Orbital" },
    { value: "tracking", label: "Tracking" },
    { value: "static", label: "Estatica" },
    { value: "steadicam", label: "Steadicam" },
  ],
  tech: [
    { value: "orbital", label: "Orbital" },
    { value: "dolly-out", label: "Dolly Out" },
    { value: "tracking", label: "Tracking" },
    { value: "crane-up", label: "Crane Up" },
    { value: "handheld", label: "Handheld" },
  ],
  moda: [
    { value: "tracking", label: "Tracking" },
    { value: "steadicam", label: "Steadicam" },
    { value: "dolly-in", label: "Dolly In" },
    { value: "orbital", label: "Orbital" },
    { value: "crane-up", label: "Crane Up" },
  ],
  fitness: [
    { value: "handheld", label: "Handheld" },
    { value: "tracking", label: "Tracking" },
    { value: "dolly-in", label: "Dolly In" },
    { value: "crane-up", label: "Crane Up" },
    { value: "steadicam", label: "Steadicam" },
  ],
  outros: [
    { value: "orbital", label: "Orbital" },
    { value: "dolly-in", label: "Dolly In" },
    { value: "dolly-out", label: "Dolly Out" },
    { value: "tracking", label: "Tracking" },
    { value: "crane-up", label: "Crane Up" },
    { value: "steadicam", label: "Steadicam" },
    { value: "handheld", label: "Handheld" },
    { value: "static", label: "Estatica" },
  ],
};

// ── Lightings ────────────────────────────────────────────────────

export const NICHE_LIGHTINGS: NichePresets = {
  food: [
    { value: "soft-natural", label: "Soft Natural" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "high-key", label: "High Key" },
    { value: "backlit", label: "Backlit" },
  ],
  beauty: [
    { value: "soft-natural", label: "Soft Natural" },
    { value: "studio-3point", label: "Studio 3 Point" },
    { value: "high-key", label: "High Key" },
    { value: "neon-accent", label: "Neon Accent" },
  ],
  tech: [
    { value: "dramatic-rim", label: "Dramatic Rim" },
    { value: "neon-accent", label: "Neon Accent" },
    { value: "low-key", label: "Low Key" },
    { value: "studio-3point", label: "Studio 3 Point" },
  ],
  moda: [
    { value: "studio-3point", label: "Studio 3 Point" },
    { value: "dramatic-rim", label: "Dramatic Rim" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "high-key", label: "High Key" },
  ],
  fitness: [
    { value: "dramatic-rim", label: "Dramatic Rim" },
    { value: "high-key", label: "High Key" },
    { value: "soft-natural", label: "Soft Natural" },
    { value: "backlit", label: "Backlit" },
  ],
  outros: [
    { value: "soft-natural", label: "Soft Natural" },
    { value: "dramatic-rim", label: "Dramatic Rim" },
    { value: "golden-hour", label: "Golden Hour" },
    { value: "high-key", label: "High Key" },
    { value: "low-key", label: "Low Key" },
    { value: "neon-accent", label: "Neon Accent" },
    { value: "studio-3point", label: "Studio 3 Point" },
    { value: "backlit", label: "Backlit" },
  ],
};

// ── Compositions (shared, not niche-specific) ────────────────────

export const COMPOSITIONS: Preset[] = [
  { value: "centered", label: "Centralizado" },
  { value: "rule-of-thirds", label: "Regra dos Tercos" },
  { value: "close-up", label: "Close-up" },
  { value: "wide", label: "Plano Aberto" },
  { value: "low-angle", label: "Contra-plongee" },
  { value: "high-angle", label: "Plongee" },
  { value: "dutch-angle", label: "Dutch Angle" },
];

// ── Moods (shared, not niche-specific) ───────────────────────────

export const MOODS: Preset[] = [
  { value: "premium", label: "Premium" },
  { value: "energetico", label: "Energetico" },
  { value: "misterioso", label: "Misterioso" },
  { value: "acolhedor", label: "Acolhedor" },
  { value: "futurista", label: "Futurista" },
  { value: "natural", label: "Natural" },
  { value: "minimalista", label: "Minimalista" },
  { value: "dramatico", label: "Dramatico" },
];
