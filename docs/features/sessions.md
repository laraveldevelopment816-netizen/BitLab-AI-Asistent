# Sessions — thread view razgovora

> Glavna stranica dashboarda. Jedan red = jedan razgovor (klijent + AI), klik → cijela komunikacija turn-by-turn.

## Zašto thread view

Kad gledaš pojedinačne poruke (Live / History tab), gubiš tok razgovora. Korisnik je možda postavio 3 pitanja redom, AI je u prvom pogriješio, u drugom ispravio, u trećem eskalirao — sa message-level view-om vidiš samo isječke. Sa session view-om vidiš **cijeli luk razgovora** i lakše uočavaš:

- AI greške koje se ponavljaju kroz turn-ove
- Korisničke frustracije (kratki upiti tipa "ne", "kako misliš", "ne to")
- Cijenu po cijeloj sesiji (jedan razgovor = jedan klijent = jedan event)
- Latency degradaciju kako razgovor raste (history postaje veći)

## Šta vidi korisnik

### Sessions stranica (`/admin/sessions`)

Tabela sesija sortirana po posljednjoj aktivnosti. Polling 5s, filter po channel-u.

| Kolona | Šta |
|---|---|
| `session` | Skraćen UUID (prvih 8 znakova) |
| `channel` | chat / voice / email tag |
| `model` | haiku / sonnet tag |
| `msgs` | Broj poruka u sesiji |
| `tokens` | Suma `tokens_in / tokens_out` kroz sesiju |
| `latency` | Suma latency-ja, prikazan u sekundama |
| `cost` | Total $ kroz sesiju |
| `err` | Broj failed request-a u sesiji (highlight kad >0) |
| `started` | Vrijeme prve poruke |
| `last activity` | Vrijeme zadnje poruke |
| `first prompt` | Skraćen prvi upit korisnika |

### SessionDetail (`/admin/sessions/:id`)

Top-line metrike (messages, tokens, latency, cost, errors), pa **tok razgovora** — svaki turn je collapsible kartica:

```
#1  [12:34:56]  ✓ ok   "imate li gaming mis"           1 tools · 6.5s · $0.04  ▼
    ┌─ USER ────────────────────────────────────────────────┐
    │ imate li gaming mis                                    │
    └────────────────────────────────────────────────────────┘
    1 tool call:
      ▶ search_products({"query":"gaming miš","category_id":"277"}) 3500ms
    ┌─ ASSISTANT ───────────────────────────────────────────┐
    │ Imamo nekoliko gaming miševa na lageru:                │
    │ - **Logitech G502 HERO** — 199 KM — Na lageru          │
    │ ...                                                    │
    └────────────────────────────────────────────────────────┘

#2  [12:35:12]  ✓ ok   "koji je najbolji za office?"   1 tools · 4.1s · $0.03  ▶

#3  [12:35:48]  ✓ ok   "možeš li poslati link na email" 1 tools · 5.2s · $0.04 ▶
```

Klik na turn proširi/skupi. Tool calls između User i Assistant bubble-a — vidiš tačno **šta** je AI radio između pitanja i odgovora.

Link "full request #N →" vodi na pojedinačni RequestDetail ako trebaš još detalja.

## Kako to radi

### Klijent (widget.js)

Pri otvaranju widget-a generiše UUID i čuva u `sessionStorage`:

```javascript
let sessionId = sessionStorage.getItem('bitlab.sessionId');
if (!sessionId) {
  sessionId = window.crypto.randomUUID();  // ili fallback
  sessionStorage.setItem('bitlab.sessionId', sessionId);
}
```

`sessionStorage` se **briše kad se browser tab zatvori** — odgovara životnom ciklusu razgovora. Ako korisnik refresh-uje stranicu unutar istog tab-a, session se nastavlja. Novi tab = novi session = novi UUID.

