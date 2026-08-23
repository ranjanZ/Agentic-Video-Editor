import { useEffect, useRef } from "react";
import { Editor, LogLevel } from "../state/editor";

const LEVEL_STYLE: Record<LogLevel, { tag: string; cls: string }> = {
  info: { tag: "info", cls: "text-dim border-line" },
  ok: { tag: " ok ", cls: "text-mint border-mint/40" },
  warn: { tag: "warn", cls: "text-amber border-amber/40" },
  err: { tag: "fail", cls: "text-coral border-coral/40" },
  tool: { tag: "tool", cls: "text-cyan border-cyan/40" },
};

export default function ConsolePanel({ ed }: { ed: Editor }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [ed.logs.length]);

  return (
    <div className="flex flex-col h-[180px] min-h-0">
      {/* console */}
      <div className="panel flex-1 min-h-0 flex flex-col anim-rise" style={{ animationDelay: "60ms" }}>
        <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-line">
          <span className="w-2 h-2 rounded-full bg-mint/80" />
          <h3 className="panel-title">Session console</h3>
          <span className="ml-auto font-mono text-[9.5px] text-faint">{ed.logs.length} events</span>
        </div>
        <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-3 py-2.5 flex flex-col gap-1.5">
          {ed.logs.map((l) => {
            const s = LEVEL_STYLE[l.level];
            return (
              <div key={l.id} className="anim-log flex items-start gap-2 leading-snug">
                <span className="font-mono text-[9.5px] text-faint tabular-nums mt-0.5 shrink-0">{l.time}</span>
                <span className={`font-mono text-[9px] uppercase tracking-wider border rounded px-1 py-px mt-px shrink-0 ${s.cls}`}>
                  {s.tag}
                </span>
                <span className="font-mono text-[10.5px] text-ink/85 break-words min-w-0">{l.text}</span>
              </div>
            );
          })}
        </div>
        <div className="px-3.5 py-2 border-t border-line bg-bg1/60 font-mono text-[9.5px] text-faint">
          frameforge v2.1 · preview engine · all tool calls logged with resolved paths
        </div>
      </div>
    </div>
  );
}
