import { useEffect, useState } from "react";
import Monitor from "./components/Monitor";
import Timeline from "./components/Timeline";
import ToolsPanel from "./components/ToolsPanel";
import ConsolePanel from "./components/ConsolePanel";
import ChatPanel from "./components/ChatPanel";
import { useEditor } from "./state/editor";
import { IDownload, IFilm, IRedo, IUndo } from "./components/icons";

function Logo() {
  return (
    <svg viewBox="0 0 28 28" className="w-7 h-7">
      <rect x="2.5" y="5" width="23" height="18" rx="3" fill="none" stroke="#ffb224" strokeWidth="2" />
      <path d="M7 5v18M21 5v18" stroke="#ffb224" strokeWidth="1.4" opacity="0.55" />
      <path d="M12.2 10.5v7l6-3.5-6-3.5z" fill="#3adbe6" />
    </svg>
  );
}

export default function App() {
  const ed = useEditor();
  const [chatOpen, setChatOpen] = useState(false);

  /* global shortcuts */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      const mod = e.ctrlKey || e.metaKey;

      if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) ed.redo();
        else ed.undo();
        return;
      }
      if (mod) return;

      switch (e.key) {
        case " ":
          e.preventDefault();
          ed.togglePlay();
          break;
        case "ArrowLeft":
          e.preventDefault();
          ed.stepFrame(e.shiftKey ? -10 : -1);
          break;
        case "ArrowRight":
          e.preventDefault();
          ed.stepFrame(e.shiftKey ? 10 : 1);
          break;
        case "s":
        case "S":
          ed.splitAtPlayhead();
          break;
        case "Delete":
        case "Backspace":
          e.preventDefault();
          ed.removeSelected();
          break;
        case "c":
        case "C":
          ed.setShowCaptions(!ed.showCaptions);
          break;
        case "j":
        case "J":
          ed.setRate(-2);
          if (!ed.playing) ed.togglePlay();
          break;
        case "k":
        case "K":
          if (ed.playing) ed.togglePlay();
          break;
        case "l":
        case "L":
          if (ed.playing && ed.rate === 1) ed.setRate(2);
          else {
            ed.setRate(1);
            if (!ed.playing) ed.togglePlay();
          }
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ed]);

  return (
    <div className="studio-bg scanlines h-full min-h-screen flex flex-col font-body text-ink min-w-[1080px]">
      {/* ------------------------------ top bar ------------------------------ */}
      <header className="relative z-10 flex items-center gap-4 px-4 py-2.5 border-b border-line bg-bg1/80 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <Logo />
          <div className="leading-none">
            <div className="font-display font-bold text-[17px] tracking-tight">
              FRAME<span className="text-amber">FORGE</span>
            </div>
            <div className="text-[9px] font-display font-semibold tracking-[0.22em] text-faint uppercase mt-0.5">
              iterative cut studio
            </div>
          </div>
        </div>

        <div className="h-6 w-px bg-line" />

        <div className="flex items-center gap-2">
          <span className="chip !text-[11px] !py-1"><IFilm className="w-3 h-3 text-amber" /> demo_reel.ffproj</span>
          <span className="chip">{ed.aspect}</span>
          <span className="chip">24 fps</span>
          <span className="chip !text-mint !border-mint/30">
            <span className="w-1.5 h-1.5 rounded-full bg-mint inline-block" />
            autosave
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button className="btn btn-ghost btn-icon" onClick={ed.undo} disabled={!ed.canUndo} title="Undo (Ctrl+Z)">
            <IUndo className="w-4 h-4" />
          </button>
          <button className="btn btn-ghost btn-icon" onClick={ed.redo} disabled={!ed.canRedo} title="Redo (Ctrl+Shift+Z)">
            <IRedo className="w-4 h-4" />
          </button>
          <div className="h-6 w-px bg-line" />
          <button className="btn" onClick={() => window.open('/data/output', '_blank')} title="Open output folder">
            <IDownload className="w-4 h-4" /> Output
          </button>
          <button className="btn btn-amber" onClick={ed.exportEDL}>
            <IDownload className="w-4 h-4" /> Export
          </button>
        </div>
      </header>

      {/* ------------------------------ workspace ---------------------------- */}
      <main className="relative z-10 flex-1 min-h-0 grid grid-cols-[300px_minmax(0,1fr)_330px] gap-4 p-4 max-w-[1800px] w-full mx-auto">
        <aside className="min-h-0">
          <ToolsPanel ed={ed} />
        </aside>

        <section className="min-h-0 flex flex-col gap-4">
          <Monitor ed={ed} />
          <Timeline ed={ed} />
        </section>

        <aside className="min-h-0">
          <ConsolePanel ed={ed} />
        </aside>
      </main>

      {/* ------------------------------ status bar --------------------------- */}
      <footer className="relative z-10 flex items-center gap-4 px-4 py-1.5 border-t border-line bg-bg1/80 text-[10px] font-mono text-faint overflow-x-auto whitespace-nowrap">
        <span><kbd>Space</kbd> play</span>
        <span><kbd>←</kbd><kbd>→</kbd> frame · <kbd>Shift</kbd> ×10</span>
        <span><kbd>S</kbd> split at playhead</span>
        <span><kbd>Del</kbd> remove clip</span>
        <span><kbd>Ctrl Z</kbd> undo · <kbd>Ctrl ⇧ Z</kbd> redo</span>
        <span><kbd>J</kbd><kbd>K</kbd><kbd>L</kbd> shuttle</span>
        <span><kbd>C</kbd> captions</span>
        <span className="ml-auto text-faint">
          sources · <span className="text-cyan/80">data/input/input_audio.mp3</span> ·{" "}
          <span className="text-amber/80">data/input/input_video.mkv</span>
        </span>
      </footer>

      {chatOpen && <ChatPanel ed={ed} onClose={() => setChatOpen(false)} />}
      <button
        className="fixed z-30 bottom-5 right-5 btn btn-amber shadow-xl"
        onClick={() => setChatOpen((open) => !open)}
        aria-label={chatOpen ? "Close agent chat" : "Open agent chat"}
        title={chatOpen ? "Close agent chat" : "Open agent chat"}
      >
        {chatOpen ? "Close chat" : "Agent chat"}
      </button>
    </div>
  );
}
