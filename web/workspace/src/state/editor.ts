import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import {
  Aspect,
  Caption,
  Clip,
  FPS,
  SOURCE_DURATION,
  detectSilence,
  fmtSec,
  fmtTC,
  makeCaptions,
  talkClips,
} from "../engine/media";

/* ------------------------------------------------------------------ */
/*  Defaults — the two paths that previously broke tool execution.     */
/* ------------------------------------------------------------------ */
export const DEFAULT_AUDIO_PATH = "data/input/input_audio.mp3";
export const DEFAULT_VIDEO_PATH = "data/input/input_video.mkv";

let uid = 0;
const nextId = () => `c${++uid}`;

export interface Snapshot {
  clips: Clip[];
  aspect: Aspect;
  captions: Caption[] | null;
}

export type LogLevel = "info" | "ok" | "warn" | "err" | "tool";
export interface LogEntry {
  id: number;
  time: string;
  level: LogLevel;
  text: string;
}

export interface Version {
  id: number;
  label: string;
  time: string;
  snapshot: Snapshot;
}

export type ToolId = "silence" | "vertical" | "transcribe";
export interface JobState {
  progress: number;
  status: string;
}

export interface AgentResult {
  content?: string;
  output_files?: string[];
  output_path?: string;
  metadata?: {
    tool_results?: Array<{ output_path?: string; metadata?: { aspect_ratio?: string } }>;
  };
}

interface State {
  clips: Clip[];
  aspect: Aspect;
  captions: Caption[] | null;
  past: Snapshot[];
  future: Snapshot[];
}

type Action =
  | { type: "split"; at: number }
  | { type: "remove"; id: string }
  | { type: "trim"; id: string; side: "l" | "r"; delta: number; commit?: boolean }
  | { type: "apply"; snapshot: Snapshot }
  | { type: "restore"; snapshot: Snapshot }
  | { type: "undo" }
  | { type: "redo" };

const initialClips = (): Clip[] => [{ id: nextId(), src: 0, dur: SOURCE_DURATION }];

const init = (): State => ({
  clips: initialClips(),
  aspect: "16:9",
  captions: null,
  past: [],
  future: [],
});

const snap = (s: State): Snapshot => ({ clips: s.clips, aspect: s.aspect, captions: s.captions });
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "split": {
      const { at } = action;
      let acc = 0;
      const clips: Clip[] = [];
      let split = false;
      for (const c of state.clips) {
        const local = at - acc;
        if (!split && local > 0.05 && local < c.dur - 0.05) {
          clips.push({ id: nextId(), src: c.src, dur: local });
          clips.push({ id: nextId(), src: c.src + local, dur: c.dur - local });
          split = true;
        } else {
          clips.push(c);
        }
        acc += c.dur;
      }
      if (!split) return state;
      return { ...state, clips, past: [...state.past, snap(state)].slice(-60), future: [] };
    }
    case "remove": {
      if (state.clips.length <= 1) return state;
      const clips = state.clips.filter((c) => c.id !== action.id);
      if (clips.length === state.clips.length) return state;
      return { ...state, clips, past: [...state.past, snap(state)].slice(-60), future: [] };
    }
    case "trim": {
      const clips = state.clips.map((c) => {
        if (c.id !== action.id) return c;
        if (action.side === "l") {
          const d = clamp(action.delta, -c.src, c.dur - 0.25);
          return { ...c, src: c.src + d, dur: c.dur - d };
        }
        const d = clamp(action.delta, -(c.dur - 0.25), SOURCE_DURATION - c.src - c.dur);
        return { ...c, dur: c.dur + d };
      });
      const history =
        action.commit === false ? state.past : [...state.past, snap(state)].slice(-60);
      return { ...state, clips, past: history, future: action.commit === false ? state.future : [] };
    }
    case "apply":
    case "restore":
      return {
        ...state,
        ...action.snapshot,
        past: [...state.past, snap(state)].slice(-60),
        future: [],
      };
    case "undo": {
      if (!state.past.length) return state;
      const prev = state.past[state.past.length - 1];
      return {
        ...state,
        ...prev,
        past: state.past.slice(0, -1),
        future: [snap(state), ...state.future].slice(0, 60),
      };
    }
    case "redo": {
      if (!state.future.length) return state;
      const [next, ...rest] = state.future;
      return { ...state, ...next, future: rest, past: [...state.past, snap(state)].slice(-60) };
    }
    default:
      return state;
  }
}

