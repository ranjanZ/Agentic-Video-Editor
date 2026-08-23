import { useMemo } from "react";
import { DEFAULT_AUDIO_PATH, DEFAULT_VIDEO_PATH, Editor, ToolId } from "../state/editor";
import { detectSilence } from "../engine/media";
import { IAlert, IBolt, ICaptions, ICheck, IFilm, IHistory, IRatio, IReset, ISpinner, IWave } from "./icons";

const AUDIO_RE = /\.(mp3|wav)$/i;
const VIDEO_RE = /\.(mkv|mp4|mov|webm)$/i;

function SectionHead({ icon, title, aside }: { icon: React.ReactNode; title: string; aside?: string }) {
  return (
    <div className="flex items-center gap-2 mb-2.5">
      <span className="text-faint">{icon}</span>
      <h3 className="panel-title">{title}</h3>
      {aside && <span className="ml-auto font-mono text-[9.5px] text-faint">{aside}</span>}
    </div>
  );
}

export default function ToolsPanel({ ed }: { ed: Editor }) {
  const audioValid = AUDIO_RE.test(ed.audioPath.trim());
  const videoValid = VIDEO_RE.test(ed.videoPath.trim());
  const gapCount = useMemo(() => detectSilence().length, []);

  const upload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/upload", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed");
    const path = data.path as string;
    const type = AUDIO_RE.test(path) ? "audio" : VIDEO_RE.test(path) ? "video" : null;
    if (!type) throw new Error("Unsupported media format");
    const media = document.createElement(type);
    media.preload = "metadata";
    media.onloadedmetadata = () => ed.addMediaSource(path, type, Number.isFinite(media.duration) ? media.duration : 0);
    media.onerror = () => ed.addMediaSource(path, type);
    media.src = `/data/input/${encodeURIComponent(path.split(/[\\/]/).pop() || "")}`;
  };

  const tools: Array<{
    id: ToolId;
    name: string;
    desc: string;
    icon: React.ReactNode;
    color: string;
    border: string;
    params: string[];
    note: string;
    ready: boolean;
    readyHint?: string;
  }> = [
    {
      id: "silence",
      name: "Remove silence",
      desc: "Scans A1 for gaps under −32 dB, cuts them and ripple-deletes on V1.",
      icon: <IWave className="w-4 h-4" />,
      color: "text-amber",
      border: "border-amber/40 bg-amber/10 hover:bg-amber/20",
      params: [`input_path="${ed.audioPath}"`, `min_gap=0.65s`],
      note: `${gapCount} silent gaps found in source`,
      ready: audioValid && ed.clips.length > 0,
      readyHint: "audio path must end in .mp3 or .wav",
    },
    {
      id: "vertical",
      name: ed.aspect === "9:16" ? "Convert to landscape" : "Convert to vertical",
      desc:
        ed.aspect === "9:16"
          ? "Conforms the sequence back to 16:9 and restores the full frame."
          : "Center-reframes every shot to 9:16 with action-safe guides.",
      icon: <IRatio className="w-4 h-4" />,
      color: "text-cyan",
      border: "border-cyan/40 bg-cyan/10 hover:bg-cyan/20",
      params: [`input="${ed.videoPath}"`, ed.aspect === "9:16" ? "preset=16:9" : "preset=9:16"],
      note:
        ed.aspect === "9:16"
          ? "currently 9:16 — run to revert to landscape"
          : "output → data/output/*_vertical_9x16.mkv",
      ready: videoValid && audioValid,
      readyHint: "video path must end in .mkv / .mp4 / .mov",
    },
    {
      id: "transcribe",
      name: "Transcribe dialogue",
      desc: "ASR v2 with word timing — writes caption blocks onto track TX.",
      icon: <ICaptions className="w-4 h-4" />,
      color: "text-sky",
      border: "border-sky/40 bg-sky/10 hover:bg-sky/20",
      params: [`input_path="${ed.audioPath}"`, "model=asr-v2"],
      note: ed.captions ? `${ed.captions.length} caption blocks on TX` : "TX track is empty",
      ready: audioValid,
      readyHint: "audio path must end in .mp3 or .wav",
    },
  ];

  return (
    <div className="flex flex-col gap-4 h-full min-h-0 overflow-y-auto pr-0.5">
      {/* sources */}
      <div className="panel p-3.5 anim-rise" style={{ animationDelay: "40ms" }}>
        <SectionHead icon={<IFilm className="w-3.5 h-3.5" />} title="Media sources" aside={`${ed.mediaSources.length} loaded`} />
        <div className="mb-3 flex flex-col gap-1.5">
          {ed.mediaSources.map((source) => (
            <button
              key={source.id}
              className="flex items-center gap-2 rounded border border-line bg-bg1/70 px-2 py-1.5 text-left hover:border-line2"
              onClick={() => source.type === "video" ? ed.setVideoPath(source.path) : ed.setAudioPath(source.path)}
              title="Use this source for the active tool"
            >
              <span className={source.type === "video" ? "text-amber" : "text-cyan"}>{source.type === "video" ? "V" : "A"}</span>
              <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-ink/80">{source.path.split(/[\\/]/).pop()}</span>
              <span className="font-mono text-[9px] text-faint">{source.duration > 0 ? `${source.duration.toFixed(1)}s` : "metadata"}</span>
              {source.type === "video" && source.path === ed.videoPath && <span className="text-[9px] text-mint">active</span>}
              {source.type === "video" && source.duration > 0 && (
                <span
                  className="font-mono text-[9px] text-amber"
                  onClick={(event) => { event.stopPropagation(); ed.addSourceToTimeline(source); }}
                >
                  + V1
                </span>
              )}
            </button>
          ))}
        </div>
        <label className="block mb-2">
          <span className="flex items-center justify-between text-[10.5px] font-display font-semibold tracking-wide text-dim mb-1">
            AUDIO <span className={`font-mono text-[9.5px] ${audioValid ? "text-mint" : "text-coral"}`}>{audioValid ? "resolved" : "bad ext"}</span>
          </span>
          <input
            className={`path-input ${audioValid ? "" : "invalid"}`}
            value={ed.audioPath}
            spellCheck={false}
            onChange={(e) => ed.setAudioPath(e.target.value)}
            placeholder={DEFAULT_AUDIO_PATH}
          />
        </label>
        <label className="block">
          <span className="flex items-center justify-between text-[10.5px] font-display font-semibold tracking-wide text-dim mb-1">
            VIDEO <span className={`font-mono text-[9.5px] ${videoValid ? "text-mint" : "text-coral"}`}>{videoValid ? "resolved" : "bad ext"}</span>
          </span>
          <input
            className={`path-input ${videoValid ? "" : "invalid"}`}
            value={ed.videoPath}
            spellCheck={false}
            onChange={(e) => ed.setVideoPath(e.target.value)}
            placeholder={DEFAULT_VIDEO_PATH}
          />
        </label>
        <label className="btn w-full justify-center mt-2 cursor-pointer">
          Load media file
          <input
            type="file"
            className="hidden"
            accept="video/*,audio/*"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0]).catch((error) => ed.log("err", error.message))}
          />
        </label>
        <p className="mt-2.5 flex gap-1.5 items-start text-[10px] leading-relaxed text-faint">
          <ICheck className="w-3 h-3 shrink-0 mt-0.5 text-mint" />
          Active sources are passed to every tool. Add more files to build a multi-source sequence.
        </p>
      </div>

      {/* AI tools */}
      <div className="panel p-3.5 anim-rise" style={{ animationDelay: "120ms" }}>
        <SectionHead icon={<IBolt className="w-3.5 h-3.5" />} title="AI tools" aside="iterative · reversible" />
        <div className="flex flex-col gap-2.5">
          {tools.map((t) => {
            const job = ed.jobs[t.id];
            return (
              <div
                key={t.id}
                className={`rounded-lg border border-line bg-bg1/70 p-3 transition-all duration-200 ${
                  job ? "border-line2 shadow-[0_0_24px_rgba(255,178,36,0.06)]" : "hover:border-line2"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`${t.color}`}>{t.icon}</span>
                  <span className="font-display font-semibold text-[13px]">{t.name}</span>
                  <button
                    className={`tool-run ml-auto ${t.border} ${t.color}`}
                    disabled={!t.ready || ed.busy}
                    onClick={() => ed.runTool(t.id)}
                  >
                    {job ? "running" : "Run"}
                  </button>
                </div>
                <p className="mt-1.5 text-[11px] leading-snug text-dim">{t.desc}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {t.params.map((p) => (
                    <span key={p} className="chip !text-[9.5px]">{p}</span>
                  ))}
                </div>
                {job ? (
                  <div className="mt-2.5">
                    <div className="flex items-center gap-2 text-[10px] font-mono text-dim">
                      <ISpinner className={`w-3 h-3 ${t.color}`} />
                      <span className="truncate">{job.status}</span>
                      <span className={`ml-auto ${t.color}`}>{Math.round(job.progress * 100)}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 rounded-full bg-bg0 overflow-hidden border border-line/60">
                      <div
                        className="h-full rounded-full progress-shimmer bg-amber/80 transition-[width] duration-200"
                        style={{ width: `${Math.max(4, job.progress * 100)}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <p className="mt-2 flex items-center gap-1.5 text-[9.5px] font-mono">
                    {t.ready ? (
                      <>
                        <ICheck className={`w-3 h-3 ${t.color}`} />
                        <span className="text-faint">{t.note}</span>
                      </>
                    ) : (
                      <>
                        <IAlert className="w-3 h-3 text-coral" />
                        <span className="text-coral/90">{t.readyHint}</span>
                      </>
                    )}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* versions */}
      <div className="panel p-3.5 anim-rise" style={{ animationDelay: "200ms" }}>
        <SectionHead icon={<IHistory className="w-3.5 h-3.5" />} title="Versions" aside={`${ed.versions.length} saved`} />
        {ed.versions.length === 0 ? (
          <p className="text-[10.5px] text-faint leading-relaxed">
            Every tool pass and structural edit is snapshotted here — roll back any step and keep cutting forward.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {ed.versions.map((v) => (
              <li key={v.id} className="flex items-center gap-2 group">
                <span className="w-1.5 h-1.5 rounded-full bg-amber/70 shrink-0" />
                <button
                  className="text-left text-[11.5px] font-display font-semibold text-ink/90 hover:text-amber transition-colors truncate"
                  onClick={() => ed.restoreVersion(v)}
                  title="Restore this version"
                >
                  {v.label}
                </button>
                <span className="ml-auto font-mono text-[9.5px] text-faint shrink-0">
                  {v.snapshot.clips.length} clips · {v.time}
                </span>
              </li>
            ))}
          </ul>
        )}
        <button className="btn w-full justify-center mt-3 !py-1.5" onClick={ed.resetProject}>
          <IReset className="w-3.5 h-3.5" /> Reset to full source
        </button>
      </div>
    </div>
  );
}
