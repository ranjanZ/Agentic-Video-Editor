import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import {
  Clip,
  PEAKS,
  PEAK_STEP,
  SILENCE_THRESHOLD,
  amplitude,
  drawContent,
  fmtTC,
} from "../engine/media";
import type { Editor } from "../state/editor";
import { IBlade, IRedo, ITrash, IUndo, IZoomIn, IZoomOut } from "./icons";

const GUTTER = 46;
const RULER_H = 26;
const V_H = 74;
const A_H = 58;
const TX_H = 26;

/* ------------------------- clip thumbnails ------------------------- */

const Thumb = memo(function Thumb({
  t,
  w,
  h,
}: {
  t: number;
  w: number;
  h: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let live = true;
    const draw = () => {
      const cv = ref.current;
      const ctx = cv?.getContext("2d");
      if (!cv || !ctx) return;
      const scale = Math.max(w / 1280, h / 720);
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate((w - 1280 * scale) / 2, (h - 720 * scale) / 2);
      ctx.scale(scale, scale);
      drawContent(ctx, t);
      ctx.restore();
    };
    draw();
    // redraw once webfonts arrive so burned-in titles use Space Grotesk
    if (document.fonts?.ready) document.fonts.ready.then(() => live && draw());
    return () => {
      live = false;
    };
  }, [t, w, h]);
  return <canvas ref={ref} width={w} height={h} className="block h-full" style={{ width: w }} />;
});

const ClipBlock = memo(function ClipBlock({
  clip,
  x,
  w,
  h,
  selected,
  onSelect,
  onScrub,
  onTrimStart,
}: {
  clip: Clip;
  x: number;
  w: number;
  h: number;
  selected: boolean;
  onSelect: (id: string) => void;
  onScrub: (e: React.PointerEvent) => void;
  onTrimStart: (e: React.PointerEvent, id: string, side: "l" | "r") => void;
}) {
  const thumbs = useMemo(() => {
    const n = Math.max(1, Math.round(w / 62));
    return Array.from({ length: n }, (_, i) => ({
      t: clip.src + ((i + 0.5) * clip.dur) / n,
      tw: Math.ceil(w / n),
      key: `${clip.id}-${clip.src.toFixed(2)}-${clip.dur.toFixed(2)}-${n}-${i}`,
    }));
  }, [clip.id, clip.src, clip.dur, w]);

  return (
    <div
      className={`clip-block absolute top-1 bottom-1 rounded-md overflow-hidden cursor-pointer group ${
        selected
          ? "ring-2 ring-amber shadow-[0_0_18px_rgba(255,178,36,0.35)]"
          : "ring-1 ring-line2/70 hover:ring-line2"
      }`}
      style={{ left: x, width: Math.max(8, w) }}
      onPointerDown={(e) => {
        onSelect(clip.id);
        onScrub(e);
      }}
      title={`${clip.sourceId || "source"} · src ${fmtTC(clip.src)} → ${fmtTC(clip.src + clip.dur)} · ${clip.dur.toFixed(2)}s`}
    >
      <div className="flex h-full">
        {thumbs.map((th) => (
          <Thumb key={th.key} t={th.t} w={th.tw} h={h - 8} />
        ))}
      </div>
      <div className="absolute inset-x-0 bottom-0 px-1.5 py-0.5 bg-gradient-to-t from-black/85 to-transparent">
        <span className="font-mono text-[9.5px] text-ink/85 tabular-nums truncate block">
          {fmtTC(clip.src).slice(3)}–{fmtTC(clip.src + clip.dur).slice(3)}
        </span>
      </div>
      {/* trim handles */}
      {(["l", "r"] as const).map((side) => (
        <div
          key={side}
          onPointerDown={(e) => onTrimStart(e, clip.id, side)}
          className={`absolute top-0 bottom-0 w-2 cursor-ew-resize z-10 flex items-center justify-center transition-colors ${
            side === "l" ? "left-0" : "right-0"
          } ${selected ? "bg-amber/80" : "bg-amber/0 group-hover:bg-amber/40"}`}
        >
          <div className="w-0.5 h-6 rounded bg-black/50" />
        </div>
      ))}
    </div>
  );
});

