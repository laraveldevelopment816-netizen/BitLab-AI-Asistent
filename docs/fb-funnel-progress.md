# FB Funnel — Progress Log

Trag napretka kroz cijeli eksperiment "B2B akvizicija na autopilotu, ROI 1:5".
Ovaj fajl je samo navigacioni dnevnik — stvarni rad je u sibling repoima.

## Repoi (sibling u `Other/`)

| Repo | Status | Svrha |
|---|---|---|
| `ralph-fb-funnel` | skelet, push-an na GitLab | Ad targeting, ROI scaling (downstream) |
| `ralph-fb-prospector` | skelet, push-an na GitLab | FB profil + email collection |
| `ralph-li-prospector` | **SKELETON, lokalni** | Privremeni LI prospector dok FB ne bude spreman |
| `playwright-router` | `linkedin/post` postoji; `linkedin/scrape_*` **SKELETON** | Browser automation backend |
| `people-first` | brainstorm sesija `2026-05-16-bitlab-shop-fb-b2b-funnel` | Originalni pitch + decisions |

## Timeline

### 2026-05-16
- Brainstorm sesija u `people-first` repou (decisions.md + log.md + pitch.html).
- Tri-fazni dizajn dogovoren: Discovery → Test → Sustain.
- Awaiting Branislav greenlight.

### 2026-05-24
- Skeleton `ralph-fb-funnel/` (AGENTS, PROMPT_build, IMPLEMENTATION_PLAN, README) — Ralph pattern adaptiran za FB B2B akviziciju.

### 2026-05-25
- `ralph-fb-funnel` premešten u parent folder kao samostalan git repo.
- `ralph-fb-prospector` skeleton dodan (separation of concerns — collection odvojen od funnel-a).
- Oba push-ana na GitLab pod `tech-talent-connect/`.
- Identifikovan blocker: nema FB skill-ova u `playwright-router` + FB login automation netrivijalan.
- **Pivot:** privremeno se nadovezujemo na postojeći LinkedIn skill umjesto FB-a (LI auth već radi).
- Dodan SKELETON za `linkedin/scrape_*` u `playwright-router` (search-people, company-employees, group-members; sva tri 501 stub).
- Dodan SKELETON `ralph-li-prospector/` (samo README, ostalo TBD).

## Trenutni korak

**Završeno 2026-05-25 (kasnije):**
- `ralph-li-prospector/` AGENTS/PROMPT/PLAN popunjeni i uskladjeni sa `bitLab-ai-asistent/ralph/` runner-om (markeri STOP + PAUSE, helper kontrakti `wait_pause.py`).

**Sljedeća odluka:**
1. Implementirati prvi LI scrape sub-skill u `playwright-router` (predlog: `search-people` jer je najmanje DOM-zavisan).
2. **Alignment TODO (već push-ano na GitLab, treba commit):** `ralph-fb-prospector` i `ralph-fb-funnel` AGENTS/PROMPT/PLAN trebaju isti tretman — zamijeniti custom markere (`AWAIT_APPROVAL`, `AWAIT_BUDGET`) sa `PAUSE` (sa/bez `until=`) jer postojeći `ralph.sh` razumije samo STOP + PAUSE.

## Blokirano

- FB skill-ovi i FB warm session — odgođeno dok LI pristup ne pokaže ROI.
- Branislav greenlight na ad spend — relevantno tek za Faza 2 Test (poslije nego što Discovery donese ≥200 validnih leadova).