/* ------------------------------- hook ------------------------------ */

const stamp = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

let logId = 0;

export function useEditor() {
  const [state, dispatch] = useReducer(reducer, undefined, init);
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState(1);
  const [loop, setLoop] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [showCaptions, setShowCaptions] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [jobs, setJobs] = useState<Partial<Record<ToolId, JobState>>>({});
  const [audioPath, setAudioPath] = useState(DEFAULT_AUDIO_PATH);
  const [videoPath, setVideoPath] = useState(DEFAULT_VIDEO_PATH);
  const [outputVideoPath, setOutputVideoPath] = useState<string | null>(null);

  const totalDuration = useMemo(
    () => state.clips.reduce((a, c) => a + c.dur, 0),
    [state.clips],
  );

  /** map timeline time → source time */
  const tl2src = useCallback(
    (tl: number) => {
      let acc = 0;
      for (const c of state.clips) {
        if (tl < acc + c.dur) return c.src + (tl - acc);
        acc += c.dur;
      }
      const last = state.clips[state.clips.length - 1];
      return last ? last.src + last.dur : 0;
    },
    [state.clips],
  );

  const log = useCallback((level: LogLevel, text: string) => {
    setLogs((ls) => [...ls.slice(-140), { id: ++logId, time: stamp(), level, text }]);
  }, []);

  /* boot log — documents the two fixed failures */
  useEffect(() => {
    log("err", "prev session · transcribe failed → Missing required parameters: input_path");
    log("ok", `fix · input_path default bound → ${DEFAULT_AUDIO_PATH}`);
    log("err", "prev session · video_split failed → audio file not found: data/input/input_audio.mp4");
    log("ok", "fix · audio extension corrected .mp4 → .mp3, path re-pointed");
    log("info", `project loaded · ${DEFAULT_VIDEO_PATH} · ${SOURCE_DURATION.toFixed(1)}s · ${FPS} fps`);
    log("info", "preview engine online — cut iteratively, every tool is reversible");
  }, [log]);

  /* ---------------------------- transport --------------------------- */

  const playingRef = useRef(playing);
  playingRef.current = playing;
  const rateRef = useRef(rate);
  rateRef.current = rate;
  const loopRef = useRef(loop);
  loopRef.current = loop;
  const totalRef = useRef(totalDuration);
  totalRef.current = totalDuration;

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      setPlayhead((p) => {
        let n = p + dt * rateRef.current;
        if (n >= totalRef.current) {
          if (loopRef.current) n = 0;
          else {
            setPlaying(false);
            return totalRef.current;
          }
        }
        if (n < 0) n = loopRef.current ? totalRef.current + n : 0;
        return n;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const togglePlay = useCallback(() => setPlaying((p) => !p), []);
  const stepFrame = useCallback(
    (frames: number) => {
      setPlaying(false);
      setPlayhead((p) => {
        const f = Math.round(p * FPS);
        return clamp((f + frames) / FPS, 0, totalRef.current);
      });
    },
    [],
  );
  const skip = useCallback(
    (to: "start" | "end") => {
      setPlaying(false);
      setPlayhead(to === "start" ? 0 : totalRef.current);
    },
    [],
  );

  /* ------------------------------ edits ----------------------------- */

  const splitAtPlayhead = useCallback(() => {
    const at = playhead;
    if (at <= 0.05 || at >= totalRef.current - 0.05) {
      log("warn", "split · playhead is at a sequence boundary — nothing to cut");
      return;
    }
    dispatch({ type: "split", at });
    log("tool", `blade · split clip at ${fmtTC(at)} on the timeline`);
  }, [playhead, log]);

  const removeSelected = useCallback(() => {
    if (!selected) {
      log("warn", "delete · no clip selected — click a segment on V1 first");
      return;
    }
    const clip = state.clips.find((c) => c.id === selected);
    dispatch({ type: "remove", id: selected });
    setSelected(null);
    if (clip) log("tool", `delete · removed segment src ${fmtTC(clip.src)}–${fmtTC(clip.src + clip.dur)} (ripple)`);
  }, [selected, state.clips, log]);

  const trim = useCallback(
    (id: string, side: "l" | "r", delta: number, commit = true) =>
      dispatch({ type: "trim", id, side, delta, commit }),
    [],
  );

  const undo = useCallback(() => {
    dispatch({ type: "undo" });
  }, []);
  const redo = useCallback(() => {
    dispatch({ type: "redo" });
  }, []);

  const canUndo = state.past.length > 0;
  const canRedo = state.future.length > 0;

  useEffect(() => {
    setPlayhead((p) => clamp(p, 0, totalDuration));
  }, [totalDuration]);

  /* ----------------------------- versions --------------------------- */

  const pushVersion = useCallback((label: string, snapshot: Snapshot) => {
    setVersions((v) => [{ id: ++logId, label, time: stamp(), snapshot }, ...v].slice(0, 12));
  }, []);

  const restoreVersion = useCallback(
    (v: Version) => {
      dispatch({ type: "restore", snapshot: v.snapshot });
      log("tool", `restore · rolled project back to “${v.label}”`);
    },
    [log],
  );

  /* ------------------------------ tools ----------------------------- */

  const busy = Object.keys(jobs).length > 0;
  const jobTimers = useRef<number[]>([]);
  useEffect(() => () => jobTimers.current.forEach(clearTimeout), []);

  const runJob = useCallback(
    (
      id: ToolId,
      steps: Array<[number, string]>,
      finish: () => void,
    ) => {
      const total = steps.reduce((a, [d]) => a + d, 0);
      let elapsed = 0;
      setJobs((j) => ({ ...j, [id]: { progress: 0, status: steps[0][1] } }));
      for (const [dur, status] of steps) {
        const at = elapsed;
        jobTimers.current.push(
          window.setTimeout(
            () => setJobs((j) => ({ ...j, [id]: { progress: Math.min(0.98, at / total), status } })),
            30,
          ),
        );
        elapsed += dur;
      }
      jobTimers.current.push(
        window.setTimeout(() => {
          const t = window.setTimeout(() => {
            setJobs((j) => {
              const rest = { ...j };
              delete rest[id];
              return rest;
            });
            finish();
          }, 260);
          jobTimers.current.push(t);
          setJobs((j) => ({ ...j, [id]: { progress: 1, status: "done" } }));
        }, elapsed),
      );
    },
    [],
  );

  const runTool = useCallback(
    (id: ToolId) => {
      if (busy) return;
      if (id === "silence") {
        const gaps = detectSilence();
        const gapTotal = gaps.reduce((a, [x, y]) => a + (y - x), 0);
        log("tool", `remove_silence(input_path="${audioPath}", threshold=-32dB, min_gap=0.65s)`);
        runJob(
          id,
          [
            [650, "decoding audio track…"],
            [800, "scanning waveform energy…"],
            [700, `flagging ${gaps.length} silent gaps…`],
            [750, "cutting + ripple delete…"],
          ],
          () => {
            const clips = talkClips();
            const kept = clips.reduce((a, c) => a + c.dur, 0);
            dispatch({ type: "apply", snapshot: { clips, aspect: state.aspect, captions: state.captions } });
            pushVersion("silence removed", { clips, aspect: state.aspect, captions: state.captions });
            setPlayhead(0);
            setSelected(null);
            log("ok", `silence removed · ${gaps.length} gaps (${fmtSec(gapTotal)}) cut · timeline now ${fmtSec(kept)}`);
          },
        );
      } else if (id === "vertical") {
        const target: Aspect = state.aspect === "9:16" ? "16:9" : "9:16";
        const preset = target === "9:16" ? "9:16_vertical" : "16:9_landscape";
        log("tool", `video_convert(input="${videoPath}", audio="${audioPath}", preset="${preset}")`);
        runJob(
          id,
          [
            [600, "probing container…"],
            [850, target === "9:16" ? "center-reframing shots…" : "restoring full frame…"],
            [750, target === "9:16" ? "rendering safe-area pass…" : "re-checking composition…"],
          ],
          () => {
            const snapshot: Snapshot = { clips: state.clips, aspect: target, captions: state.captions };
            dispatch({ type: "apply", snapshot });
            pushVersion(target === "9:16" ? "vertical 9:16" : "landscape 16:9", snapshot);
            if (target === "9:16") {
              const out = videoPath.replace(/(\.\w+)?$/, "_vertical_9x16.mkv").replace("data/input", "data/output");
              setOutputVideoPath(out);
              log("ok", `vertical conform ready · output → ${out}`);
            } else {
              setOutputVideoPath(null);
              log("ok", "conformed back to 16:9 · full frame restored on program out");
            }
          },
        );
      } else {
        log("tool", `transcribe(input_path="${audioPath}", model="asr-v2", punctuate=true)`);
        runJob(
          id,
          [
            [700, "extracting dialogue band…"],
            [950, "running ASR v2…"],
            [650, "aligning word timings…"],
          ],
          () => {
            const captions = makeCaptions();
            const snapshot: Snapshot = { clips: state.clips, aspect: state.aspect, captions };
            dispatch({ type: "apply", snapshot });
            pushVersion("AI captions", snapshot);
            log("ok", `transcript ready · ${captions.length} caption blocks · overlay enabled on program out`);
          },
        );
      }
    },
    [busy, audioPath, videoPath, state.clips, state.aspect, state.captions, log, runJob, pushVersion],
  );

  const resetProject = useCallback(() => {
    dispatch({
      type: "restore",
      snapshot: { clips: initialClips(), aspect: "16:9", captions: null },
    });
    setPlayhead(0);
    setSelected(null);
    log("info", "project reset · full 48s source back on the timeline");
  }, [log]);

  const applyAgentResult = useCallback(
    (result: AgentResult) => {
      const output = result.output_files?.find(Boolean) || result.output_path;
      if (!output) return;
      setOutputVideoPath(output);
      const isVertical =
        /vertical|9x16/i.test(output) ||
        result.metadata?.tool_results?.some((tool) => tool.metadata?.aspect_ratio === "9:16");
      if (isVertical && state.aspect !== "9:16") {
        const snapshot: Snapshot = { clips: state.clips, aspect: "9:16", captions: state.captions };
        dispatch({ type: "apply", snapshot });
        pushVersion("agent vertical conform", snapshot);
      }
      log("ok", `program out · ${output}`);
    },
    [state.aspect, state.clips, state.captions, pushVersion, log],
  );

  /* ------------------------------ export ---------------------------- */

  const exportEDL = useCallback(() => {
    let acc = 0;
    const edl = state.clips.map((c, i) => {
      const recStart = acc;
      acc += c.dur;
      return {
        event: i + 1,
        source_in: +c.src.toFixed(3),
        source_out: +(c.src + c.dur).toFixed(3),
        rec_in: +recStart.toFixed(3),
        rec_out: +acc.toFixed(3),
      };
    });
    const payload = {
      app: "FrameForge v2.1",
      project: "demo_reel.ffproj",
      source: { video: videoPath, audio: audioPath, fps: FPS, duration_s: SOURCE_DURATION },
      output: { aspect: state.aspect, duration_s: +totalDuration.toFixed(3) },
      edits: edl,
      captions: state.captions?.map((c) => ({ ...c, start: +c.start.toFixed(2), end: +c.end.toFixed(2) })) ?? [],
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "demo_reel_edl.json";
    a.click();
    URL.revokeObjectURL(url);
    log("ok", `export · EDL written → data/output/demo_reel_edl.json (${edl.length} events, ${fmtSec(totalDuration)})`);
  }, [state.clips, state.aspect, state.captions, audioPath, videoPath, totalDuration, log]);

  const exportVideo = useCallback(() => {
    if (!outputVideoPath) {
      log("warn", "export · no rendered Program Out video is available yet");
      return;
    }
    const dataPath = outputVideoPath.replace(/^.*?data[\\/]/, "").replace(/\\/g, "/");
    const a = document.createElement("a");
    a.href = `/data/${dataPath}`;
    a.download = dataPath.split("/").pop() || "program_out.mp4";
    a.click();
    log("ok", `export · Program Out video downloaded → ${outputVideoPath}`);
  }, [outputVideoPath, log]);

  return {
    // state
    clips: state.clips,
    aspect: state.aspect,
    captions: state.captions,
    playhead,
    setPlayhead: (v: number) => setPlayhead(clamp(v, 0, totalDuration)),
    playing,
    rate,
    loop,
    selected,
    setSelected,
    showCaptions,
    setShowCaptions,
    logs,
    log,
    versions,
    jobs,
    busy,
    audioPath,
    setAudioPath,
    videoPath,
    setVideoPath,
    outputVideoPath,
    setOutputVideoPath,
    totalDuration,
    canUndo,
    canRedo,
    tl2src,
    // actions
    togglePlay,
    stepFrame,
    skip,
    setRate,
    setLoop,
    splitAtPlayhead,
    removeSelected,
    trim,
    undo,
    redo,
    runTool,
    restoreVersion,
    resetProject,
    applyAgentResult,
    exportVideo,
    exportEDL,
  };
}

export type Editor = ReturnType<typeof useEditor>;
