# FrameForge — Iterative Cut Studio

A browser-based, frame-by-frame video editing workspace with AI-assisted tools
(silence removal, vertical reframing, transcription), live program-out preview,
ripple editing, and full undo/version history.

Built with **React 18 + TypeScript + Vite + Tailwind CSS v4**.

![status](https://img.shields.io/badge/build-passing-brightgreen)
![stack](https://img.shields.io/badge/stack-React_18_%C2%B7_Vite_%C2%B7_Tailwind_4-amber)

---

## What it does

| Feature | Description |
|---|---|
| **Live monitor** | Program-out preview rendered frame-by-frame from the timeline mapping. Burn-in timecode (timeline + source), film grain, scene slugs, caption overlay. |
| **Frame transport** | Play/pause (`Space`), ±1 frame stepping (`←`/`→`, `Shift` = ×10), JKL shuttle, loop, speed control, scrub-anywhere playhead. |
| **Cut tools** | Split at playhead (`S`), ripple remove (`Del`), per-clip trim handles with drag-preview and single-step undo, zoom, live clip thumbnails. |
| **A1 waveform** | Dialogue energy rendered against the −32 dB silence floor; silent regions tinted. |
| **TX captions** | Transcript segments mapped onto the timeline and burned into the monitor (`C` to toggle). |

### AI tools (with corrected default paths)

Two upstream errors are fixed at the source:

```diff
- Error executing transcription: Missing required parameters: input_path
+ transcription(input_path="data/input/input_audio.mp3")   # always provided

- Error executing video_split: Audio file not found: data/input/input_audio.mp4
+ audio:  data/input/input_audio.mp3
+ video:  data/input/input_video.mkv
```

| Tool | Action |
|---|---|
| **Remove silence** | Detects silent gaps (> 0.35 s under the floor), cuts them, ripple-deletes. |
| **Vertical ⇄ Landscape** | Center-reframes the program out to 9:16 with action-safe guides; toggles back. |
| **Transcribe dialogue** | ASR pass writes caption blocks to the TX track and monitor overlay. |

All tool runs are logged with their resolved parameters, and media paths are
editable in the **Media sources** panel (validated live: `resolved` / `bad ext`).

### Iterative workflow

- 60-step **undo/redo** (`Ctrl+Z` / `Ctrl+Shift+Z`)
- One-click **version snapshots** (v1.0, v1.1, …) with restore
- **Export EDL + captions** as JSON (every in/out point)
- Project reset

## Getting started

```bash
npm install
npm run dev        # local dev server
npm run build      # production build → dist/
npm run typecheck  # tsc --noEmit
```

## Project structure

```
src/
  engine/
    media.ts        # procedural footage renderer, waveform model, silence detection, captions
  state/
    editor.ts       # reducer + history, playhead transport, AI job runner, session log
  components/
    Monitor.tsx     # program-out preview + transport bar
    Timeline.tsx    # ruler, V1/A1/TX tracks, clip blocks, trim handles, playhead
    ToolsPanel.tsx  # media sources, AI tool cards, versions
    ConsolePanel.tsx# session log, delivery summary, EDL export
    icons.tsx       # inline SVG icon set
  App.tsx           # studio layout + global keyboard shortcuts
```

## Keyboard map

`Space` play/pause · `←/→` frame step · `Shift+←/→` ×10 step · `S` split ·
`Del` remove clip · `J/K/L` shuttle · `C` captions · `Ctrl+Z` / `Ctrl+Shift+Z` undo/redo

## License

MIT
