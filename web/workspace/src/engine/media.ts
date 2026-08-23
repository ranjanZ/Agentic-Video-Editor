/* ------------------------------------------------------------------ */
/*  FrameForge media engine                                            */
/*  Procedural "source footage" rendered frame-by-frame on canvas,     */
/*  a deterministic dialogue waveform with real silence regions, and   */
/*  transcript generation. Everything the editor cuts against.         */
/* ------------------------------------------------------------------ */

export const FPS = 24;
export const SOURCE_DURATION = 48; // seconds of source footage
export const VW = 1280; // virtual content width
export const VH = 720; // virtual content height

export type Aspect = "16:9" | "9:16";

export interface Clip {
  id: string;
  sourceId?: string;
  src: number; // source in-point (s)
  dur: number; // duration (s)
}

export interface Caption {
  start: number; // source time (s)
  end: number;
  text: string;
}

/* ----------------------------- timecode ---------------------------- */

export function fmtTC(sec: number): string {
  const s = Math.max(0, sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = Math.floor(s % 60);
  const f = Math.floor((s - Math.floor(s)) * FPS);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(h)}:${p(m)}:${p(ss)}:${p(f)}`;
}

export function fmtSec(sec: number): string {
  return `${sec.toFixed(2)}s`;
}

/* --------------------------- deterministic rng --------------------- */

function mulberry(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ----------------------------- waveform ---------------------------- */
/* Dialogue bursts across the 48s source — the gaps are real silence.  */

export const TALK_REGIONS: Array<[number, number]> = [
  [0.6, 3.8],
  [4.7, 9.1],
  [10.3, 11.6],
  [13.0, 17.4],
  [18.6, 23.3],
  [25.1, 27.7],
  [28.9, 33.5],
  [34.8, 36.1],
  [37.4, 42.2],
  [43.5, 47.0],
];

export function amplitude(t: number): number {
  let env = 0;
  for (const [a, b] of TALK_REGIONS) {
    if (t >= a && t <= b) {
      const fade = Math.min(1, (t - a) / 0.18, (b - t) / 0.18);
      env = Math.max(env, Math.max(0, fade));
    }
  }
  if (env <= 0) return 0.012 + 0.008 * Math.sin(t * 7);
  const chatter =
    0.62 +
    0.24 * Math.sin(t * 11.7) * Math.sin(t * 5.3 + 1.2) +
    0.14 * Math.sin(t * 23.1 + 0.6);
  return Math.min(1, env * Math.max(0.12, chatter));
}

export function buildPeaks(step = 0.035): number[] {
  const n = Math.ceil(SOURCE_DURATION / step);
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    let mx = 0;
    const t0 = i * step;
    for (let j = 0; j < 4; j++) mx = Math.max(mx, amplitude(t0 + (j * step) / 4));
    out.push(mx);
  }
  return out;
}

export const PEAKS = buildPeaks();
export const PEAK_STEP = SOURCE_DURATION / PEAKS.length;
export const SILENCE_THRESHOLD = 0.07;
export const DEFAULT_SILENCE_THRESHOLD_DB = -32;

/** Detect contiguous silence stretches (>= minLen seconds). */
export function detectSilence(minLen = 0.65, thresholdDb = DEFAULT_SILENCE_THRESHOLD_DB): Array<[number, number]> {
  const threshold = Math.pow(10, thresholdDb / 20);
  const gaps: Array<[number, number]> = [];
  let start: number | null = null;
  for (let i = 0; i < PEAKS.length; i++) {
    const t = i * PEAK_STEP;
    if (PEAKS[i] < threshold) {
      if (start === null) start = t;
    } else if (start !== null) {
      if (t - start >= minLen) gaps.push([start, t]);
      start = null;
    }
  }
  if (start !== null && SOURCE_DURATION - start >= minLen) gaps.push([start, SOURCE_DURATION]);
  return gaps;
}

/** Clips that keep only the talking parts (with a small pad). */
export function talkClips(pad = 0.16, maxDuration = SOURCE_DURATION): Clip[] {
  const clips: Clip[] = [];
  TALK_REGIONS.forEach(([a, b], i) => {
    const start = Math.max(0, a - pad);
    const end = Math.min(maxDuration, b + pad);
    if (end <= start) return;
    clips.push({
      id: `talk-${i}`,
      src: start,
      dur: end - start,
    });
  });
  return clips.filter((c) => c.dur > 0.1);
}

/* ----------------------------- captions ---------------------------- */

const WORDS = [
  "every", "frame", "is", "a", "decision", "we", "cut", "on", "motion",
  "and", "let", "the", "rhythm", "breathe", "silence", "is", "not",
  "empty", "it", "holds", "the", "scene", "together", "trim", "until",
  "the", "beat", "lands", "then", "hold", "two", "frames", "longer",
  "the", "eye", "follows", "the", "light", "keep", "your", "in-points",
  "honest", "and", "your", "out-points", "brave", "this", "is", "how",
  "a", "story", "finds", "its", "pace",
];

export function makeCaptions(): Caption[] {
  const caps: Caption[] = [];
  let wi = 0;
  const rnd = mulberry(1337);
  for (const [a, b] of TALK_REGIONS) {
    let t = a;
    while (t < b - 0.25) {
      const len = Math.min(b - t, 1.6 + rnd() * 1.3);
      const count = 4 + Math.floor(rnd() * 4);
      const words: string[] = [];
      for (let k = 0; k < count; k++) {
        words.push(WORDS[wi % WORDS.length]);
        wi++;
      }
      words[0] = words[0][0].toUpperCase() + words[0].slice(1);
      caps.push({ start: t, end: Math.min(b, t + len), text: words.join(" ") });
      t += len + 0.12;
    }
  }
  return caps;
}

/* -------------------------- scene rendering ------------------------ */

const SCENES = [
  { name: "COLD OPEN", from: 0, to: 12 },
  { name: "INTERVIEW / A-CAM", from: 12, to: 24 },
  { name: "PRODUCT MACRO", from: 24, to: 36 },
  { name: "END CARD", from: 36, to: 48 },
];

export function sceneAt(t: number) {
  return SCENES.find((s) => t >= s.from && t < s.to) ?? SCENES[3];
}

function rr(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
}

/** Draw the 1280x720 virtual frame for source time t. */
export function drawContent(ctx: CanvasRenderingContext2D, t: number) {
  const scene = sceneAt(t);
  ctx.save();

  if (scene.name === "COLD OPEN") {
    const g = ctx.createLinearGradient(0, 0, VW, VH);
    g.addColorStop(0, "#08131f");
    g.addColorStop(1, "#0d2438");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, VW, VH);

    // drifting concentric rings
    const cx = VW * 0.72;
    const cy = VH * 0.46;
    for (let i = 6; i > 0; i--) {
      ctx.beginPath();
      ctx.arc(cx, cy, 40 + i * 62 + Math.sin(t * 0.9 + i) * 14, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255,178,36,${0.05 + i * 0.028})`;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    // sun disc
    const sy = VH * 0.42 - ((t % 12) / 12) * 60;
    const sg = ctx.createRadialGradient(cx, sy, 10, cx, sy, 150);
    sg.addColorStop(0, "rgba(255,207,107,0.95)");
    sg.addColorStop(0.5, "rgba(255,150,40,0.35)");
    sg.addColorStop(1, "rgba(255,150,40,0)");
    ctx.fillStyle = sg;
    ctx.beginPath();
    ctx.arc(cx, sy, 150, 0, Math.PI * 2);
    ctx.fill();

    // light sweep
    const sweep = ((t * 120) % (VW + 700)) - 350;
    const lg = ctx.createLinearGradient(sweep, 0, sweep + 320, VH);
    lg.addColorStop(0, "rgba(58,219,230,0)");
    lg.addColorStop(0.5, "rgba(58,219,230,0.10)");
    lg.addColorStop(1, "rgba(58,219,230,0)");
    ctx.fillStyle = lg;
    ctx.fillRect(0, 0, VW, VH);

    // title block
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#eaf2fb";
    ctx.font = "700 108px 'Space Grotesk', sans-serif";
    ctx.fillText("DEMO REEL", 84, VH * 0.46);
    ctx.fillStyle = "#ffb224";
    ctx.font = "700 34px 'Space Grotesk', sans-serif";
    ctx.fillText("— FIELD CUT v2", 88, VH * 0.46 + 54);
    ctx.fillStyle = "rgba(233,238,246,0.55)";
    ctx.font = "500 21px 'IBM Plex Mono', monospace";
    ctx.fillText("shot on location · graded in-studio · 24 fps", 88, VH * 0.46 + 96);

    // bottom ticker bar
    ctx.fillStyle = "rgba(255,178,36,0.9)";
    ctx.fillRect(84, VH - 96, VW - 168, 3);
    ctx.fillStyle = "rgba(233,238,246,0.5)";
    ctx.font = "500 17px 'IBM Plex Mono', monospace";
    ctx.fillText("FRAMEFORGE PICTURES · PRESENTS", 84, VH - 64);
  } else if (scene.name.startsWith("INTERVIEW")) {
    const g = ctx.createLinearGradient(0, 0, 0, VH);
    g.addColorStop(0, "#101c2a");
    g.addColorStop(1, "#1b2c3d");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, VW, VH);

    // bokeh
    const rnd = mulberry(42);
    for (let i = 0; i < 14; i++) {
      const bx = rnd() * VW;
      const by = rnd() * VH * 0.7;
      const br = 14 + rnd() * 46;
      const ph = t * 0.5 + i;
      ctx.beginPath();
      ctx.arc(bx + Math.sin(ph) * 10, by + Math.cos(ph * 0.7) * 8, br, 0, Math.PI * 2);
      ctx.fillStyle = i % 3 === 0 ? "rgba(255,178,36,0.09)" : "rgba(58,219,230,0.07)";
      ctx.fill();
    }

    // key light
    const kg = ctx.createRadialGradient(VW * 0.38, VH * 0.34, 40, VW * 0.38, VH * 0.34, 460);
    kg.addColorStop(0, "rgba(255,214,150,0.22)");
    kg.addColorStop(1, "rgba(255,214,150,0)");
    ctx.fillStyle = kg;
    ctx.fillRect(0, 0, VW, VH);

    // subject silhouette (subtle breathing)
    const breathe = Math.sin(t * 1.4) * 4;
    const hx = VW * 0.4;
    const hy = VH * 0.42 + breathe;
    ctx.fillStyle = "#0a141f";
    ctx.beginPath();
    ctx.arc(hx, hy, 92, 0, Math.PI * 2); // head
    ctx.fill();
    ctx.beginPath(); // shoulders
    ctx.moveTo(hx - 210, VH);
    ctx.quadraticCurveTo(hx - 190, hy + 130, hx, hy + 108);
    ctx.quadraticCurveTo(hx + 190, hy + 130, hx + 210, VH);
    ctx.closePath();
    ctx.fill();
    // rim light on head
    ctx.beginPath();
    ctx.arc(hx, hy, 92, -Math.PI * 0.85, -Math.PI * 0.15);
    ctx.strokeStyle = "rgba(58,219,230,0.5)";
    ctx.lineWidth = 3;
    ctx.stroke();

    // lower third
    const ltIn = Math.max(0, Math.min(1, (t - 12.6) * 2.2));
    ctx.save();
    ctx.translate(-(1 - ltIn) * 60, 0);
    ctx.globalAlpha = ltIn;
    ctx.fillStyle = "rgba(10,16,24,0.85)";
    rr(ctx, 84, VH - 170, 470, 86, 8);
    ctx.fill();
    ctx.fillStyle = "#ffb224";
    ctx.fillRect(84, VH - 170, 5, 86);
    ctx.fillStyle = "#eaf2fb";
    ctx.font = "600 30px 'Space Grotesk', sans-serif";
    ctx.fillText("ARI SOLBERG", 112, VH - 132);
    ctx.fillStyle = "rgba(233,238,246,0.6)";
    ctx.font = "400 19px 'IBM Plex Mono', monospace";
    ctx.fillText("director of photography", 112, VH - 104);
    ctx.restore();
  } else if (scene.name.startsWith("PRODUCT")) {
    ctx.fillStyle = "#070c14";
    ctx.fillRect(0, 0, VW, VH);

    // perspective floor grid
    ctx.strokeStyle = "rgba(58,219,230,0.16)";
    ctx.lineWidth = 1;
    const horizon = VH * 0.62;
    for (let i = 0; i < 16; i++) {
      const z = ((i * 60 + t * 90) % 960) / 960;
      const y = horizon + z * z * (VH - horizon);
      ctx.globalAlpha = z;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(VW, y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (let i = -8; i <= 8; i++) {
      ctx.beginPath();
      ctx.moveTo(VW / 2 + i * 40, horizon);
      ctx.lineTo(VW / 2 + i * 260, VH);
      ctx.strokeStyle = "rgba(58,219,230,0.10)";
      ctx.stroke();
    }

    // rotating wireframe cube
    const cx = VW / 2;
    const cy = VH * 0.4;
    const a = t * 0.9;
    const b = t * 0.55;
    const S = 130;
    const verts = [-1, 1]
      .flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) => [x * S, y * S, z * S])));
    const proj = verts.map(([x, y, z]) => {
      const x1 = x * Math.cos(a) - z * Math.sin(a);
      const z1 = x * Math.sin(a) + z * Math.cos(a);
      const y1 = y * Math.cos(b) - z1 * Math.sin(b);
      const z2 = y * Math.sin(b) + z1 * Math.cos(b);
      const d = 560 / (560 + z2);
      return [cx + x1 * d, cy + y1 * d, z2] as const;
    });
    const edges = [
      [0, 1], [1, 3], [3, 2], [2, 0],
      [4, 5], [5, 7], [7, 6], [6, 4],
      [0, 4], [1, 5], [2, 6], [3, 7],
    ];
    ctx.lineWidth = 2;
    for (const [i, j] of edges) {
      const depth = (proj[i][2] + proj[j][2]) / 2;
      const al = 0.75 - (depth / S) * 0.35;
      ctx.strokeStyle = `rgba(255,178,36,${Math.max(0.2, al)})`;
      ctx.beginPath();
      ctx.moveTo(proj[i][0], proj[i][1]);
      ctx.lineTo(proj[j][0], proj[j][1]);
      ctx.stroke();
    }
    // orbiting sparks
    for (let i = 0; i < 26; i++) {
      const ang = t * (0.8 + (i % 5) * 0.13) + i * 2.4;
      const rad = 200 + (i % 4) * 34;
      const px = cx + Math.cos(ang) * rad;
      const py = cy + Math.sin(ang) * rad * 0.42;
      ctx.beginPath();
      ctx.arc(px, py, 2.2, 0, Math.PI * 2);
      ctx.fillStyle = i % 3 ? "rgba(58,219,230,0.8)" : "rgba(255,178,36,0.85)";
      ctx.fill();
    }
    ctx.fillStyle = "rgba(233,238,246,0.9)";
    ctx.font = "700 44px 'Space Grotesk', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("BUILT FRAME BY FRAME", cx, VH * 0.78);
    ctx.textAlign = "left";
  } else {
    // END CARD
    ctx.fillStyle = "#05080d";
    ctx.fillRect(0, 0, VW, VH);
    const roll = (t - 36) * 46;
    const credits = [
      "DEMO REEL", "—————", "direction  ·  frameforge studio",
      "edit  ·  iterative cut engine", "grade  ·  amber / cyan split",
      "sound  ·  dialogue + room tone", "silence removed  ·  automatically",
      "captions  ·  ai transcript v2", "conformed  ·  9:16 vertical",
      "—————", "made with frameforge", "fin.",
    ];
    ctx.textAlign = "center";
    credits.forEach((line, i) => {
      const y = VH * 0.9 + i * 64 - roll;
      if (y < -40 || y > VH + 40) return;
      ctx.fillStyle = i === 0 ? "#ffb224" : "rgba(233,238,246,0.82)";
      ctx.font = i === 0 ? "700 56px 'Space Grotesk', sans-serif" : "500 24px 'IBM Plex Mono', monospace";
      ctx.fillText(line, VW / 2, y);
    });
    ctx.textAlign = "left";
  }
  ctx.restore();
}