Svaki `POST /api/chat` u body-ju ima `session_id`:
```json
{
  "message": "imate li gaming mis",
  "history": [...],
  "channel": "chat",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Voice mod **dijeli isti session ID** (jer dijele `history` array). Pređi sa chat-a u voice — i dalje ista sesija.

### Backend

`Request.session_id: str | None` (nullable za backward compat — legacy podaci nemaju).

`POST /api/chat`:
- `ChatRequest` Pydantic model prima opciono `session_id`
- Prosljeđuje u `_persist_trace()` koji ga snima uz svaki request

`GET /api/dashboard/sessions`:
- Vrati sve `Request`-ove sa non-null `session_id`
- Group by `session_id` u Python-u (SQLite GROUP BY za stringove + cost lookup je manje fleksibilan)
- Sortiraj sesije po posljednjoj aktivnosti (silazno)
- Paginate (50 per page)

Agregati po sesiji:
- `msg_count` = len(rows)
- `total_tokens_in/out` = sum
- `total_latency_ms` = sum
- `total_cost_usd` = sum cost-ova (per-request kroz `_cost(model, in, out)`)
- `error_count` = count gdje `status='error'`
- `first_prompt_preview` = prvi prompt u sesiji (truncated 200)

`GET /api/dashboard/sessions/:id`:
- Sve request-e sa tim `session_id`, sortirane po `created_at` (najstariji prvi)
- Svaki request ima puni `tool_calls[]` timeline (kao u RequestDetail)

## Granica skopa

- **Email kanal:** trenutno svaki email = novi session (n8n ne čuva sessionStorage). Ako želimo da grupišemo emailove po sender-u + thread, treba dodati logiku u `api_email` — npr. session_id = sha256(sender). Sesija 11+.
- **Compare:** koristi `compare_group_id` (postojeći koncept), ne `session_id`. Compare grupiše više modela na jedan upit; session grupiše više upita istog korisnika. Različite ose.
- **Cross-device:** session ne preživljava ni refresh tab-a u inkognito modu, ni device switch. Za to bi trebao authenticated user_id (post-launch).

## Legacy podaci (prije Sesije 8 hotfix sessions)

Stari requesti (commit-ovani prije ove granske izmjene) nemaju `session_id`. Sessions tab ih **preskače** — ostaju vidljivi u Live i History. Migracija u backfill: nije rađena (svaki dan je novi razgovor pa stari podaci nemaju vrijednost u thread view-u).

## Migration

Idempotentno, dodaje kolonu + index ako ne postoje:

```bash
python scripts/migrate_session_id.py
```

Output: `✅ Dodato session_id + index` ili `✅ session_id kolona već postoji — nothing to do`.

Server-side deploy: pokreni jednom poslije `git pull` koraka iz [`../operations/DEPLOY.md`](../operations/DEPLOY.md). U `_init_db()` lifespan task-u već se kreiraju sve tabele iz modela, ali `ADD COLUMN` na postojećoj tabeli zahtijeva eksplicitnu migraciju (SQLAlchemy `create_all` ne dira postojeće).

## Implementacija

| Element | Lokacija |
|---|---|
| Schema | `app/storage/models.py` `Request.session_id` |
| Migration | `scripts/migrate_session_id.py` |
| Repo | `app/storage/repo.py` `insert_request(session_id=...)` |
| API request | `app/main.py` `ChatRequest.session_id` |
| Persist | `app/server/dashboard.py` `_persist_trace(session_id=...)` |
| List endpoint | `app/server/dashboard.py` `list_sessions()` |
| Detail endpoint | `app/server/dashboard.py` `get_session(session_id)` |
| UUID generation | `public/widget.js` `_uuid()` + `sessionStorage` |
| Sessions page | `dashboard/src/pages/Sessions.tsx` |
| SessionDetail page | `dashboard/src/pages/SessionDetail.tsx` |
| API client | `dashboard/src/api.ts` `listSessions()`, `getSession()` |

## Default home

`/admin/` redirect → `/admin/sessions` (ne više `/admin/live`). Live i History ostaju u nav menu-u za message-level analizu kad treba.
