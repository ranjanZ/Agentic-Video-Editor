import React from "react";

type P = { className?: string };
const base = (className?: string) => ({
  className: className ?? "w-4 h-4",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  viewBox: "0 0 24 24",
});

export const IPlay = ({ className }: P) => (
  <svg {...base(className)} fill="currentColor" stroke="none">
    <path d="M7 4.5v15l13-7.5-13-7.5z" />
  </svg>
);
export const IPause = ({ className }: P) => (
  <svg {...base(className)} fill="currentColor" stroke="none">
    <rect x="6" y="4.5" width="4" height="15" rx="1" />
    <rect x="14" y="4.5" width="4" height="15" rx="1" />
  </svg>
);
export const IStepBack = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M18 5v14L8 12l10-7z" fill="currentColor" stroke="none" />
    <line x1="6" y1="5" x2="6" y2="19" />
  </svg>
);
export const IStepFwd = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M6 5v14l10-7L6 5z" fill="currentColor" stroke="none" />
    <line x1="18" y1="5" x2="18" y2="19" />
  </svg>
);
export const ISkipStart = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M19 5v14L9 12l10-7z" fill="currentColor" stroke="none" />
    <path d="M8 5v14" />
    <path d="M5 5v14" />
  </svg>
);
export const ISkipEnd = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M5 5v14l10-7L5 5z" fill="currentColor" stroke="none" />
    <path d="M16 5v14" />
    <path d="M19 5v14" />
  </svg>
);
export const ILoop = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M17 2l4 4-4 4" />
    <path d="M3 11v-1a4 4 0 0 1 4-4h14" />
    <path d="M7 22l-4-4 4-4" />
    <path d="M21 13v1a4 4 0 0 1-4 4H3" />
  </svg>
);
export const IBlade = ({ className }: P) => (
  <svg {...base(className)}>
    <circle cx="6" cy="6" r="2.4" />
    <circle cx="6" cy="18" r="2.4" />
    <path d="M8.1 7.6L20 19.5M8.1 16.4L20 4.5" />
  </svg>
);
export const ITrash = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <line x1="10" y1="11" x2="10" y2="17" />
    <line x1="14" y1="11" x2="14" y2="17" />
  </svg>
);
export const IUndo = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M3 7v6h6" />
    <path d="M21 17a9 9 0 0 0-15-6.7L3 13" />
  </svg>
);
export const IRedo = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M21 7v6h-6" />
    <path d="M3 17a9 9 0 0 1 15-6.7L21 13" />
  </svg>
);
export const IZoomIn = ({ className }: P) => (
  <svg {...base(className)}>
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.5" y2="16.5" />
    <line x1="8" y1="11" x2="14" y2="11" />
    <line x1="11" y1="8" x2="11" y2="14" />
  </svg>
);
export const IZoomOut = ({ className }: P) => (
  <svg {...base(className)}>
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.5" y2="16.5" />
    <line x1="8" y1="11" x2="14" y2="11" />
  </svg>
);
export const IWand = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M15 4V2M15 10V8M11 6H9M21 6h-2M17.8 3.2l-1.4 1.4M17.8 8.8l-1.4-1.4M12.2 3.2l1.4 1.4" />
    <path d="M3 21L13.5 10.5l1.5 1.5L4.5 22.5 3 21z" fill="currentColor" stroke="none" />
    <path d="M13.5 10.5L15 12" />
  </svg>
);
export const IRatio = ({ className }: P) => (
  <svg {...base(className)}>
    <rect x="8" y="3" width="8" height="18" rx="1.5" />
    <path d="M4 8v8M20 8v8" strokeDasharray="2 3" />
  </svg>
);
export const ICaptions = ({ className }: P) => (
  <svg {...base(className)}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M7 12h4M13 12h4M7 15.5h7" />
  </svg>
);
export const IDownload = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M12 3v12M7 10l5 5 5-5" />
    <path d="M4 19h16" />
  </svg>
);
export const IFilm = ({ className }: P) => (
  <svg {...base(className)}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
  </svg>
);
export const IWave = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M2 12h2l2-7 3 14 3-10 2 6 2-3h6" />
  </svg>
);
export const IAlert = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M12 3L2 20h20L12 3z" />
    <line x1="12" y1="10" x2="12" y2="14" />
    <circle cx="12" cy="17" r="0.4" fill="currentColor" />
  </svg>
);
export const ICheck = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M4 12.5l5 5L20 6.5" />
  </svg>
);
export const IHistory = ({ className }: P) => (
  <svg {...base(className)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3.5 2" />
  </svg>
);
export const IReset = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 3v5h5" />
  </svg>
);
export const IBolt = ({ className }: P) => (
  <svg {...base(className)} fill="currentColor" stroke="none">
    <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" />
  </svg>
);
export const ISpinner = ({ className }: P) => (
  <svg {...base(`spinner ${className ?? "w-4 h-4"}`)}>
    <path d="M21 12a9 9 0 1 1-6.2-8.56" />
  </svg>
);