/* --------------------------- waveform track ------------------------ */

const WaveTrack = memo(function WaveTrack({
  width,
  pxPerSec,
  tl2src,
  height,
}: {
  width: number;
  pxPerSec: number;
  tl2src: (t: number) => number;
  height: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    const ctx = cv?.getContext("2d");
    if (!cv || !ctx) return;
    const W = Math.max(50, Math.min(2600, Math.floor(width)));
    cv.width = W;
    ctx.clearRect(0, 0, W, height);
    const mid = height / 2;
    for (let x = 0; x < W; x++) {
      const tl = (x / W) * width / pxPerSec;
      const src = tl2src(tl);
      const a = amplitude(src);
      const silent = a < SILENCE_THRESHOLD;
      const bh = Math.max(1.5, a * (height - 10));
      ctx.fillStyle = silent ? "rgba(90,107,130,0.35)" : "rgba(58,219,230,0.75)";
      ctx.fillRect(x, mid - bh / 2, 1, bh);
      if (silent) {
        ctx.fillStyle = "rgba(255,93,93,0.10)";
        ctx.fillRect(x, 0, 1, height);
      }
    }
    // silence threshold line
    ctx.strokeStyle = "rgba(255,93,93,0.35)";
    ctx.setLineDash([4, 5]);
    ctx.beginPath();
    ctx.moveTo(0, mid - SILENCE_THRESHOLD * (height - 10));
    ctx.lineTo(W, mid - SILENCE_THRESHOLD * (height - 10));
    ctx.stroke();
    ctx.setLineDash([]);
  }, [width, pxPerSec, tl2src, height]);
  return <canvas ref={ref} className="block w-full" style={{ height }} />;
});

/* ------------------------------ main ------------------------------- */

