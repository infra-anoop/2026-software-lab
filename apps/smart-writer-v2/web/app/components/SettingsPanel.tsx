"use client";

export const CITATION_MODES = ["panel", "inline", "footnotes", "combo"] as const;

export type CitationMode = (typeof CITATION_MODES)[number];

type SettingsPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  citationMode: CitationMode;
  onCitationModeChange: (mode: CitationMode) => void;
  auditSecret: string;
  onAuditSecretChange: (value: string) => void;
  disabled?: boolean;
};

const MODE_LABELS: Record<CitationMode, string> = {
  panel: "Sources panel (default)",
  inline: "Inline markers",
  footnotes: "Footnotes",
  combo: "Panel + inline",
};

export function SettingsPanel({
  open,
  onOpenChange,
  citationMode,
  onCitationModeChange,
  auditSecret,
  onAuditSecretChange,
  disabled = false,
}: SettingsPanelProps) {
  return (
    <section className="settings" aria-label="Settings">
      <button
        type="button"
        className="settings-toggle"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => onOpenChange(!open)}
      >
        Settings
      </button>
      {open ? (
        <div className="settings-body">
          <p className="status">Chat preferences. More options will land here.</p>
          <label className="settings-field">
            Preview gate secret
            <input
              type="password"
              autoComplete="off"
              value={auditSecret}
              disabled={disabled}
              onChange={(event) => onAuditSecretChange(event.target.value)}
              placeholder="Shared preview secret"
            />
          </label>
          <p className="status">
            Preview gate only. The browser sends this as X-Audit-Secret. Anyone
            with the secret can run paid jobs. This is not a login.
          </p>
          <label className="settings-field">
            Citation format
            <select
              value={citationMode}
              disabled={disabled}
              onChange={(event) =>
                onCitationModeChange(event.target.value as CitationMode)
              }
            >
              {CITATION_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {MODE_LABELS[mode]}
                </option>
              ))}
            </select>
          </label>
          <p className="status">
            Applies on the next send. Hidden when a draft has no sources.
          </p>
        </div>
      ) : null}
    </section>
  );
}
