# FRONTEND_SPEC.md - Synapse "Luxury Wellness" UI (engineering specification for Cline)

> Save as `docs/FRONTEND_SPEC.md`. Cline MUST read `.clinerules` first; where this file conflicts with `.clinerules` or `assignment-pharma.pdf`, STOP and ask. The graded contract (`GET /health`, `POST /ask`, self-contained container, one image, port 8000) is untouched. Every backend change below is **additive and optional**.

---

# 0. Scope, sequencing, decisions

## 0.1 What this replaces

This spec replaces Task 9 (minimal UI), the UI half of Task 12 (trace panel), Task 13 (interactive citations) and the UI half of Task 14. It is delivered in phases A-G (Section 8). Each phase ends with `npm run build`, `pytest`, and Docker still green, and its own commit.

## 0.2 Priorities and cut line

| Tier | Features                                                                                                                                     | If behind schedule |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| MUST | Phase A (API), B (foundation, theme, layout), C (chat, ask bar, history, answer card, disclaimer), D (source badges, modal, cross-highlight) | Never cut          |
| MUST | Footer, reading time + progress bar, Stage timeline (real events), mobile drawers, safe-area/keyboard handling                               | Never cut          |
| MUST | Zen mode, haptics, hover cross-sync between chips and trace panel                                                                            | Never cut          |

Hard rule: run Docker (Task 10) and push the baseline (Task 11) after Phase C. Phases D-G are improvements on top of a submittable build.

## 0.3 Decisions that clarify the brief (do not silently change)

1. **Source text is NOT added to `/ask`.** Twenty-one files per response would bloat every answer and defeat caching. A new read-only `GET /api/v1/sources/{file_name}` serves the Markdown plus per-chunk character spans. `/ask` only gains small optional fields (`retrieval`, `trace`).
2. **Honest progress only.** The "Stream of Thought" card renders REAL stage events from `POST /ask/stream`. If streaming is unavailable it shows an indeterminate "Working..." state, then the completed timeline from `response.trace`. Never simulate stages with timers.
3. **Sessions are a UI grouping.** The backend has no conversation memory; every question is answered independently from the corpus. Never send earlier turns. Show a one-line hint ("Each question is answered independently from the corpus").
4. **Palette is exactly nine hex values** (Section 3). No other hues. Neutral tints/shades come only from `color-mix()` of palette colors with white or black. Sidebars and drawers are `#243341` in BOTH themes; in dark mode they are a deeper mix so they stay distinguishable.
5. **Contrast corrections.** Ocean `#205D96` has only ~1.9:1 against `#243341`, so it is never used for text/focus rings on dark surfaces: Glacial `#B5DBFF` is the accent there (~9:1). Sage `#519A76` is ~3.8:1 on night and ~3:1 on alabaster: use it only for dots/icons/large text, always paired with a text label.
6. **Glass blur only on overlays** (header, drawers, modal). Answer cards use elevation, borders and a translucent warm surface, not `backdrop-filter`, to keep scrolling smooth on phones.
7. **Wording is clinical-safe.** Review verdict `pass` is labeled "Grounding check passed", never "Verified". `revise` -> "Review notes". `insufficient_evidence` -> "Insufficient evidence in sources".
8. **"Local-first" wording is truthful:** "History stays in this browser". Questions are still sent to the configured LLM endpoint. Provide a "Clear all history" action.
9. **Haptics** work on Android/Chromium only (iOS Safari has no Vibration API). Feature-detect, never promise, and allow disabling.
10. **Fonts are self-hosted** via npm (`@fontsource-variable/*`). No CDN, no Google Fonts: the container must work offline-for-assets and under a strict CSP.
11. **Tailwind v3.4 is pinned.** If Tailwind v4 is already installed, port the tokens to a `@theme` block, keeping the same names and values.
12. **No `<form>` submit reloads, no `dangerouslySetInnerHTML`, no localStorage for secrets** (there are none; history is non-sensitive but still try/catch wrapped).

## 0.4 Dependencies (each justified; add nothing else without a one-line reason)

`react`, `react-dom`, `zustand` (tiny store + `persist` for history/settings), `zod` (runtime API validation), `react-markdown` + `remark-gfm` + `rehype-sanitize` (safe Markdown), `unist-util-visit` (highlight plugin), `lucide-react` (icons), `@fontsource-variable/inter`, `@fontsource-variable/fraunces`, `@tailwindcss/typography`, `clsx`. Dev: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, eslint + typescript-eslint, prettier + `prettier-plugin-tailwindcss`. Add `remark-frontmatter` ONLY if the corpus files have YAML front matter (check in Phase A). Verify each package exists with `npm view <pkg>` before installing; pin exact versions.

---

# 1. Architecture & file map

## 1.1 Frontend

```
frontend/
├── index.html
├── public/theme-init.js              # blocking, CSP-safe theme bootstrap (no inline script)
├── tailwind.config.ts  postcss.config.js  vite.config.ts  tsconfig*.json
└── src/
    ├── main.tsx  App.tsx  index.css
    ├── types/{api.ts, ui.ts}
    ├── lib/
    │   ├── api/{client.ts, schemas.ts, stream.ts}      # fetch + Zod + SSE parser
    │   ├── markdown/{SafeMarkdown.tsx, rehypeSourceHighlight.ts, rehypeCitations.ts}
    │   ├── storage/safeStorage.ts                      # try/catch + quota handling
    │   ├── reading.ts  haptics.ts  contrast.ts         # contrast.ts used by tests
    ├── stores/{history.ts, settings.ts, ui.ts}
    ├── hooks/{useTheme, useMediaQuery, useVisualViewport, useHealth, useAskStream,
    │          useSourceDocument, useReadingProgress, useAutoScroll}.ts
    ├── components/
    │   ├── layout/{AppShell, Header, Footer, Drawer, ThemeToggle}.tsx
    │   ├── history/HistorySidebar.tsx
    │   ├── chat/{ChatFeed, UserBubble, AnswerCard, ReadingProgress, StickyAskBar,
    │   │        EmptyState, StageTimeline, ReviewNotes, SourceBadges, CitationChip}.tsx
    │   ├── trace/{TracePanel, IndexStatus, RetrievedChunks, ToolCalls}.tsx
    │   ├── sources/SourceModal.tsx
    │   └── zen/ZenReader.tsx
    └── test/setup.ts
```

## 1.2 Backend (verify real paths in the repo first; names below follow `.clinerules` Section 4)

