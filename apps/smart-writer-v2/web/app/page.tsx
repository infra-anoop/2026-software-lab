"use client";

import { FormEvent, useCallback, useState } from "react";

import { PropertyChips } from "./components/PropertyChips";
import {
  CitationMode,
  SettingsPanel,
} from "./components/SettingsPanel";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

type SourceRow = {
  source_id: string;
  kind?: string;
  bundle?: string;
  uri?: string | null;
  title?: string | null;
};

type ArtifactView = {
  artifact_id: string;
  body: string;
  citation_mode?: string;
  producing_mode?: string;
  parent_artifact_id?: string | null;
  sources?: SourceRow[];
  web_signal?: string;
};

async function api(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`/api/proxy/${path.replace(/^\//, "")}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
}

function showSourcesPanel(mode: string | undefined): boolean {
  return mode === "panel" || mode === "combo" || mode === "footnotes";
}

export default function Page() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [materialUri, setMaterialUri] = useState("");
  const [artifact, setArtifact] = useState<ArtifactView | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [intent, setIntent] = useState<"auto" | "regenerate">("auto");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [citationMode, setCitationMode] = useState<CitationMode>("panel");

  const ensureConversation = useCallback(async (): Promise<string> => {
    if (conversationId) {
      return conversationId;
    }
    const response = await api("v1/conversations", { method: "POST" });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const body = (await response.json()) as { conversation_id: string };
    setConversationId(body.conversation_id);
    return body.conversation_id;
  }, [conversationId]);

  const pollJob = useCallback(async (jobId: string): Promise<void> => {
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      const response = await api(`v1/jobs/${jobId}`);
      const body = (await response.json()) as {
        status?: string;
        error?: string;
        artifact?: ArtifactView;
      };
      setStatus(body.status ?? "unknown");
      if (body.status === "succeeded" && body.artifact) {
        setArtifact(body.artifact);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: body.artifact?.body ?? "" },
        ]);
        return;
      }
      if (body.status === "failed" || body.status === "timed_out") {
        throw new Error(body.error || body.status);
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
    throw new Error("Timed out waiting for draft");
  }, []);

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy) {
      return;
    }
    setBusy(true);
    setStatus("sending");
    setDraft("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    try {
      const cid = await ensureConversation();
      const materials = materialUri.trim()
        ? [{ uri: materialUri.trim(), label: null }]
        : [];
      const response = await api(`v1/conversations/${cid}/messages`, {
        method: "POST",
        body: JSON.stringify({
          text,
          client_intent: intent,
          citation_mode: citationMode,
          materials,
        }),
      });
      const payload = (await response.json()) as {
        type?: string;
        job_id?: string;
        assistant_message?: { text?: string };
        detail?: string;
      };
      if (!response.ok) {
        throw new Error(payload.detail || response.statusText);
      }
      if (payload.type === "clarify") {
        const question = payload.assistant_message?.text ?? "";
        setMessages((prev) => [...prev, { role: "assistant", text: question }]);
        setStatus("clarify");
        return;
      }
      if (payload.type === "job_accepted" && payload.job_id) {
        setStatus("queued");
        await pollJob(payload.job_id);
        return;
      }
      throw new Error("Unexpected turn response");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus("error");
      setMessages((prev) => [...prev, { role: "assistant", text: message }]);
    } finally {
      setIntent("auto");
      setBusy(false);
    }
  }

  const sources = artifact?.sources ?? [];
  const hasSources = sources.length > 0;
  const effectiveMode = artifact?.citation_mode ?? citationMode;
  const renderCitations =
    hasSources && showSourcesPanel(effectiveMode);

  return (
    <main className="shell">
      <header className="top">
        <div className="top-row">
          <div className="brand">
            <h1 className="brand-mark">
              Smart Writer <span>V2</span>
            </h1>
            <p className="brand-lede">
              Grant draft in chat. Questions first if something critical is
              missing.
            </p>
          </div>
          <SettingsPanel
            open={settingsOpen}
            onOpenChange={setSettingsOpen}
            citationMode={citationMode}
            onCitationModeChange={setCitationMode}
            disabled={busy}
          />
        </div>
      </header>
      <div className="grid">
        <section className="thread" aria-label="Conversation">
          {messages.length === 0 ? (
            <p className="empty">
              Describe the org, funder, ask, why them, and any evidence.
            </p>
          ) : (
            messages.map((msg, index) => (
              <article
                key={`${msg.role}-${index}`}
                className={`bubble ${msg.role}`}
              >
                <strong>{msg.role === "user" ? "You" : "Assistant"}</strong>
                <pre>{msg.text}</pre>
              </article>
            ))
          )}
          <form onSubmit={onSubmit} className="composer">
            <label>
              Material URL (optional)
              <input
                value={materialUri}
                onChange={(event) => setMaterialUri(event.target.value)}
                placeholder="https://…"
                disabled={busy}
              />
            </label>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Write a message…"
              rows={4}
              disabled={busy}
            />
            <PropertyChips
              disabled={busy}
              onPick={(id) =>
                setDraft((prev) => (prev.trim() ? `${prev.trim()} ${id}` : id))
              }
            />
            <div className="composer-actions">
              <button type="submit" disabled={busy || !draft.trim()}>
                {busy ? "Working…" : "Send"}
              </button>
              <button
                type="button"
                className="secondary"
                disabled={busy || !artifact}
                onClick={() => setIntent("regenerate")}
              >
                Start over (next send)
              </button>
            </div>
            {intent === "regenerate" ? (
              <p className="status">Next send starts a fresh generate.</p>
            ) : null}
            {status ? <p className="status">{status}</p> : null}
          </form>
        </section>
        <aside className="pane" aria-label="Draft and sources">
          <h2>Draft</h2>
          {artifact ? (
            <p className="status">
              {artifact.producing_mode ?? "generate"}{" "}
              {artifact.artifact_id.slice(0, 8)}
              {artifact.parent_artifact_id
                ? ` ← ${artifact.parent_artifact_id.slice(0, 8)}`
                : " (new)"}
            </p>
          ) : null}
          {artifact?.body ? (
            <pre className="body">{artifact.body}</pre>
          ) : (
            <p className="empty">No draft yet.</p>
          )}
          {hasSources && effectiveMode === "inline" ? (
            <p className="status">
              Citation format: inline (markers in draft when present). No sources
              panel.
            </p>
          ) : null}
          {renderCitations ? (
            <div>
              <h2>{effectiveMode === "footnotes" ? "Footnotes" : "Sources"}</h2>
              <ul className="sources">
                {sources.map((src, index) => (
                  <li key={src.source_id}>
                    {effectiveMode === "footnotes" ? (
                      <sup>{index + 1}</sup>
                    ) : null}{" "}
                    <span>{src.title || src.uri || src.source_id}</span>
                    {src.bundle ? <em> {src.bundle}</em> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </aside>
      </div>
    </main>
  );
}