/* --------------------------- full frame ---------------------------- */

export interface FrameOpts {
  aspect: Aspect;
  captions: Caption[] | null;
  showCaptions: boolean;
  playing: boolean;
}

/** Render a complete output frame into a WxH canvas (cover-scaled). */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  W: number,
  H: number,
  t: number,
  opts: FrameOpts,
) {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#05080d";
  ctx.fillRect(0, 0, W, H);

  const scale = Math.max(W / VW, H / VH); // cover → simulated reframe
  ctx.save();
  ctx.translate((W - VW * scale) / 2, (H - VH * scale) / 2);
  ctx.scale(scale, scale);
  drawContent(ctx, t);
  ctx.restore();

  // burn-in timecode + meta (canvas space)
  const frame = Math.floor(t * FPS);
  ctx.font = `600 ${Math.max(11, Math.round(H * 0.026))}px 'IBM Plex Mono', monospace`;
  ctx.fillStyle = "rgba(233,238,246,0.85)";
  ctx.fillText(`TC ${fmtTC(t)}`, Math.round(W * 0.03), H - Math.round(H * 0.035));
  ctx.fillStyle = "rgba(233,238,246,0.45)";
  ctx.textAlign = "right";
  ctx.fillText(`${sceneAt(t).name} · F${String(frame).padStart(4, "0")}`, W - Math.round(W * 0.03), H - Math.round(H * 0.035));
  ctx.textAlign = "left";

  // vertical safe-area guides
  if (opts.aspect === "9:16") {
    ctx.strokeStyle = "rgba(255,178,36,0.35)";
    ctx.setLineDash([7, 7]);
    ctx.lineWidth = 1;
    rr(ctx, W * 0.05, H * 0.06, W * 0.9, H * 0.88, 10);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(255,178,36,0.6)";
    ctx.font = "600 11px 'IBM Plex Mono', monospace";
    ctx.fillText("9:16 SAFE ACTION", W * 0.05 + 8, H * 0.06 + 18);
  }

  // captions overlay
  if (opts.showCaptions && opts.captions) {
    const cap = opts.captions.find((c) => t >= c.start && t <= c.end);
    if (cap) {
      const size = Math.max(13, Math.round(H * 0.034));
      ctx.font = `600 ${size}px 'IBM Plex Sans', sans-serif`;
      const tw = ctx.measureText(cap.text).width;
      const bw = Math.min(W * 0.92, tw + size * 1.6);
      const bx = (W - bw) / 2;
      const by = H * (opts.aspect === "9:16" ? 0.74 : 0.82);
      ctx.fillStyle = "rgba(5,8,13,0.78)";
      rr(ctx, bx, by - size * 1.5, bw, size * 2.2, 7);
      ctx.fill();
      ctx.strokeStyle = "rgba(255,178,36,0.5)";
      ctx.lineWidth = 1;
      rr(ctx, bx, by - size * 1.5, bw, size * 2.2, 7);
      ctx.stroke();
      ctx.fillStyle = "#f4f8fd";
      ctx.textAlign = "center";
      ctx.fillText(cap.text, W / 2, by, bw - 16);
      ctx.textAlign = "left";
    }
  }

  // film grain
  const seed = Math.floor(t * FPS) * 7919 + 17;
  const rnd = mulberry(seed);
  ctx.fillStyle = "rgba(255,255,255,0.045)";
  const grains = Math.round((W * H) / 9000);
  for (let i = 0; i < grains; i++) {
    ctx.fillRect(Math.floor(rnd() * W), Math.floor(rnd() * H), 1.4, 1.4);
  }

  // vignette
  const vg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.42, W / 2, H / 2, Math.max(W, H) * 0.78);
  vg.addColorStop(0, "rgba(0,0,0,0)");
  vg.addColorStop(1, "rgba(0,0,0,0.42)");
  ctx.fillStyle = vg;
  ctx.fillRect(0, 0, W, H);

  // playing indicator
  if (opts.playing) {
    ctx.fillStyle = "#ff5d5d";
    ctx.beginPath();
    ctx.arc(Math.round(W * 0.03) + 5, Math.round(H * 0.05) + 5, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(233,238,246,0.8)";
    ctx.font = "600 12px 'IBM Plex Mono', monospace";
    ctx.fillText("PREVIEW", Math.round(W * 0.03) + 16, Math.round(H * 0.05) + 9);
  }
}