```
backend/app/
├── api/sources.py            NEW  GET /api/v1/sources, GET /api/v1/sources/{file_name}
├── api/health.py             MOD  + version, index_stats (optional fields)
├── api/ask_stream.py         NEW (only if absent)  POST /ask/stream
├── schemas/sources.py        NEW
├── schemas/ask.py            MOD  + retrieval, trace (optional, default None)
├── schemas/health.py         MOD
├── retrieval/chunker.py      MOD  chunk spans: start_char / end_char in the normalized source text
├── retrieval/loader.py       MOD  expose the normalized text registry (file_name -> text)
├── services/source_service.py NEW
├── services/ask_service.py   MOD  build retrieval + trace from existing Evidence / StageEvents
└── main.py                   MOD  router wiring; SPA fallback exclusions
backend/tests/
├── unit/test_chunk_offsets.py
├── integration/test_sources_api.py
├── integration/test_ask_contract.py     # old fields unchanged, new fields optional
└── integration/test_ask_stream.py       # only if streaming is added here
```

---

# 2. Backend changes (additive, non-breaking)

## 2.1 `/ask` response: optional additions

Existing fields (`answer`, `sources`, `citations`, `disclaimer`, `plan`, `tool_calls`, `review`, `retrieval_mode`, `trace_id`, `usage`, `latency_ms`) are unchanged. Add only if missing, all optional with default `None`:

```python
class RetrievedChunkInfo(BaseModel):
    chunk_id: str
    source_file: str
    section_path: str
    excerpt: str                 # <= 300 chars, trimmed on a word boundary
    dense_rank: int | None       # None when the chunk was not in the dense top-k
    bm25_rank: int | None
    fused_score: float
    cited: bool                  # True when referenced by a final citation

class RetrievalInfo(BaseModel):
    mode: Literal["hybrid", "bm25_only"]
    candidates: int              # distinct chunks considered before the budget cut
    returned: int
    chunks: list[RetrievedChunkInfo]   # at most 12, cited chunks first

class StageTraceInfo(BaseModel):
    stage: Literal["plan", "retrieve", "tools", "review", "answer"]
    status: Literal["done", "skipped", "error"]
    duration_ms: int | None
    summary: str | None          # UI-safe: never raw prompts, never secrets
```

`AskResponse` gains `retrieval: RetrievalInfo | None = None` and `trace: list[StageTraceInfo] | None = None`, built in `ask_service.py` from the existing `Evidence` and `StageEvent` objects. `AskRequest` is unchanged (still tolerant of extra fields).

## 2.2 `/health`: optional additions

Keep HTTP 200 always and the existing keys. Add `version: str` (package/setting `APP_VERSION`, fallback to the pyproject version) and `index_stats: {files: int, chunks: int, embedding_model: str | None} | None`.

## 2.3 Chunk spans

Check whether `Chunk` already records its location. If not, extend the chunker to track `start_char` / `end_char` (half-open) into the NORMALIZED source text (line endings normalized to `\n` exactly once, in the loader; that same string is what the endpoint serves). Rules:

- A chunk's span is the contiguous original range that contributed to its text. Synthetic parts (the repeated table header row, the embedding-text prefix) are not part of the span.
- Overlap between split chunks is allowed; spans may overlap.
- The endpoint converts offsets to **UTF-16 code units** (JavaScript string indices) so frontend slicing and mdast `position.offset` agree. If the file is all BMP characters the numbers are unchanged. Helper: `len(text[:i].encode("utf-16-le")) // 2`, computed once per boundary, not per character in a hot loop.
- Unit tests: spans are in bounds and ordered, `source[start:end]` is non-empty and starts at a heading or block boundary, spans survive a file with CRLF input, non-BMP character handled.

## 2.4 `GET /api/v1/sources` and `GET /api/v1/sources/{file_name}`

```python
class SourceChunkSpan(BaseModel):
    chunk_id: str
    section_path: str
    start: int                   # UTF-16 offset into `markdown`
    end: int

class SourceDocument(BaseModel):
    file_name: str
    title: str                   # first H1, else the file name
    drug_name: str
    source_type: Literal["dailymed", "medlineplus", "glossary"]
    markdown: str                # the exact normalized text the spans refer to
    chunks: list[SourceChunkSpan]
```

- The list endpoint returns `[{file_name, title, drug_name, source_type, size_chars}]`.
- **Security:** serve ONLY files in the loader's registry (an allowlist built at startup from `CORPUS_DIR`). Never join user input into a path. Validate `file_name` against `^[A-Za-z0-9._-]+\.md$`; anything else or unknown -> 404 in the standard error shape. Tests must cover `..%2f`, absolute paths, null bytes, and long names.
- Headers: `ETag` (weak, hash of the text) and `Cache-Control: public, max-age=3600`; honor `If-None-Match` with 304.
- `GLOSSARY.md` is served as `source_type: "glossary"` with an empty `chunks` list.
- Wait for index readiness is NOT required (the registry exists from startup); it must work while the index is `building`.

## 2.5 `POST /ask/stream` (Phase E, only if not already implemented)

Server-Sent-Events format over a streamed POST response (`text/event-stream`, `Cache-Control: no-store`, `X-Accel-Buffering: no`):

```
event: stage   data: {"stage":"retrieve","status":"running|done|skipped|error","duration_ms":120,"summary":"12 chunks from 3 files"}
event: result  data: <full AskResponse JSON>
event: error   data: {"error":{"code":"...","message":"...","request_id":"..."}}
```

Same pipeline and the same `StageEvent` objects as `/ask`; cancel the pipeline on client disconnect; summaries UI-safe. `/ask` remains the graded endpoint and is not modified in behavior.

## 2.6 Static serving rules (`main.py`)

Mount the built UI at `/` AFTER all API routes. The SPA fallback to `index.html` applies only to navigation-like requests: it MUST NOT capture `/api/*`, `/ask*`, `/health`, `/docs`, `/redoc`, `/openapi.json`, and a missing asset with a file extension (e.g. `/missing.js`) must return 404, not `index.html`. If `frontend/dist` is absent the API still starts.

## 2.7 Backend tests (existing tests must pass unchanged)

Add: `test_ask_contract.py` (old fields intact, new fields optional, response validates against the old and the new model), `test_sources_api.py` (200 + spans valid, 304 on ETag, 404 and traversal cases, works while the index is `building`), `test_chunk_offsets.py`, health additive-field test, static-serving exclusions test.

---

# 3. Design system

