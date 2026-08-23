import { useEffect, useRef } from "react";
import { drawFrame } from "../engine/media";
import type { Editor } from "../state/editor";
import { fmtTC } from "../engine/media";
import {
  ICaptions,
  ILoop,
  IPause,
  IPlay,
  ISkipEnd,
  ISkipStart,
  IStepBack,
  IStepFwd,
} from "./icons";

export default function Monitor({ ed }: { ed: Editor }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tcMainRef = useRef<HTMLSpanElement>(null);
  const tcSrcRef = useRef<HTMLSpanElement>(null);

  const live = useRef({
    playhead: ed.playhead,
    aspect: ed.aspect,
    captions: ed.captions,
    showCaptions: ed.showCaptions,
    playing: ed.playing,
    tl2src: ed.tl2src,
  });
  live.current = {
    playhead: ed.playhead,
    aspect: ed.aspect,
    captions: ed.captions,
    showCaptions: ed.showCaptions,
    playing: ed.playing,
    tl2src: ed.tl2src,
  };

  useEffect(() => {
    let raf = 0;
    const loop = () => {
      const cv = canvasRef.current;
      const ctx = cv?.getContext("2d");
      if (cv && ctx) {
        const l = live.current;
        const W = cv.width;
        const H = cv.height;
        drawFrame(ctx, W, H, l.tl2src(l.playhead), {
          aspect: l.aspect,
          captions: l.captions,
          showCaptions: l.showCaptions,
          playing: l.playing,
        });
        if (tcMainRef.current) tcMainRef.current.textContent = fmtTC(l.playhead);
        if (tcSrcRef.current) tcSrcRef.current.textContent = `SRC ${fmtTC(l.tl2src(l.playhead))}`;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  const vertical = ed.aspect === "9:16";
  const toMediaUrl = (path: string) => {
    const dataPath = path.replace(/^.*?data[\\/]/, "").replace(/\\/g, "/");
    return `/data/${dataPath}`;
  };
  const outputUrl = ed.outputVideoPath ? toMediaUrl(ed.outputVideoPath) : null;
  const sourceUrl = /\.(mp4|webm|mov)$/i.test(ed.videoPath)
    ? toMediaUrl(ed.videoPath)
    : `/api/media/preview/${encodeURIComponent(ed.videoPath.split(/[\\/]/).pop() || "source.mkv")}`;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onLoaded = () => {
      video.currentTime = Math.min(ed.playhead, video.duration || ed.totalDuration);
    };
    video.addEventListener("loadedmetadata", onLoaded);
    return () => video.removeEventListener("loadedmetadata", onLoaded);
  }, [outputUrl, sourceUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (Math.abs(video.currentTime - ed.playhead) > 0.08) {
      video.currentTime = Math.min(ed.playhead, video.duration || ed.totalDuration);
    }
    if (ed.playing && video.paused) void video.play().catch(() => undefined);
    if (!ed.playing && !video.paused) video.pause();
  }, [ed.playing, ed.playhead, ed.totalDuration]);

  return (
    <section className="panel overflow-hidden anim-rise">
      {/* monitor header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-line">
        <div className="flex items-center gap-2.5">
          <span
            className={`w-2 h-2 rounded-full ${ed.playing ? "bg-coral rec-dot" : "bg-faint"}`}
          />
          <h2 className="panel-title !text-ink">Program Out</h2>
          <span className="chip">{ed.aspect}</span>
          {ed.captions && (
            <span className="chip !text-sky !border-sky/30">CC · {ed.captions.length}</span>
          )}
        </div>
        <button
          className={`btn btn-icon !p-1.5 ${ed.showCaptions ? "btn-on" : ""}`}
          onClick={() => ed.setShowCaptions(!ed.showCaptions)}
          title="Toggle caption overlay (C)"
        >
          <ICaptions className="w-4 h-4" />
        </button>
      </div>

      {/* picture */}
      <div className="relative flex items-center justify-center bg-[#05080d] px-4 py-4">
        <div
          className="relative transition-all duration-500"
          style={{
            aspectRatio: vertical ? "9 / 16" : "16 / 9",
            height: vertical ? "min(46vh, 460px)" : "auto",
            width: vertical ? "auto" : "100%",
            maxWidth: vertical ? "none" : "100%",
          }}
        >
          {outputUrl || sourceUrl ? (
            <video
              ref={videoRef}
              src={outputUrl || sourceUrl}
              controls
              className="w-full h-full block rounded-md shadow-[0_0_60px_rgba(0,0,0,0.6)] object-contain bg-black"
              onTimeUpdate={(event) => ed.setPlayhead(event.currentTarget.currentTime)}
              onPlay={() => {
                if (!ed.playing) ed.togglePlay();
              }}
              onPause={() => {
                if (ed.playing) ed.togglePlay();
              }}
            />
          ) : (
            <canvas
              ref={canvasRef}
              width={vertical ? 540 : 960}
              height={vertical ? 960 : 540}
              className="w-full h-full block rounded-md shadow-[0_0_60px_rgba(0,0,0,0.6)]"
            />
          )}
          {/* corner frame marks */}
          <div className="pointer-events-none absolute inset-0 rounded-md ring-1 ring-white/10" />
        </div>
      </div>

      {/* transport */}
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-t border-line bg-bg1/60">
        {outputUrl && (
          <a className="btn btn-amber" href={outputUrl} download title="Download the current Program Out video">
            Download output
          </a>
        )}
        <div className="flex items-center gap-1">
          <button className="btn btn-ghost btn-icon" onClick={() => ed.skip("start")} title="Go to start">
            <ISkipStart className="w-4 h-4" />
          </button>
          <button className="btn btn-ghost btn-icon" onClick={() => ed.stepFrame(-1)} title="Previous frame (←)">
            <IStepBack className="w-4 h-4" />
          </button>
          <button
            className={`btn btn-icon !px-4 !py-2 ${ed.playing ? "btn-amber" : ""}`}
            onClick={ed.togglePlay}
            title="Play / pause (Space)"
          >
            {ed.playing ? <IPause className="w-5 h-5" /> : <IPlay className="w-5 h-5" />}
          </button>
          <button className="btn btn-ghost btn-icon" onClick={() => ed.stepFrame(1)} title="Next frame (→)">
            <IStepFwd className="w-4 h-4" />
          </button>
          <button className="btn btn-ghost btn-icon" onClick={() => ed.skip("end")} title="Go to end">
            <ISkipEnd className="w-4 h-4" />
          </button>
        </div>

        <button
          className={`btn ${ed.loop ? "btn-on" : ""}`}
          onClick={() => ed.setLoop(!ed.loop)}
          title="Loop playback"
        >
          <ILoop className="w-3.5 h-3.5" />
          loop
        </button>

        {/* rate */}
        <div className="flex items-center border border-line rounded-md overflow-hidden">
          {[-2, 1, 2].map((r) => (
            <button
              key={r}
              onClick={() => {
                ed.setRate(r);
                if (r !== 0 && !ed.playing) ed.togglePlay();
              }}
              className={`px-2.5 py-1.5 font-mono text-[11px] transition-colors ${
                ed.rate === r && ed.playing
                  ? "bg-amber/15 text-amber"
                  : "text-dim hover:text-ink hover:bg-bg2"
              }`}
              title={r < 0 ? "Reverse (J)" : r === 1 ? "Play (L)" : "Double speed (LL)"}
            >
              {r < 0 ? "«" : r === 1 ? "►" : "»"}
            </button>
          ))}
        </div>

        {/* timecode */}
        <div className="ml-auto flex items-baseline gap-3">
          <span ref={tcSrcRef} className="font-mono text-[11px] text-faint tabular-nums">
            SRC 00:00:00:00
          </span>
          <span className="font-mono font-semibold text-xl text-amber tabular-nums tracking-tight leading-none">
            <span ref={tcMainRef}>00:00:00:00</span>
          </span>
          <span className="font-mono text-[11px] text-faint tabular-nums">/ {fmtTC(ed.totalDuration)}</span>
        </div>
      </div>
    </section>
  );
}
