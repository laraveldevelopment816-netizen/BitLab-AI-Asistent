# Screens — detailed specs

Open `prototype/Conduit.html` in a browser alongside this doc. Every measurement, color, and copy string below was lifted directly from the prototype.

---

## Global chrome

### Sidebar (`width: 232px, fixed`)
- Background `panelLo` (#0d1014), right border `border` (#1f242b)
- Top section (header, padding `20px 18px 18px`, bottom border):
  - Conduit mark (28px SVG, see `ConduitMark` in `components.jsx`)
  - "conduit" — mono, 15px, weight 600, letter-spacing −0.01em
  - "v0.3.2 · local" — mono, 10px, color `textMute`, letter-spacing 0.05em
- Nav items (padding `8px 12px`, margin `1px 0`):
  - Active: bg `accent14` (`#7dd3fc14`), left border 2px `accent`, text `text`
  - Inactive: transparent, left border 2px transparent, text `textDim`
  - Title: 13px sans, weight 500 active / 400 inactive
  - Hint below: 10.5px sans, color `textMute`
  - Items: Live · History · Adapters · Compose · Compare · Templates · Cost · Roadmap · Settings
- Footer (padding `12px 16px`, top border): mono 10.5px stats panel
  - `queue / req/min / spend/d` rows, dashed separator, `API :8000` with pulsing green dot

### Top bar (per-page)
- Padding `20px 28px 18px`, bottom border, flex space-between
- H1: 22px sans, weight 500, letter-spacing −0.02em
- Subtitle: 13px sans, color `textDim`, margin-top 4px
- Right slot for buttons or status

### Detail Drawer (right slide-out)
- Width 540px, full-height, bg `panel`
- Backdrop: `#000a` (60% black) with 0.18s fadeIn
- Slides in 0.22s `cubic-bezier(.2,.8,.3,1)` from `translateX(100%)`
- Header (padding `18px 22px 14px`, bottom border):
  - "request" mono 11px `textMute`
  - Request id mono 16px
  - Row: AdapterPill + client Tag + StatusBadge
  - Close button 28×28, transparent, 1px border `border`, "×" glyph
- Body sections (label "prompt" / "response" / "timing" / "tokens & cost" / "actions"):
  - Each section label: mono 10px uppercase, letter-spacing 0.08em, color `textMute`, margin-bottom 8px
  - Code blocks: bg `panelLo`, 1px border `border`, radius 4, padding 12, mono 12px, line-height 1.6
  - Response shows blinking caret (`width 6, height 12, bg accent`) at end if `status === 'ok'`
- Timing breakdown: 5-segment horizontal bar (queue/navigate/send/gen/extract) over 8px height, with grid below showing each phase's ms

---

## 1. Live

**TopBar right:** streaming/paused indicator (dot + label), pause/resume button, "⤓ export jsonl"

**Metrics row** (4 cards, padding `16px 28px 0`, gap 10):
- "last 30 visible" — count
- "input tokens" — sum
- "output tokens" — sum
- "cost @ real api" — sum, accent color

**Log table** (margin `16px 28px 28px`, bg `panel`, 1px border, radius 6):
- Header row: bg `panelLo`, padding `10px 16px`, mono 10px uppercase, color `textMute`
- Columns: `76px 110px 110px 1fr 70px 80px 70px 60px` — time / id / adapter / prompt / tokens / latency / cost / status
- Row: padding `8px 16px`, 1px bottom border, mono 12px, cursor pointer
- Hover: bg `accent10`
- Fresh row (newly arrived): bg `accent08`, fades to transparent over 0.6s after 1.5s
- Tokens cell: green `↓N` + amber `↑M` (down arrow input, up arrow output)

**Behavior:** ticker every 3.5s adds a synthetic new row when not paused; cap at 30 rows.

---

## 2. History

**Filter bar** (padding `12px 28px`, bottom border):
- Search input (flex 1, padding `7px 12px`, bg `panel`, border, radius 4, mono 12px) — placeholder "Search prompts…"
- Adapter select: `all adapters` + each adapter
- Status select: `all statuses · 200 OK · errors · rate limited`

**Log table:** same as Live but no ticker, full set of mock requests filtered live.

**Empty state:** centered text "No requests match your filters." in `textMute`, padding 40.

---

## 3. Adapters

**TopBar right:** "+ Add adapter" primary button.

**Grid:** `repeat(auto-fill, minmax(360px, 1fr))`, gap 14, padding `20px 28px`.

**AdapterCard** (`bg panel`, border, radius 6, padding 16, position relative):
- Top accent bar: 2px high, full width, `bg adapter.color`, opacity 0.7 (or 0.2 if offline)
- Header row: name + status dot (pulsing if online); right side: status Tag (online/degraded/offline)
- Model line: mono 11px, color `textDim`
- 4-stat grid (queue / active / p95 / success):
  - Each: mono 9.5px uppercase label + 16px mono value
  - Success% colored: ≥99 green, 95–99 amber, <95 red
- Detail rows (mono 10.5px, dashed top border, padding `10px 0`):
  - `auth` — green dot if authenticated
  - `session` — age string
  - `today` — req count + token totals
  - `last err` — only if present, in red
- Action row: ghost buttons "Re-login · Logs · Test ping"

---

## 4. Compose

**Two-column layout** (`1fr 1fr`, gap 18, padding `20px 28px`).

**Left column:**
- Section "prompt": textarea, rows 10, padding 12, bg `panelLo`, border, radius 4, mono 12.5px, line-height 1.6, vertical resize
- Section "routing": 2-col grid
  - Field "Target adapter": select (auto + each non-offline adapter)
  - Field "Policy when auto": select (cheapest/fastest/sticky/roundrobin)
- Checkbox "Stream response (SSE)" — sans 12.5px, `textDim`
- Buttons row: primary "▶ Send" + ghost "Save as template" + ghost "Copy as cURL"

**Right column:**
- Section "response": min-height 280, padding 14, bg `panelLo`, mono 12.5px
  - Empty: comment-style placeholder "// response will appear here…" in `textMute`
  - Pending: "⠋ generating…" in `accent`, blink animation
  - Done: text + blinking caret
- Section "this run" (only when done): 4-metric grid (latency / ↓ in / ↑ out / cost)

---

## 5. Compare

**TopBar subtitle:** "Fan one prompt to N adapters · weigh quality vs. cost vs. latency"

**Sections:**
- "prompt" — textarea, rows 3
- "adapters to compare" — chip buttons (toggle on/off):
  - On: bg `adapter.color + '22'`, border `adapter.color + '80'`, text `adapter.color`, prefixed "✓ "
  - Off: bg `panelLo`, border `border`, text `textDim`
- Run button: "▶ Run on N adapters"

**Results row** (`grid-template-columns: repeat(N, 1fr)`, gap 12):
- Each column: bg `panel`, border, radius 6
  - Top accent border 2px = adapter color
  - Header: AdapterPill (size md) + latency · cost (right)
  - Body: response text or pending spinner, mono 12px, line-height 1.6, min-height 120
  - Footer (top border): mono 10.5px, `textMute` — "↓N ↑M" left, model name right

**Mock fan-out timing:** stagger results 700ms, 1200ms, 1700ms…

---

## 6. Templates

**Two-column layout** (320px list + 1fr preview, full height).

**List** (left, right border):
- Each item: padding `10px 18px`, left border 2px (transparent or `accent`), bg `accent10` if active
  - Title: 13px sans
  - Sub: mono 10.5px `textMute` — `#tag1 #tag2 · N uses`

**Preview** (right, padding `20px 28px`):
- H2: 18px sans, weight 500
- Body block: bg `panelLo`, border, radius 4, mono 12.5px, line-height 1.6
  - `{{variables}}` get accent-tinted background (`accent20`), accent text, padding `1px 4px`, radius 2
- Action row: primary "Use template" + ghost "Edit · Duplicate"

---

## 7. Cost

**Header metrics row** (4 cards, gap 10):
- "today, total" — accent, with sub "N requests"
- "↓ input tokens"
- "↑ output tokens"
- "projected / month" — sub "at current rate"

**Section "monthly budget · soft limit $50":**
- Card with bg `panelLo`, border, radius 6, padding 16
- Header line (mono 12px): "$X.XX projected" left, "N% of $50" right
- Bar: 10px high, bg `bg`, radius 2
  - Fill: width = pct%, color = green <70%, amber 70–90%, red >90%

**Section "by adapter":**
- Each row in a stacked card: padding `14px 18px`, bottom border
  - Layout: `160px 1fr 100px 90px` — pill / proportion bar / token totals / cost
  - Bar: 6px high, normalized to max cost across adapters

**Section "hourly traffic · last 24h":**
- Card with stacked bar chart, 140px tall, gap 3px between hour columns
- Each column is column-reverse flex stacking adapter contributions
- X axis: "24h ago · 12h · now" (mono 10px `textMute`)
- Legend: colored dots + adapter names (mono 10.5px)

---

## 8. Roadmap (in-app)

This is the build plan, surfaced inside the app itself for visibility. Use the same data as `prototype/data.js → window.ROADMAP`.

**Top: PlanIntro card** with 4 metrics (phases / sessions est / opus sessions / sonnet sessions) + a paragraph on the working principle.

**Timeline** (max-width 980, padding `22px 28px 40px`):
- Vertical line at left (2px wide, `border` color)
- Each PhaseCard:
  - Numbered circle on the line: 18px, 2px border `statusColor`, contains phase index
  - Status colors: `done` → green; `in_progress` → accent (cyan); `todo` → mute
  - Card: bg `panel`, border (cyan tint if in-progress), radius 6, padding 16
  - Header: phase number + title + Tags (status / model / effort / "~N msg")
  - Bullet list of deliverables (12.5px sans, line-height 1.7, color `textDim`)
  - Test criterion: mono 11.5px in a `panelLo` block, left border 2px `statusColor`, prefixed `$ test:`

**Bottom: SessionEconomics card** explaining the €20 Pro plan math.

---

## 9. Settings

**Single-column form** (max-width 720, padding `20px 28px`):

Each setting block has bottom border, padding `16px 0`:
- Title: 14px sans, weight 500
- Description: 12px sans, `textDim`, margin `3px 0 10px`
- Control

Blocks:
1. **Conduit API key** — readonly input (mono 12px) showing masked key, "Reveal" + "Rotate" buttons
2. **Default routing policy** — select
3. **Monthly budget** — number input (width 100) + " USD / month" suffix
4. **Webhooks** — display-only mono code block showing webhook URL
5. **Telemetry** — checkbox: "Keep request/response bodies (off in production by default)"

---

## Shared atom specs

### `<StatusDot>`
8px circle, color by status (green/amber/red/mute). 6px box-shadow glow. If `pulse` prop and status is online, render an absolute-positioned ring scaling 1→2.4 over 2s, opacity 0.5→0.

### `<Tag>`
Mono 10px uppercase, letter-spacing 0.04em, padding `2px 6px`, radius 3.
Background = `color + 20` (or `+10` if `subtle`), border = `color + 40`, text = color.

### `<StatusBadge>`
Tag preset for request statuses:
- `ok` → green "200 OK"
- `error` → red "ERR"
- `rate_limit` → purple "429"

### `<AdapterPill>`
Inline-flex, gap 6: 6px dot in adapter.color + adapter name.
Background `color + 18`, border `color + 30`, text = `color`.
Mono, weight 500. Sizes: sm = 11px / `2px 6px`, md = 12px / `4px 10px`.

### `<Btn>`
Padding `6px 12px`, radius 4, sans 12px.
Variants:
- default: bg `panelHi`, text `text`, border `border`; hover bg `borderHi`
- ghost: bg transparent, text `textDim`, border `border`; hover bg `borderHi`
- primary: bg `accent`, text `bg`, border `accent`

### `<Metric>`
Card: bg `panelLo`, border, radius 4, padding `10px 12px`.
Stack: 10px mono uppercase label + 18px mono value + optional 10.5px mono `textDim` sub.

---

## Copy & terminology

Use these exact strings — they're carefully chosen for the devtool register:
- "Live stream" (not "Live feed" or "Activity")
- "Real-time feed from /v1/chat/completions and adapter queues" (Live subtitle)
- "Browser sessions, health, and per-provider stats" (Adapters subtitle)
- "Send a one-off prompt — same path your API clients take" (Compose subtitle)
- "Fan one prompt to N adapters · weigh quality vs. cost vs. latency" (Compare subtitle)
- "Reusable prompts with {{variables}}" (Templates subtitle)
- "What today's traffic would cost on the real APIs" (Cost subtitle)
- "9 phases · each phase = one Claude session · each phase ends testable" (Roadmap subtitle)
- "API keys, routing defaults, alerts" (Settings subtitle)
