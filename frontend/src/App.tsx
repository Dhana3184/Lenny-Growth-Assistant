
import { useEffect, useState, type FormEvent } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

type Source = {
  citation_id?: string | number;
  title?: string;
  guest?: string;
  youtube_url?: string;
  source_file?: string;
  excerpt?: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

type ArtifactFormat = "markdown" | "html";
type Provider = "ollama" | "openai";

function App() {
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState<Provider>("ollama");
  const [providerModel, setProviderModel] = useState("qwen2.5:3b");

  useEffect(() => {
    fetch(`${API_BASE}/config`)
      .then((r) => {
        if (!r.ok) throw new Error("Config unavailable");
        return r.json();
      })
      .then((c) => {
        if (c.provider === "ollama" || c.provider === "openai") {
          setProvider(c.provider);
          setProviderModel(c.model || "");
        }
      })
      .catch(() => {});
  }, []);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [artifactOpen, setArtifactOpen] = useState(false);
  const [artifactFormat, setArtifactFormat] =
    useState<ArtifactFormat>("markdown");
  const [artifactTitle, setArtifactTitle] = useState("Untitled artifact");
  const [artifactContent, setArtifactContent] = useState("");
  const [artifactLoading, setArtifactLoading] = useState(false);

  function startNewChat() {
    setSessionId(null);
    setMessages([]);
    setQuestion("");
    setError("");
    setArtifactOpen(false);
    setArtifactContent("");
    setArtifactTitle("Untitled artifact");
  }

  async function sendQuestion(prompt: string, showInChat = true): Promise<ChatMessage | null> {
    const response = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: prompt,
        provider,
        ...(sessionId ? { session_id: sessionId } : {}),
      }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Backend error ${response.status}: ${detail.slice(0, 250)}`);
    }

    const result = await response.json();

    if (typeof result.answer !== "string") {
      throw new Error("The backend response did not contain an answer.");
    }

    if (result.session_id) {
      setSessionId(result.session_id);
    }

    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: result.answer,
      sources: Array.isArray(result.sources) ? result.sources : [],
    };

    if (showInChat) {
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: assistantMessage.content,
          sources: assistantMessage.sources },
      ]);
    }

    return assistantMessage;
  }

  async function askQuestion(event?: FormEvent<HTMLFormElement>)  {
    event?.preventDefault();
    if (!question.trim() || loading) return;

    const currentQuestion = question.trim();
    setQuestion("");
    setError("");
    setMessages((previous) => [
      ...previous,
      { role: "user", content: currentQuestion },
    ]);
    setLoading(true);

    try {
      await sendQuestion(currentQuestion);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not get an answer. Check that the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function generateArtifact() {
    if (artifactLoading || loading) return;

    setError("");
    setArtifactLoading(true);
    setArtifactOpen(true);

    const conversation = messages
      .slice(-10)
      .map((message) => `${message.role.toUpperCase()}: ${message.content}`)
      .join("\n\n");

    if (!conversation.trim()) {
      setError("Ask a question first so the artifact can use your conversation.");
      setArtifactLoading(false);
      return;
    }

    const instruction =
      artifactFormat === "html"
        ? `Create a complete, self-contained HTML document with embedded CSS based on this conversation. Return only HTML code, without Markdown fences. Keep factual claims grounded in the conversation and its cited transcript sources. Do not include JavaScript. Give it a polished, accessible design.\n\nConversation:\n${conversation}`
        : `Create a polished Markdown document based on this conversation. Use a clear title, headings, bullets where useful, and actionable takeaways. Keep factual claims grounded in the conversation and its cited transcript sources. Return only the Markdown document.\n\nConversation:\n${conversation}`;

    setArtifactTitle(
      artifactFormat === "html" ? "Generated HTML artifact" : "Generated Markdown artifact",
    );

    try {
      const result = await sendQuestion(instruction, false);
      if (result) {
        const cleaned = result.content
          .replace(/^```(?:html|markdown|md)?\s*/i, "")
          .replace(/\s*```$/, "");
        setArtifactContent(cleaned);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Artifact generation failed. Check the backend.",
      );
    } finally {
      setArtifactLoading(false);
    }
  }

  function downloadArtifact() {
    const extension = artifactFormat === "html" ? "html" : "md";
    const mimeType = artifactFormat === "html" ? "text/html" : "text/markdown";
    const blob = new Blob([artifactContent], { type: `${mimeType};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${artifactTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">L</div>
          <div>
            <strong>Lenny Growth</strong>
            <span>Knowledge assistant</span>
          </div>
        </div>

        <button className="new-chat-button" onClick={startNewChat}>
          <span>＋</span> New chat
        </button>

        <div className="sidebar-label">YOUR WORKSPACE</div>
        <button className="sidebar-link active" onClick={() => setArtifactOpen(false)}>
          <span>◉</span> Conversation
        </button>
        <button
          className="sidebar-link"
          onClick={() => setArtifactOpen(true)}
        >
          <span>▤</span> Artifact workspace
        </button>

        <div className="sidebar-bottom">
          <span className="status-dot" />
          <div>
            <strong>{provider === "ollama" ? "Local AI" : "Cloud AI"}</strong>
            <span>{providerModel}</span>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div>
            <span className="eyebrow">LENNY'S PODCAST</span>
            <h1>Growth Assistant</h1>
          </div>
          <div className="topbar-actions">
            <label className="provider-pill">
              <span className="status-dot" />
              <select
                aria-label="AI provider"
                value={provider}
                disabled={loading || artifactLoading}
                onChange={(event) => {
                  const next = event.target.value as Provider;
                  setProvider(next);
                  setProviderModel(next === "ollama" ? "qwen2.5:3b" : "gpt-4o-mini");
                }}
              >
                <option value="ollama">Local ? Ollama</option>
                <option value="openai">Cloud ? OpenAI</option>
              </select>
            </label>
            <button className="outline-button" onClick={startNewChat}>＋ New chat</button>
          </div>
        </header>

        <div className={`workspace ${artifactOpen ? "with-artifact" : ""}`}>
          <section className="conversation-panel">
            <div className="conversation-scroll">
              {messages.length === 0 ? (
                <div className="welcome-screen">
                  <div className="welcome-icon">✳</div>
                  <span className="eyebrow">YOUR PRODUCT & GROWTH PARTNER</span>
                  <h2>Good ideas start with<br />better questions.</h2>
                  <p>
                    Explore lessons from Lenny's Podcast. Ask about product
                    strategy, finding product-market fit, growth, leadership,
                    and building successful teams.
                  </p>
                  <div className="suggestion-grid">
                    {[
                      "How can startups find product-market fit?",
                      "What makes a successful growth loop?",
                      "How should a product manager prioritize?",
                      "How can teams improve user retention?",
                    ].map((suggestion) => (
                      <button
                        className="suggestion-card"
                        key={suggestion}
                        onClick={() => setQuestion(suggestion)}
                      >
                        <span>{suggestion}</span><span>↗</span>
                      </button>
                    ))}
                  </div>
                  <p className="grounding-note">Answers are generated from retrieved podcast transcripts and include sources when available.</p>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message, index) => (
                    <article className={`message-card ${message.role}`} key={index}>
                      <div className="avatar">
                        {message.role === "user" ? "Y" : "L"}
                      </div>
                      <div className="message-body">
                        <div className="message-heading">
                          <strong>{message.role === "user" ? "You" : "Lenny Assistant"}</strong>
                          {message.role === "assistant" && <span>AI RESPONSE</span>}
                        </div>
                        <p className="message-content">{message.content}</p>
                        {message.sources && message.sources.length > 0 && (
                          <details className="sources">
                            <summary>Sources ({message.sources.length})</summary>
                            <div className="source-list">
                              {message.sources.map((source, sourceIndex) => (
                                <div className="source-card" key={`${source.source_file ?? source.title ?? "source"}-${sourceIndex}`}>
                                  <strong>[{source.citation_id ?? sourceIndex + 1}] {source.title ?? source.source_file ?? "Podcast transcript"}</strong>
                                  {source.guest && <span>Guest: {source.guest}</span>}
                                  {source.excerpt && <p>{source.excerpt}</p>}
                                  {source.youtube_url && (
                                    <a href={source.youtube_url} target="_blank" rel="noreferrer">
                                      Open episode ↗
                                    </a>
                                  )}
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    </article>
                  ))}
                  {loading && (
                    <div className="thinking"><span className="spinner" /> Searching transcripts and preparing an answer…</div>
                  )}
                  <div id="message-end" />
                </div>
              )}
            </div>

            {error && <div className="error-banner" role="alert">{error}</div>}

            <form className="composer" onSubmit={(event) => void askQuestion(event)}>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void askQuestion();
                  }
                }}
                placeholder="Ask a question about product, growth, or leadership…"
                aria-label="Your question"
                rows={2}
              />
              <div className="composer-footer">
                <span>Grounded in Lenny's Podcast transcripts</span>
                <button type="submit" disabled={loading || !question.trim()}>
                  {loading ? "Thinking…" : "Ask Lenny"} <span>↑</span>
                </button>
              </div>
            </form>
            <div className="privacy-note">AI can make mistakes. Verify important claims against the cited sources.</div>
          </section>

          {artifactOpen && (
            <aside className="artifact-panel">
              <div className="artifact-header">
                <div>
                  <span className="eyebrow">WORKSPACE</span>
                  <h2>Artifact viewer</h2>
                </div>
                <button className="icon-button" onClick={() => setArtifactOpen(false)} aria-label="Close artifact viewer">×</button>
              </div>

              <label className="field-label" htmlFor="artifact-title">Artifact title</label>
              <input
                id="artifact-title"
                className="artifact-title-input"
                value={artifactTitle}
                onChange={(event) => setArtifactTitle(event.target.value)}
              />

              <label className="field-label" htmlFor="artifact-format">Output format</label>
              <select
                id="artifact-format"
                value={artifactFormat}
                onChange={(event) => setArtifactFormat(event.target.value as ArtifactFormat)}
              >
                <option value="markdown">Markdown document</option>
                <option value="html">HTML + CSS page</option>
              </select>

              <button className="generate-button" onClick={() => void generateArtifact()} disabled={artifactLoading || loading || messages.length === 0}>
                {artifactLoading ? "Generating…" : "✦ Generate from conversation"}
              </button>

              {artifactLoading && <p className="artifact-hint">Using the current conversation to prepare your artifact…</p>}

              {artifactContent && (
                <>
                  <div className="artifact-preview-label">
                    <span>PREVIEW</span>
                    <button onClick={downloadArtifact}>↓ Download</button>
                  </div>
                  {artifactFormat === "html" ? (
                    <iframe
                      className="html-preview"
                      title="Generated HTML artifact preview"
                      sandbox=""
                      srcDoc={artifactContent}
                    />
                  ) : (
                    <pre className="markdown-preview">{artifactContent}</pre>
                  )}
                  <label className="field-label" htmlFor="artifact-content">Edit source</label>
                  <textarea
                    id="artifact-content"
                    className="artifact-editor"
                    value={artifactContent}
                    onChange={(event) => setArtifactContent(event.target.value)}
                    rows={10}
                  />
                </>
              )}

              {!artifactContent && !artifactLoading && (
                <div className="artifact-empty">
                  <span>▤</span>
                  <strong>Your next great idea, rendered.</strong>
                  <p>Generate a document or a webpage from the conversation. Review the content before sharing it.</p>
                </div>
              )}
              <p className="security-note">HTML preview runs in a sandbox without script permissions. Review generated content before using it elsewhere.</p>
            </aside>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
