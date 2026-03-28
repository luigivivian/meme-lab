"use client";

import { Input } from "@/components/ui/input";

export interface SrtEntry {
  index: number;
  start: string;
  end: string;
  text: string;
}

export function SrtEditor({
  entries,
  onChange,
}: {
  entries: SrtEntry[];
  onChange: (entries: SrtEntry[]) => void;
}) {
  function updateEntry(idx: number, field: keyof SrtEntry, value: string) {
    const updated = entries.map((e, i) =>
      i === idx ? { ...e, [field]: field === "index" ? parseInt(value) || 0 : value } : e
    );
    onChange(updated);
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[60px_100px_100px_1fr] gap-2 text-xs text-muted-foreground font-medium px-1">
        <span>#</span>
        <span>Inicio</span>
        <span>Fim</span>
        <span>Texto</span>
      </div>
      {entries.map((entry, idx) => (
        <div key={entry.index} className="grid grid-cols-[60px_100px_100px_1fr] gap-2 items-center">
          <span className="text-xs text-muted-foreground text-center">{entry.index}</span>
          <Input
            value={entry.start}
            onChange={(e) => updateEntry(idx, "start", e.target.value)}
            className="font-mono text-xs h-8"
            placeholder="00:00:00,000"
          />
          <Input
            value={entry.end}
            onChange={(e) => updateEntry(idx, "end", e.target.value)}
            className="font-mono text-xs h-8"
            placeholder="00:00:00,000"
          />
          <Input
            value={entry.text}
            onChange={(e) => updateEntry(idx, "text", e.target.value)}
            className="text-sm h-8"
          />
        </div>
      ))}
      {entries.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-4">Nenhuma legenda carregada.</p>
      )}
    </div>
  );
}