## 3.1 Palette (exact; single source of truth)

| Token       | Hex       | Role                                                             |
| ----------- | --------- | ---------------------------------------------------------------- |
| `night`     | `#243341` | Dark background, sidebars/drawers (both themes), light-mode text |
| `alabaster` | `#F0F2F5` | Light background, dark-mode text                                 |
| `ocean`     | `#205D96` | Primary actions, source badges, light-mode accent                |
| `steel`     | `#294B6C` | Action hover, badge hover, headings accent, dark-mode badges     |
| `glacial`   | `#B5DBFF` | Hover/active highlights, dark-mode accent text and focus ring    |
| `ice`       | `#E0F0FF` | Light-mode hover/selection tint, user bubble                     |
| `cream`     | `#FFEDCF` | Light-mode AI answer card                                        |
| `champagne` | `#FFEBC9` | Citation highlight, card borders, review notes                   |
| `sage`      | `#519A76` | Ready/healthy dot, "grounding check passed" accent               |

Usage map: AI card = `cream` (light) / raised `night` (dark); user bubble = `ice` (light) / `steel` (dark); passage highlight = `champagne` (+ 3px `ocean`/`glacial` left rule); hover on dark sidebars = `glacial` at 12%, active = 20% + left rule; primary button = `ocean` bg + `alabaster` text (~6:1), hover `steel`; source badge = `ocean` (light) / `steel` + `glacial` text (dark); status ready = `sage`.

## 3.2 `frontend/tailwind.config.ts`

```ts
import type { Config } from 'tailwindcss';
import defaultTheme from 'tailwindcss/defaultTheme';
import typography from '@tailwindcss/typography';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Exact brand palette. Never add other hues.
        night: '#243341',
        alabaster: '#F0F2F5',
        ocean: '#205D96',
        steel: '#294B6C',
        glacial: '#B5DBFF',
        ice: '#E0F0FF',
        cream: '#FFEDCF',
        champagne: '#FFEBC9',
        sage: '#519A76',
        // Semantic tokens: values switch with the `dark` class (see index.css)
        app: 'var(--c-bg)',
        side: 'var(--c-side)',
        surface: 'var(--c-surface)',
        card: 'var(--c-card)',
        ink: 'var(--c-ink)',
        'ink-muted': 'var(--c-ink-muted)',
        line: 'var(--c-line)',
        accent: 'var(--c-accent)',
        'accent-soft': 'var(--c-accent-soft)',
        action: 'var(--c-action)',
        'action-hover': 'var(--c-action-hover)',
        'action-ink': 'var(--c-action-ink)',
        badge: 'var(--c-badge)',
        'badge-ink': 'var(--c-badge-ink)',
        mark: 'var(--c-mark)',
      },
      fontFamily: {
        sans: ['"Inter Variable"', ...defaultTheme.fontFamily.sans],
        display: ['"Fraunces Variable"', ...defaultTheme.fontFamily.serif],
      },
      boxShadow: {
        float:
          '0 1px 2px rgb(36 51 65 / 0.06), 0 12px 28px -12px rgb(36 51 65 / 0.22)',
        glass: '0 24px 60px -20px rgb(0 0 0 / 0.45)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'none' },
        },
        'mark-pulse': {
          '0%': { boxShadow: '0 0 0 0 rgb(32 93 150 / 0.45)' },
          '100%': { boxShadow: '0 0 0 14px rgb(32 93 150 / 0)' },
        },
        'dot-pulse': {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
        'sheet-in-left': {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'none' },
        },
        'sheet-in-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'none' },
        },
      },
      animation: {
        'fade-up': 'fade-up .35s ease-out both',
        'mark-pulse': 'mark-pulse 1.4s ease-out 1',
        'dot-pulse': 'dot-pulse 1.6s ease-in-out infinite',
        'sheet-in-left': 'sheet-in-left .28s cubic-bezier(.22,1,.36,1) both',
        'sheet-in-right': 'sheet-in-right .28s cubic-bezier(.22,1,.36,1) both',
      },
    },
  },
  plugins: [typography],
} satisfies Config;
```

## 3.3 `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Brand palette: mirrors tailwind.config.ts */
  --night: #243341;
  --alabaster: #f0f2f5;
  --ocean: #205d96;
  --steel: #294b6c;
  --glacial: #b5dbff;
  --ice: #e0f0ff;
  --cream: #ffedcf;
  --champagne: #ffebc9;
  --sage: #519a76;

  color-scheme: light;
  --c-bg: var(--alabaster);
  --c-side: var(--night);
  --c-surface: color-mix(in srgb, var(--alabaster) 50%, white);
  --c-card: var(--cream);
  --c-card-line: color-mix(in srgb, var(--night) 10%, var(--champagne));
  --c-ink: var(--night);
  --c-ink-muted: color-mix(in srgb, var(--night) 72%, var(--alabaster));
  --c-line: color-mix(in srgb, var(--night) 14%, transparent);
  --c-accent: var(--ocean);
  --c-accent-soft: var(--ice);
  --c-action: var(--ocean);
  --c-action-hover: var(--steel);
  --c-action-ink: var(--alabaster);
  --c-badge: var(--ocean);
  --c-badge-ink: var(--alabaster);
  --c-mark: var(--champagne);
  --c-bubble: var(--ice);
}

/* Dark theme AND always-dark scopes (sidebars, drawers) share the same variables */
:root.dark,
.scope-dark {
  color-scheme: dark;
  --c-surface: color-mix(in srgb, var(--night) 90%, white);
  --c-card: color-mix(in srgb, var(--night) 93%, white);
  --c-card-line: color-mix(in srgb, var(--glacial) 16%, transparent);
  --c-ink: var(--alabaster);
  --c-ink-muted: color-mix(in srgb, var(--alabaster) 72%, var(--night));
  --c-line: color-mix(in srgb, var(--glacial) 16%, transparent);
  --c-accent: var(--glacial);
  --c-accent-soft: color-mix(in srgb, var(--glacial) 14%, transparent);
  --c-action-hover: color-mix(in srgb, var(--ocean) 78%, var(--glacial));
  --c-badge: var(--steel);
  --c-badge-ink: var(--glacial);
  --c-mark: color-mix(in srgb, var(--champagne) 22%, var(--night));
  --c-bubble: var(--steel);
}
:root.dark {
  --c-bg: var(--night);
  --c-side: color-mix(in srgb, var(--night) 78%, black);
}

