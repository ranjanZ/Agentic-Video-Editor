import { FormEvent, useState } from "react";
import type { Editor } from "../state/editor";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatPanelProps = {
  ed: Editor;
};

export default function ChatPanel({ ed }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "What would you like to change in this edit?" },
  ]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;

    setDraft("");
    setError(null);
    setMessages((current) => [...current, { role: "user", content: message }]);
    setSending(true);

    try {
      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          context: {
            video_path: ed.videoPath,
            audio_path: ed.audioPath,
            media_sources: ed.mediaSources.map(({ path, type, duration }) => ({ path, type, duration })),
            tool_config: ed.toolConfig,
            output_dir: "data/output",
          },
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The agent could not respond.");
      ed.applyAgentResult(data);
      setMessages((current) => [...current, { role: "assistant", content: data.content || "Done." }]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The agent could not respond.");
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="panel flex-1 min-h-0 flex flex-col overflow-hidden">
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-line bg-bg2/90">
        <div>
          <div className="panel-title text-amber">agent chat</div>
          <div className="text-[11px] text-faint mt-1">FrameForge assistant</div>
        </div>
        <span className="chip !text-mint !border-mint/30">online</span>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] rounded-lg px-3 py-2 text-[12px] leading-relaxed ${message.role === "user" ? "bg-amber text-bg0" : "bg-bg3 text-ink border border-line2"}`}>
              {message.content}
            </div>
          </div>
        ))}
        {sending && <div className="text-[11px] text-faint anim-log">agent is thinking...</div>}
        {error && <div className="text-[11px] text-coral border border-coral/30 bg-coral/10 rounded px-3 py-2">{error}</div>}
      </div>

      <form onSubmit={sendMessage} className="p-3 border-t border-line bg-bg1/80">
        <div className="flex items-end gap-2">
          <textarea
            className="path-input min-h-[42px] max-h-24 resize-none"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask for an edit..."
            aria-label="Chat message"
            disabled={sending}
          />
          <button className="btn btn-amber h-[42px]" type="submit" disabled={!draft.trim() || sending}>
            Send
          </button>
        </div>
      </form>
    </section>
  );
}