export default function Timeline({ ed }: { ed: Editor }) {
  const [pxPerSec, setPxPerSec] = useState(16);
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragTrim = useRef<null | { id: string; side: "l" | "r"; lastX: number; moved: boolean }>(null);
  const scrubbing = useRef(false);

  const offsets = useMemo(() => {
    const out: Array<{ clip: Clip; x: number; w: number }> = [];
    let acc = 0;
    for (const clip of ed.clips) {
      out.push({ clip, x: acc * pxPerSec, w: clip.dur * pxPerSec });
      acc += clip.dur;
    }
    return out;
  }, [ed.clips, pxPerSec]);

  const width = ed.totalDuration * pxPerSec;

  const timeFromClientX = (clientX: number) => {
    const el = scrollRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const x = clientX - rect.left + el.scrollLeft - GUTTER;
    return Math.min(ed.totalDuration, Math.max(0, x / pxPerSec));
  };

  const startScrub = (e: React.PointerEvent) => {
    scrubbing.current = true;
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    ed.setPlayhead(timeFromClientX(e.clientX));
  };
  const moveScrub = (e: React.PointerEvent) => {
    if (scrubbing.current) ed.setPlayhead(timeFromClientX(e.clientX));
  };
  const endScrub = () => {
    scrubbing.current = false;
  };

  const onTrimStart = (e: React.PointerEvent, id: string, side: "l" | "r") => {
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    dragTrim.current = { id, side, lastX: e.clientX, moved: false };
  };
  const onTrimMove = (e: React.PointerEvent) => {
    const d = dragTrim.current;
    if (!d) return;
    const dx = e.clientX - d.lastX;
    if (dx !== 0) d.moved = true;
    d.lastX = e.clientX;
    ed.trim(d.id, d.side, dx / pxPerSec, false);
  };
  const onTrimEnd = () => {
    const d = dragTrim.current;
    if (d && d.moved) ed.trim(d.id, d.side, 0, true);
    dragTrim.current = null;
  };

  /* caption segments mapped onto the timeline */
  const capSegs = useMemo(() => {
    if (!ed.captions) return [];
    const segs: Array<{ x: number; w: number; text: string }> = [];
    let acc = 0;
    for (const clip of ed.clips) {
      for (const cap of ed.captions) {
        const s = Math.max(cap.start, clip.src);
        const e2 = Math.min(cap.end, clip.src + clip.dur);
        if (e2 > s) segs.push({ x: (acc + (s - clip.src)) * pxPerSec, w: (e2 - s) * pxPerSec, text: cap.text });
      }
      acc += clip.dur;
    }
    return segs;
  }, [ed.captions, ed.clips, pxPerSec]);

  const rulerTicks = useMemo(() => {
    const ticks: Array<{ t: number; major: boolean }> = [];
    const step = pxPerSec >= 12 ? 1 : 2;
    for (let t = 0; t <= Math.ceil(ed.totalDuration); t += step) {
      if (t > ed.totalDuration + 0.01) break;
      ticks.push({ t, major: t % 5 === 0 });
    }
    return ticks;
  }, [ed.totalDuration, pxPerSec]);

  const selectedClip = ed.clips.find((c) => c.id === ed.selected);

  return (
    <section className="panel overflow-hidden anim-rise" style={{ animationDelay: "80ms" }}>
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2 px-3 py-2 border-b border-line">
        <h2 className="panel-title mr-1">Timeline</h2>
        <button className="btn btn-amber !py-1.5" onClick={ed.splitAtPlayhead} title="Split at playhead (S)">
          <IBlade className="w-3.5 h-3.5" /> Split
        </button>
        <button
          className="btn !py-1.5 !text-coral hover:!border-coral/50"
          onClick={ed.removeSelected}
          disabled={!ed.selected || ed.clips.length <= 1}
          title="Remove selected clip (Del)"
        >
          <ITrash className="w-3.5 h-3.5" /> Remove
        </button>
        <div className="w-px h-5 bg-line mx-1" />
        <button className="btn btn-ghost btn-icon" onClick={ed.undo} disabled={!ed.canUndo} title="Undo (Ctrl+Z)">
          <IUndo className="w-4 h-4" />
        </button>
        <button className="btn btn-ghost btn-icon" onClick={ed.redo} disabled={!ed.canRedo} title="Redo (Ctrl+Shift+Z)">
          <IRedo className="w-4 h-4" />
        </button>
        <div className="w-px h-5 bg-line mx-1" />
        <button
          className="btn btn-ghost btn-icon"
          onClick={() => setPxPerSec((z) => Math.max(6, z - 4))}
          title="Zoom out"
        >
          <IZoomOut className="w-4 h-4" />
        </button>
        <button
          className="btn btn-ghost btn-icon"
          onClick={() => setPxPerSec((z) => Math.min(44, z + 4))}
          title="Zoom in"
        >
          <IZoomIn className="w-4 h-4" />
        </button>

        <div className="ml-auto flex items-center gap-2">
          {selectedClip && (
            <span className="chip !text-amber !border-amber/30">
              sel · src {fmtTC(selectedClip.src).slice(3)}–{fmtTC(selectedClip.src + selectedClip.dur).slice(3)} ·{" "}
              {selectedClip.dur.toFixed(2)}s
            </span>
          )}
          <span className="chip">
            {ed.clips.length} clip{ed.clips.length !== 1 && "s"} · {fmtTC(ed.totalDuration)}
          </span>
        </div>
      </div>

      {/* tracks */}
      <div className="flex text-[10px]">
        {/* gutter */}
        <div className="shrink-0 border-r border-line bg-bg1" style={{ width: GUTTER }}>
          <div style={{ height: RULER_H }} className="border-b border-line flex items-center justify-end pr-2">
            <span className="font-mono text-faint">{Math.round(pxPerSec)}px/s</span>
          </div>
          <div style={{ height: V_H }} className="border-b border-line flex items-center justify-center">
            <span className="font-display font-bold text-amber">V1</span>
          </div>
          <div style={{ height: A_H }} className="border-b border-line flex items-center justify-center">
            <span className="font-display font-bold text-cyan">A1</span>
          </div>
          <div style={{ height: TX_H }} className="flex items-center justify-center">
            <span className="font-display font-bold text-sky">TX</span>
          </div>
        </div>

        {/* scrollable track area */}
        <div ref={scrollRef} className="relative flex-1 overflow-x-auto overflow-y-hidden">
          <div
            className="relative"
            style={{ width: width + GUTTER, minWidth: "100%" }}
            onPointerMove={(e) => {
              moveScrub(e);
              onTrimMove(e);
            }}
            onPointerUp={() => {
              endScrub();
              onTrimEnd();
            }}
            onPointerLeave={() => {
              endScrub();
              onTrimEnd();
            }}
          >
            {/* ruler */}
            <div
              className="relative border-b border-line cursor-ew-resize select-none bg-bg1/70"
              style={{ height: RULER_H, marginLeft: 0, width }}
              onPointerDown={startScrub}
            >
              {rulerTicks.map(({ t, major }) => (
                <div key={t} className="absolute top-0 bottom-0" style={{ left: t * pxPerSec }}>
                  <div className={`w-px h-full ${major ? "bg-line2" : "bg-line/70"}`} style={{ height: major ? "100%" : "55%", marginTop: major ? 0 : "45%" }} />
                  {major && (
                    <span className="absolute top-0.5 left-1 font-mono text-faint tabular-nums whitespace-nowrap">
                      {fmtTC(t).slice(3, 8)}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {/* V1 */}
            <div
              className="relative border-b border-line bg-[#0b111a]"
              style={{ height: V_H, width }}
              onPointerDown={startScrub}
            >
              {offsets.map(({ clip, x, w }) => (
                <ClipBlock
                  key={clip.id}
                  clip={clip}
                  x={x}
                  w={w}
                  h={V_H}
                  selected={ed.selected === clip.id}
                  onSelect={ed.setSelected}
                  onScrub={startScrub}
                  onTrimStart={onTrimStart}
                />
              ))}
            </div>

            {/* A1 */}
            <div
              className="relative border-b border-line bg-[#0a1219] overflow-hidden cursor-ew-resize"
              style={{ height: A_H, width }}
              onPointerDown={startScrub}
            >
              <WaveTrack width={width} pxPerSec={pxPerSec} tl2src={ed.tl2src} height={A_H} />
            </div>

            {/* TX */}
            <div
              className="relative bg-[#0b111a] cursor-ew-resize"
              style={{ height: TX_H, width }}
              onPointerDown={startScrub}
            >
              {ed.captions ? (
                capSegs.map((s, i) => (
                  <div
                    key={i}
                    className="absolute top-1 bottom-1 rounded-sm bg-sky/15 border border-sky/40 px-1.5 overflow-hidden flex items-center"
                    style={{ left: s.x, width: Math.max(6, s.w) }}
                    title={s.text}
                  >
                    <span className="font-mono text-[9px] text-sky/90 truncate whitespace-nowrap">{s.text}</span>
                  </div>
                ))
              ) : (
                <div className="h-full flex items-center px-2">
                  <span className="font-mono text-[9.5px] text-faint">
                    — no transcript yet · run “Transcribe dialogue” to populate TX
                  </span>
                </div>
              )}
            </div>

            {/* playhead */}
            <div
              className="absolute top-0 bottom-0 z-20 pointer-events-none"
              style={{ left: ed.playhead * pxPerSec, width: 0 }}
            >
              <div className="absolute top-0 bottom-0 -left-px w-0.5 bg-amber shadow-[0_0_10px_rgba(255,178,36,0.9)]" />
              <div className="absolute -top-0 -left-[7px] w-0 h-0 border-l-[7px] border-r-[7px] border-t-[9px] border-l-transparent border-r-transparent border-t-amber playhead-glow" />
            </div>
          </div>
        </div>
      </div>

      {/* status strip */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5 border-t border-line bg-bg1/60 font-mono text-[10px] text-faint">
        <span>
          playhead <span className="text-amber">{fmtTC(ed.playhead)}</span>
        </span>
        <span>
          source <span className="text-cyan">{fmtTC(ed.tl2src(ed.playhead))}</span>
        </span>
        <span className="hidden md:inline">
          drag clip edges to trim · click a clip to arm <kbd>Del</kbd> · <kbd>S</kbd> splits under the playhead
        </span>
        <span className="ml-auto hidden lg:inline">
                  silence floor <span className="text-coral">-32 dB</span> · source {ed.sourceDuration > 0 ? `ends ${fmtTC(ed.sourceDuration)}` : "duration loading"}
        </span>
      </div>
    </section>
  );
}