html,
body,
#root {
  height: 100%;
}
body {
  margin: 0;
  background: var(--c-bg);
  color: var(--c-ink);
  font-family: 'Inter Variable', system-ui, sans-serif;
  overscroll-behavior: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-text-size-adjust: 100%;
}
:focus-visible {
  outline: 2px solid var(--c-accent);
  outline-offset: 2px;
  border-radius: 4px;
}
textarea,
input {
  font-size: 16px;
} /* prevents iOS focus-zoom */

@layer components {
  /* App shell: dynamic viewport height, safe areas, internal scrolling only */
  .app-shell {
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-top: env(safe-area-inset-top);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
  html[data-vv] .app-shell {
    height: var(--app-height);
  } /* set by useVisualViewport (iOS keyboard) */
  .composer-pad {
    padding-bottom: max(0.75rem, env(safe-area-inset-bottom));
  }
  .sheet-pad {
    padding-bottom: env(safe-area-inset-bottom);
  }

  /* Glass: overlays only (header, drawers, modal) */
  .glass {
    background: color-mix(in srgb, var(--c-surface) 72%, transparent);
    -webkit-backdrop-filter: blur(16px) saturate(140%);
    backdrop-filter: blur(16px) saturate(140%);
    border: 1px solid var(--c-line);
  }
  .glass-strong {
    background: color-mix(in srgb, var(--c-surface) 82%, transparent);
    -webkit-backdrop-filter: blur(28px) saturate(150%);
    backdrop-filter: blur(28px) saturate(150%);
    border: 1px solid var(--c-line);
  }
  @supports not (
    (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))
  ) {
    .glass,
    .glass-strong {
      background: var(--c-surface);
    }
  }

  /* Answer card: elevation + warm surface (no backdrop blur) */
  .card-float {
    background: var(--c-card);
    border: 1px solid var(--c-card-line);
    box-shadow: theme('boxShadow.float');
    border-radius: 1.25rem;
  }

  /* Markdown typography mapped to tokens */
  .prose-synapse {
    --tw-prose-body: var(--c-ink);
    --tw-prose-headings: var(--c-ink);
    --tw-prose-lead: var(--c-ink-muted);
    --tw-prose-links: var(--c-accent);
    --tw-prose-bold: var(--c-ink);
    --tw-prose-counters: var(--c-ink-muted);
    --tw-prose-bullets: var(--c-ink-muted);
    --tw-prose-hr: var(--c-line);
    --tw-prose-quotes: var(--c-ink);
    --tw-prose-quote-borders: var(--c-accent);
    --tw-prose-captions: var(--c-ink-muted);
    --tw-prose-code: var(--c-ink);
    --tw-prose-pre-code: var(--c-ink);
    --tw-prose-pre-bg: var(--c-surface);
    --tw-prose-th-borders: var(--c-line);
    --tw-prose-td-borders: var(--c-line);
  }
  .prose-synapse :where(h1, h2, h3):not(:where([class~='not-prose'] *)) {
    font-family: 'Fraunces Variable', Georgia, serif;
  }
}

