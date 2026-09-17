"use client";

const CLOSED_PROPERTIES = [
  "factual",
  "persuasive",
  "concise",
  "warm",
  "formal",
  "humorous",
  "specific",
  "urgent",
] as const;

type PropertyChipsProps = {
  onPick: (propertyId: string) => void;
  disabled?: boolean;
};

export function PropertyChips({ onPick, disabled = false }: PropertyChipsProps) {
  return (
    <div className="chips" aria-label="Optional property chips">
      <p className="status">
        Optional tone chips (correction only). The message stays primary.
      </p>
      <div className="chip-row">
        {CLOSED_PROPERTIES.map((id) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            onClick={() => onPick(id)}
          >
            {id}
          </button>
        ))}
      </div>
    </div>
  );
}