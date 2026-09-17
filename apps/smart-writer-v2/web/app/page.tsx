"use client";

import { FormEvent, useCallback, useState } from "react";

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

export default function Page() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [materialUri, setMaterialUri] = useState("");
  const [artifact, setArtifact] = useState<ArtifactView | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

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
          client_intent: "auto",
          citation_mode: null,
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
      setBusy(false);
    }
  }

  const sources = artifact?.sources ?? [];

  return (
    <main className="shell">
      <header className="top">
        <h1>Smart Writer V2</h1>
        <p>Grant draft in chat. Questions first if something critical is missing.</p>
      </header>
      <div className="grid">
        <section className="thread" aria-label="Conversation">
          {messages.length === 0 ? (
            <p className="empty">Describe the org, funder, ask, why them, and any evidence.</p>
          ) : (
            messages.map((msg, index) => (
              <article key={`${msg.role}-${index}`} className={`bubble ${msg.role}`}>
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
            <button type="submit" disabled={busy || !draft.trim()}>
              {busy ? "Working…" : "Send"}
            </button>
            {status ? <p className="status">{status}</p> : null}
          </form>
        </section>
        <aside className="pane" aria-label="Draft and sources">
          <h2>Draft</h2>
          {artifact?.body ? <pre className="body">{artifact.body}</pre> : <p className="empty">No draft yet.</p>}
          {artifact?.citation_mode === "panel" || sources.length > 0 ? (
            <div>
              <h2>Sources</h2>
              {sources.length === 0 ? (
                <p className="empty">No sources on this draft.</p>
              ) : (
                <ul className="sources">
                  {sources.map((src) => (
                    <li key={src.source_id}>
                      <span>{src.title || src.uri || src.source_id}</span>
                      {src.bundle ? <em> {src.bundle}</em> : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </aside>
      </div>
    </main>
  );
}