/* Cross-highlighting: soft fluorescent bookmark (block-level, from mdast positions) */
[data-highlight] {
  background: var(--c-mark);
  box-shadow: inset 3px 0 0 var(--c-accent);
  border-radius: 0.5rem;
  padding-inline: 0.5rem;
  margin-inline: -0.5rem;
}
[data-highlight='secondary'] {
  background: var(--c-accent-soft);
  box-shadow: none;
}
[data-highlight='primary'].is-focused {
  animation: mark-pulse 1.4s ease-out 1;
}
tr[data-highlight] > td,
tr[data-highlight] > th {
  background: var(--c-mark);
}
tr[data-highlight='secondary'] > td,
tr[data-highlight='secondary'] > th {
  background: var(--c-accent-soft);
}
tr[data-highlight] {
  box-shadow: none;
  padding: 0;
  margin: 0;
  background: transparent;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## 3.4 `frontend/index.html` and `public/theme-init.js`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content"
    />
    <meta name="theme-color" content="#F0F2F5" />
    <title>Synapse - Pharmacology Research Assistant</title>
    <script src="/theme-init.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```js
// public/theme-init.js - runs before first paint (no flash); external file so a strict CSP can stay `script-src 'self'`.
(function () {
  var pref = 'system';
  try {
    pref = localStorage.getItem('synapse.theme') || 'system';
  } catch (e) {}
  var dark =
    pref === 'dark' ||
    (pref === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', dark ? '#243341' : '#F0F2F5');
})();
```

Do not block pinch-zoom (no `maximum-scale`). `main.tsx` imports `@fontsource-variable/inter` and `@fontsource-variable/fraunces` and `index.css`.

---

# 4. Types and state

## 4.1 `types/api.ts` (mirrors the backend; snake_case is intentional; every new field optional)

```ts
export type StageName = 'plan' | 'retrieve' | 'tools' | 'review' | 'answer';
export type StageStatus = 'pending' | 'running' | 'done' | 'skipped' | 'error';

export interface Citation {
  id: string;
  source_file: string;
  section: string | null;
  chunk_id: string;
  excerpt: string;
}
export interface RetrievedChunk {
  chunk_id: string;
  source_file: string;
  section_path: string;
  excerpt: string;
  dense_rank: number | null;
  bm25_rank: number | null;
  fused_score: number;
  cited: boolean;
}
export interface RetrievalInfo {
  mode: 'hybrid' | 'bm25_only';
  candidates: number;
  returned: number;
  chunks: RetrievedChunk[];
}
export interface ToolCallInfo {
  tool: string;
  arguments: Record<string, unknown>;
  status: 'ok' | 'error' | 'timeout';
}
export interface ReviewInfo {
  verdict: 'pass' | 'revise' | 'insufficient_evidence';
  unsupported_claims: string[];
  ambiguity_flags: string[];
}
export interface StageTrace {
  stage: StageName;
  status: StageStatus;
  duration_ms: number | null;
  summary: string | null;
}

export interface AskResponse {
  answer: string;
  sources: string[];
  citations: Citation[];
  disclaimer: string;
  plan?: { complexity: 'simple' | 'multi_hop'; sub_goals: unknown[] };
  tool_calls?: ToolCallInfo[];
  review?: ReviewInfo;
  retrieval_mode?: 'hybrid' | 'bm25_only';
  retrieval?: RetrievalInfo;
  trace?: StageTrace[];
  trace_id: string;
  usage?: { tokens_in: number; tokens_out: number };
  latency_ms?: number;
}
export interface HealthResponse {
  status: string;
  index: 'building' | 'ready' | 'degraded';
  llm_configured: boolean;
  version?: string;
  index_stats?: {
    files: number;
    chunks: number;
    embedding_model: string | null;
  };
}
export interface SourceChunkSpan {
  chunk_id: string;
  section_path: string;
  start: number;
  end: number;
}
export interface SourceDocument {
  file_name: string;
  title: string;
  drug_name: string;
  source_type: 'dailymed' | 'medlineplus' | 'glossary';
  markdown: string;
  chunks: SourceChunkSpan[];
}
export type StreamEvent =
  | { type: 'stage'; data: StageTrace }
  | { type: 'result'; data: AskResponse }
  | {
      type: 'error';
      data: { code: string; message: string; request_id?: string };
    };
```

Zod schemas in `lib/api/schemas.ts` mirror these; new fields `.optional()`; parse every response; surface a friendly error when parsing fails.

## 4.2 `types/ui.ts` (camelCase, UI-only)

```ts
export type TurnStatus = 'pending' | 'done' | 'error';
export interface Turn {
  id: string;
  question: string;
  createdAt: number;
  status: TurnStatus;
  response?: AskResponse; // compacted before persisting
  error?: string;
  liveStages?: StageTrace[]; // NOT persisted
}
export interface Session {
  id: string;
  title: string;
  titleEdited: boolean;
  createdAt: number;
  updatedAt: number;
  turns: Turn[];
}
export type ThemePreference = 'light' | 'dark' | 'system';
export interface SettingsState {
  theme: ThemePreference;
  haptics: boolean;
  historyOpen: boolean;
  traceOpen: boolean;
}
export interface SourceViewTarget {
  fileName: string;
  primaryChunkIds: string[]; // cited chunks (strong highlight)
  secondaryChunkIds: string[]; // other retrieved chunks from this file (soft highlight)
}
export interface UiState {
  activeSessionId: string | null;
  selectedTurnId: string | null;
  sourceView: SourceViewTarget | null;
  zenTurnId: string | null;
  drawer: 'history' | 'trace' | null;
}
```

## 4.3 Stores (Zustand)

- `stores/history.ts`: `persist` with `name: 'synapse.history'`, `version: 1`, a `migrate` stub, `partialize` (sessions, activeSessionId only), JSON storage from `safeStorage`. Actions: `newSession`, `selectSession`, `renameSession`, `deleteSession`, `clearAll`, `addTurn`, `updateTurn`. Title auto-derived from the first question (max ~48 chars) until the user renames. Caps: 50 sessions, 200 turns total; evict the oldest. `compactForStorage(response)` drops `retrieval.chunks[].excerpt` beyond 8 chunks and trims large strings. On `QuotaExceededError` evict the oldest sessions and retry once; if it still fails keep working in memory and expose `storageWarning: boolean` (show a subtle notice).
- `stores/settings.ts`: persist `{theme, haptics, historyOpen, traceOpen}` under `synapse.settings`. The theme hook ALSO writes `synapse.theme` (plain string) because `theme-init.js` reads that key.
- `stores/ui.ts`: not persisted; modal/zen/drawer/selection state.
- `safeStorage.ts`: `getItem/setItem/removeItem` wrapped in try/catch; falls back to an in-memory map if `localStorage` is unavailable (private mode).

## 4.4 Hooks

`useTheme` (toggle `dark` on `<html>`, update `theme-color` meta, `system` follows `matchMedia`), `useMediaQuery` (`lg` = `(min-width: 1024px)`), `useVisualViewport` (Section 6.6), `useHealth` (poll `/health`: 5 s while `building`, 30 s otherwise, paused when `document.hidden`, exponential backoff on failure, abort on unmount), `useAskStream` (Section 6.5), `useSourceDocument(fileName)` (AbortController, module-level `Map` cache keyed by file name + ETag), `useReadingProgress(cardRef, scrollerRef)`, `useAutoScroll` (stick to bottom only if the user is already near the bottom; never yank while they read).

---

# 5. Components

| Component         | Responsibility and behavior                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Accessibility / tests                                                                                                                                                                               |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `AppShell`        | CSS grid: `grid-cols-[auto_1fr_auto]` at `lg`; left 280px, right 360px, each collapsible; `<lg` both become `Drawer`s. Applies `.app-shell`, calls `useVisualViewport`. In zen mode sets `data-zen` and hides sidebars/footer/composer.                                                                                                                                                                                                                                                                                                                   | Landmarks: `<header>`, `<nav aria-label="History">`, `<main>`, `<aside aria-label="Agent trace">`, `<footer>`.                                                                                      |
| `Header`          | Wordmark (Fraunces), active session title, buttons: history, trace, theme. `glass`, sticky.                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Buttons have `aria-label`, `aria-expanded`.                                                                                                                                                         |
| `ThemeToggle`     | Sun/Moon with a smooth rotate; cycles light/dark (long-press or menu for `system` is optional). Calls `haptic()`.                                                                                                                                                                                                                                                                                                                                                                                                                                         | `aria-pressed`, visible focus.                                                                                                                                                                      |
| `HistorySidebar`  | `scope-dark`. "New question" button, list grouped by Today/Yesterday/Earlier, inline rename (Enter saves, Esc cancels), delete with undo toast or confirm, "Clear all history" with confirm. Active = glacial 20% + left rule; hover = glacial 12%.                                                                                                                                                                                                                                                                                                       | Roving focus list; rename input labeled; tests for CRUD.                                                                                                                                            |
| `ChatFeed`        | Scroll container (`overflow-y-auto`, `scroll-padding-bottom`); renders `UserBubble` + `AnswerCard` per turn; `EmptyState` when no turns; `useAutoScroll`. `aria-live="polite"` on the newest answer region.                                                                                                                                                                                                                                                                                                                                               | Tests for empty state and ordering.                                                                                                                                                                 |
| `UserBubble`      | Question text, right-aligned, `bg-[var(--c-bubble)]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |                                                                                                                                                                                                     |
| `AnswerCard`      | `.card-float`. Header: "Synapse", grounding chip (sage for `pass`, champagne+ocean for `revise`, neutral for insufficient evidence), reading time, zen button, copy button. Sticky `ReadingProgress`. Body: `SafeMarkdown` (`prose prose-synapse`). Below: `ReviewNotes` (champagne block listing `unsupported_claims` / `ambiguity_flags` in plain language), `SourceBadges`, tool-call chips (collapsed), and the response's `disclaimer` (ALWAYS visible). Clicking the card sets `selectedTurnId` (drives the trace panel).                           | Tests: disclaimer present, chip variants, copy.                                                                                                                                                     |
| `SourceBadges`    | One badge per `sources` entry: file name (monospace, truncated with title), type tag (DailyMed/MedlinePlus). `bg-badge text-badge-ink`, hover `steel`. Click -> `ui.sourceView = {fileName, primary: cited chunk ids for that file, secondary: other retrieved chunk ids}`. Calls `haptic()`.                                                                                                                                                                                                                                                             | `<button>`, label "Open source <file>".                                                                                                                                                             |
| `CitationChip`    | Renders `[S1]`: small ocean/glacial chip; hover/focus shows a tooltip with the excerpt, file and section (`role="tooltip"`, `aria-describedby`); click opens the modal on that chunk. On touch, tap opens the modal directly (no hover popover). Unknown ids render as plain text.                                                                                                                                                                                                                                                                        | Tests: hover, focus, click, unknown id.                                                                                                                                                             |
| `SourceModal`     | Native `<dialog>` + `showModal()` (built-in focus trap, Esc, inert background). Panel `.glass-strong` with `shadow-glass`; full-screen sheet on mobile with `.sheet-pad`. Header: file name, drug, type badge, "Passage 1 of N" with prev/next, close. Body: `SafeMarkdown` of the full source with highlight ranges; loading skeleton, error state with Retry. On open: `scrollIntoView({block:'center'})` the first primary highlight (smooth unless reduced motion) and add `.is-focused`. Return focus to the opener on close; backdrop click closes. | Tests: opens, highlights primary, scrolls, Esc closes, focus restored, 404 error state.                                                                                                             |
| `TracePanel`      | `scope-dark`. Sections: `IndexStatus` (dot + text from `/health`: ready=sage, building=pulsing glacial "Indexing...", degraded=champagne "BM25-only", unreachable=neutral "API unreachable"; shows files/chunks/embedding model), latest-query metrics (latency, tokens in/out, per-stage durations as a thin bar), `RetrievedChunks` (file badge, section path, 2-line excerpt, rank chips "dense #2                                                                                                                                                     | bm25 #1", fused score, `cited` marker with the S-number; click opens the modal at that chunk), `ToolCalls` (name, args summary, status), review summary. Shows the selected turn (default: latest). | Never rely on color alone: icons/text for every status.                                                                                |
| `StageTimeline`   | The collapsible "Stream of Thought" card inside the pending answer. Shows the 5 REAL stages with friendly labels: Plan "Analyzing your question", Retrieve "Searching sources (semantic + keyword)", Tools "Consulting local tools", Review "Checking claims against sources", Answer "Composing cited answer". Expanded while running; collapses to a one-line summary when done ("Answered in 8.4 s                                                                                                                                                     | 5 stages                                                                                                                                                                                            | 3 sources") and can be re-expanded; collapse state remembered per turn. Without streaming: indeterminate "Working..." (no fake steps). | `<button aria-expanded>`, `aria-live="polite"` for stage changes. |
| `ReadingProgress` | See 6.2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `aria-hidden` (decorative; the reading time is the accessible info).                                                                                                                                |
| `StickyAskBar`    | See 6.7.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |                                                                                                                                                                                                     |
| `Footer`          | One line: sage health dot + text ("Index ready" etc.), version badge `v{version}` as a link to `/docs` (`target="_blank" rel="noopener"`), lock icon + "History stays in this browser" (tooltip explains that questions are sent to the configured LLM endpoint). Collapses to dot + version on narrow screens.                                                                                                                                                                                                                                           | Status is text, not only color.                                                                                                                                                                     |
| `ZenReader`       | See 6.4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |                                                                                                                                                                                                     |
| `Drawer`          | `<dialog>`-based slide-over for `<lg`: `glass` + `backdrop-blur-md` scrim, slides with `animate-sheet-in-left/right`, Esc and scrim-click close, focus trap via native dialog, body scroll lock, `.sheet-pad`. Content components are shared with the docked layout.                                                                                                                                                                                                                                                                                      | Tests: opens/closes, focus return.                                                                                                                                                                  |
| `EmptyState`      | Brand mark, one-line purpose, the independence hint (decision 3), and the 4 public evaluation questions as clickable cards (clicking fills AND sends via the normal path).                                                                                                                                                                                                                                                                                                                                                                                |                                                                                                                                                                                                     |

---

# 6. Feature specifications

## 6.1 Cross-highlighting (the hard part: follow exactly)

1. `useSourceDocument` returns `{markdown, chunks[]}`; look up spans by `chunk_id` for `primaryChunkIds` and `secondaryChunkIds`.
2. Build `ranges: {start, end, level}[]` and pass them to `SafeMarkdown` as `highlightRanges`.
3. A custom rehype plugin marks the smallest block elements whose source offsets (from mdast `position.start.offset/end.offset`, which are UTF-16 indices into the exact string passed in) overlap a range:

```ts
import { visit, SKIP } from 'unist-util-visit';
import type { Element, Root } from 'hast';

export interface HighlightRange {
  start: number;
  end: number;
  level: 'primary' | 'secondary';
}
const BLOCKS = new Set([
  'p',
  'li',
  'tr',
  'pre',
  'blockquote',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
]);

export function rehypeSourceHighlight(options: { ranges: HighlightRange[] }) {
  return (tree: Root): void => {
    visit(tree, 'element', (node: Element) => {
      if (!BLOCKS.has(node.tagName) || !node.position) return;
      const s = node.position.start.offset;
      const e = node.position.end.offset;
      if (s == null || e == null) return;
      // An outer <li> that contains a nested list must not swallow its children.
      if (
        node.tagName === 'li' &&
        node.children.some(
          (c) =>
            c.type === 'element' && (c.tagName === 'ul' || c.tagName === 'ol')
        )
      )
        return;
      const hits = options.ranges.filter((r) => s < r.end && e > r.start);
      if (hits.length === 0) return;
      node.properties.dataHighlight = hits.some((r) => r.level === 'primary')
        ? 'primary'
        : 'secondary';
      return SKIP; // do not double-mark descendants
    });
  };
}
```

4. Plugin order in `SafeMarkdown`: `[[rehypeSourceHighlight, {ranges}], [rehypeSanitize, schema], rehypeCitations]`. The sanitize `schema` extends the default so `*` elements may carry `dataHighlight` (and nothing else new). The citation plugin runs AFTER sanitize because it only creates controlled `cite-chip` elements from `[S\d+]` text nodes (skipping `code`, `pre`, `a`); map `cite-chip` in `components`.
5. If the corpus files have YAML front matter, add `remark-frontmatter` so the block is parsed and not rendered (positions stay valid) and show a small metadata header instead.
6. Highlight granularity is a whole block (paragraph, list item, table row, heading). That is intentional and robust against Markdown normalization. Tests: highlighted block gets the marker, neighbors do not, a table row is marked, a nested list item marks only the nested item, `<script>` in the source is still stripped, ranges outside the text do nothing.
7. Prev/next passage navigation cycles through `[data-highlight="primary"]` elements in DOM order.

## 6.2 Reading time and progress

```ts
// lib/reading.ts
export function estimateReadingSeconds(markdown: string): number {
  const words = markdown
    .replace(/[#>*_`|\-\[\]()]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
  return Math.max(5, Math.round(words / 3.3 / 5) * 5); // ~200 wpm, rounded to 5 s
}
export function formatReadingTime(seconds: number): string {
  return seconds < 60
    ? `${seconds} sec read`
    : `${Math.max(1, Math.round(seconds / 60))} min read`;
}
export function revealedFraction(card: DOMRect, scroller: DOMRect): number {
  if (card.height <= 0) return 0;
  return Math.min(1, Math.max(0, (scroller.bottom - card.top) / card.height));
}
```

`ReadingProgress` is a 2px bar `sticky top-0` inside the card (so it stays visible while the card's top scrolls away), width via `transform: scaleX(fraction)` with `origin-left` (GPU only), updated from a passive scroll listener throttled by `requestAnimationFrame` plus a `ResizeObserver`. Render the bar only when the card is taller than the scroller viewport; render the reading-time label whenever the answer has more than 60 words. Colors: `ocean` (light) / `glacial` (dark) on a `--c-line` track.

## 6.3 Floating glass cards

`.card-float` (Section 3.3): warm `cream` surface and `champagne`-tinted border in light mode; raised `night` surface with a `glacial` hairline in dark mode; `animate-fade-up` on mount (disabled by the reduced-motion rule). Blur is not used on cards (decision 6).

## 6.4 Zen / focus reading mode

- Toggle button on each `AnswerCard` (`aria-pressed`). Sets `ui.zenTurnId`.
- In zen: `AppShell[data-zen]` slides both sidebars out (transform, 250 ms), hides footer and the ask bar, and shows ONLY that answer in a centered reader (`max-w-[68ch]`, `text-lg leading-8`, Fraunces headings, generous padding). Disclaimer and sources remain visible at the end.
- Exit: `Esc`, an always-visible "Exit focus" floating button, or toggling again. Return focus to the zen toggle. On mobile zen simply hides both drawer triggers.
- Persist nothing: zen is a transient mode.

## 6.5 Streaming and the Stage timeline

- `lib/api/stream.ts`: `fetch` POST with `AbortController`; read `response.body.getReader()`, decode with `TextDecoder`, split on blank lines, parse `event:` / `data:` fields (support multi-line `data:`), validate each payload with Zod, emit `StreamEvent`s. Unit-test the parser with split chunks, multi-byte characters across chunk boundaries, comment lines, and malformed JSON.
- `useAskStream` sets `turn.liveStages` as events arrive and finalizes the turn on `result`. A Stop button aborts the request. On any streaming failure (HTTP error, parse error, no events within 10 s) it falls back to `POST /ask` once, silently, and shows the indeterminate state.
- Graded behavior never depends on the stream: `/ask` remains fully functional.

## 6.6 Mobile viewport and keyboard

```ts
// hooks/useVisualViewport.ts
export function useVisualViewport(): void {
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const root = document.documentElement;
    const apply = (): void => {
      root.style.setProperty('--app-height', `${vv.height}px`);
      root.dataset.vv = '1';
      if (vv.offsetTop > 0) window.scrollTo(0, 0); // iOS shifts the layout viewport when the keyboard opens
    };
    apply();
    vv.addEventListener('resize', apply);
    vv.addEventListener('scroll', apply);
    return () => {
      vv.removeEventListener('resize', apply);
      vv.removeEventListener('scroll', apply);
      root.style.removeProperty('--app-height');
      delete root.dataset.vv;
    };
  }, []);
}
```

- The shell never scrolls; only `ChatFeed` scrolls. The composer is a flex child at the bottom of the column (not `position: fixed`), so it rides above the keyboard with `.composer-pad` and `env(safe-area-inset-bottom)`.
- When the keyboard opens and the user was near the bottom, scroll the feed to the bottom.
- Inputs use 16px text (no iOS zoom). Tap targets >= 44px. Honest limit: iOS keyboard behavior can only be fully verified on a real device; verify with Chrome DevTools device emulation and list it under Known issues.

## 6.7 `StickyAskBar`

- Rounded-2xl container with `bg-surface`, hairline border, soft shadow; auto-growing `<textarea>` (1-6 rows), Enter sends, Shift+Enter newline, ignore Enter while `isComposing` (IME), counter visible from 1,800 of 2,000 chars, send button `bg-action text-action-ink` (hover `action-hover`), becomes a Stop button while a request is pending.
- Always-visible caption under the bar: "Educational research tool. Not medical advice." (the full disclaimer also appears in every answer card).
- Calls `haptic()` on send. Disabled state with a clear reason when the API is unreachable.

## 6.8 Haptics

```ts
// lib/haptics.ts
export function haptic(enabled: boolean, ms = 12): void {
  if (!enabled || typeof navigator === 'undefined' || !('vibrate' in navigator))
    return;
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
  navigator.vibrate(ms); // must run inside a user-gesture handler
}
```

Call on: send, theme toggle, source modal open. Settings toggle (default on). Unit tests: gated by `enabled`, by feature detection and by reduced motion.

## 6.9 Footer health

`useHealth` drives the dot: `ready` -> sage (static), `building` -> glacial with `animate-dot-pulse`, `degraded` -> champagne ring, unreachable -> neutral. The label text always states the status. Version from `/health.version`, falling back to a Vite `define` of the `package.json` version.

---

# 7. Tests and verification

- **Vitest:** theme toggle persists and flips the `dark` class and the `theme-color` meta; history store CRUD, eviction caps, quota-exceeded fallback, schema `version`; highlight plugin cases (6.1); reading-time and `revealedFraction` pure functions; haptics gating; Zod parsing (missing optional fields, wrong types -> friendly error); SSE parser; `CitationChip`; `SourceModal` (opens, primary highlight present, Esc, focus restore, 404); `SafeMarkdown` neutralizes `<script>` and `javascript:` links; disclaimer always rendered; footer health states.
- **Contrast test** (`contrast.test.ts` + `lib/contrast.ts`): implement WCAG contrast and an sRGB `color-mix` helper (linear interpolation of 0-255 channels); assert >= 4.5:1 for text pairs (ink/muted on bg, card, side; action-ink on action; badge-ink on badge; glacial on night) and >= 3:1 for UI pairs; document the sage exception (decision 5).
- **Backend:** `pytest` (all existing tests unchanged + the new ones in Section 2.7), `ruff check`, `mypy`.
- **Build and Docker:** `npm run build`, `tsc --noEmit`, eslint, prettier check; `docker build -t agent .` and `docker run -p 8000:8000 --env-file .env agent`; then confirm: UI loads at `/`, theme persists, `/docs` loads, `/health` 200, `POST /ask` unchanged, source modal loads a file, no request leaves the origin except the LLM calls made by the backend (check the browser network panel: no fonts/CDN hosts).
- **Regression:** re-run the eval harness; answers must be unaffected.
- **Manual (list in `docs/PROGRESS.md`):** light/dark, 320px / 390px / 768px / 1280px widths, long answer scrolling with the progress bar, zen enter/exit, drawers, keyboard-open behavior (emulated), reduced-motion.

---

# 8. Execution plan (phases)

| Phase                       | Deliverables                                                                                                                                                                                                                                                                            | Exit criteria                                                                                                                    | Commit                                                                 |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **0 Reconcile** (plan only) | Inspect the real repo (`backend/app/*`, existing `frontend/`, schemas, tests, chunker, corpus front matter). Output a gap report and a file-by-file plan. No code.                                                                                                                      | Report lists every file to create/modify and any conflict with `.clinerules`.                                                    | none                                                                   |
| **A Backend API**           | Sections 2.1-2.4, 2.6, 2.7: chunk spans, `retrieval`/`trace` fields, `/health` additions, sources endpoints, static-serving rules, tests.                                                                                                                                               | `pytest`, `ruff`, `mypy` green; old tests unchanged; eval unchanged.                                                             | `feat(api): additive retrieval info, source documents and chunk spans` |
| **B Foundation**            | Dependencies, Tailwind config, `index.css`, `index.html`, `theme-init.js`, fonts, types, Zod schemas, stores, `useTheme`/`useMediaQuery`/`useVisualViewport`, `AppShell`, `Header`, `Drawer`, `ThemeToggle`, contrast test.                                                             | `npm run build`, `tsc`, lint, vitest green; app shell renders in both themes at all widths.                                      | `feat(frontend): design system, theme engine and responsive shell`     |
| **C Chat core**             | `StickyAskBar`, `ChatFeed`, `UserBubble`, `AnswerCard` (grounding chip, `ReviewNotes`, disclaimer), `SafeMarkdown`, `EmptyState`, API client, `HistorySidebar` with persistence/rename/clear, basic `TracePanel` (index status + metrics + chunk list), `Footer`. Non-streaming `/ask`. | Everything usable end to end with the real backend; tests green. **Then run Tasks 10 and 11 (Docker + push) before continuing.** | `feat(frontend): chat, history and answer cards`                       |
| **D Source verification**   | `SourceBadges`, `CitationChip`, `rehypeCitations`, `useSourceDocument`, `SourceModal`, highlight plugin, passage navigation, trace-panel chunk click-through.                                                                                                                           | Section 6.1 tests pass; modal highlights the cited passage in a real corpus file (warfarin contraindications).                   | `feat(frontend): source modal with cross-highlighted passages`         |
| **E Reading and streaming** | `reading.ts`, `ReadingProgress`, `StageTimeline`, `useAskStream` + `POST /ask/stream` (if absent) with tests, `Footer` health polling, `ZenReader` (COULD).                                                                                                                             | Stream tests pass; non-stream fallback verified by disabling the endpoint; zen enter/exit works.                                 | `feat: reading progress, honest stage timeline and zen mode`           |
| **F Mobile polish**         | Mobile drawers (blur), safe-area and keyboard behavior, haptics (COULD), 44px targets, 16px inputs, reduced-motion verification, hover cross-sync (COULD).                                                                                                                              | Manual matrix in Section 7 recorded in `docs/PROGRESS.md`.                                                                       | `feat(frontend): mobile drawers, safe areas and haptics`               |
| **G Quality gate**          | Full verification of Section 7, Docker graded command re-run, eval re-run, update `.clinerules` (Sections 9 and 11: additive fields, palette tokens, new endpoints), update README screenshots/notes.                                                                                   | Definition of Done below.                                                                                                        | `chore: UI quality gate and docs`                                      |

---

# 9. Definition of Done

- [ ] `GET /health` and `POST /ask` behave exactly as before for the graded contract; all pre-existing backend tests pass unchanged; the eval harness result is unchanged.
- [ ] New API surface is additive and optional; sources endpoint is allowlist-only and traversal-safe.
- [ ] The nine palette hexes are the only hues; contrast test passes; focus rings visible in both themes and on dark sidebars.
- [ ] Theme toggle is flash-free, persisted, and honors `prefers-color-scheme` for first visit.
- [ ] Three-column layout at >= 1024px; drawers with blur below; composer anchored in the thumb zone with safe-area padding; keyboard never covers messages (verified in emulation, real-device check listed).
- [ ] History persists (rename, delete, clear all) with quota-safe storage; wording is truthful ("History stays in this browser").
- [ ] Every answer shows the disclaimer; the grounding chip wording follows decision 7.
- [ ] Source badges and citation chips open the modal; the cited passage is highlighted and scrolled into view; `<script>` content cannot execute.
- [ ] The Stage timeline shows only real events; fallback is honest.
- [ ] Reading time and progress bar appear only when meaningful; zen mode exits with Esc.
- [ ] No third-party network requests from the browser; fonts are bundled; no `dangerouslySetInnerHTML`.
- [ ] `npm run build`, `tsc --noEmit`, eslint, vitest, `pytest`, `ruff`, `mypy` pass; the exact graded Docker command works and the UI is served.
- [ ] `docs/PROGRESS.md`, `.clinerules` (Sections 9 and 11) and README are updated and match reality.
