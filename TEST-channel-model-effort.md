# Test plan — per-channel model + effort iz .env (mdef)

Ovaj test plan provjerava da li nove env varijable za odabir modela
i "nivoa razmišljanja" (effort) zaista mijenjaju ponašanje agenta, a
da pritom produkcija sa default vrijednostima i dalje radi kao i prije.

**Kontekst u jednoj rečenici:** agent može zvati Anthropic API direktno
ili kroz PWR (PlaywrightRouter). Za oba puta, sad možemo iz `.env`-a
postaviti zaseban model i "nivo razmišljanja" po kanalu (chat/email).
Voice kanal dijeli vrijednost sa chat-om jer im je tema ista (live
razgovor sa korisnikom).

**Šta je "effort":**

- `low` — model ne razmišlja posebno, samo odgovori. Brzo, jeftino.
  Ovo je default i poklapa se sa produkcijom prije ove kartice.
- `medium` / `high` — model dobija dodatni "budget" tokena za
  razmišljanje prije nego što počne pisati odgovor. Sporije, ali
  preciznije za kompleksnije upite. Na Anthropic putu to je
  "extended thinking" mod; na PWR putu prosljeđujemo isti parametar
  pod imenom `reasoning_effort`.

## Pre-flight

Tri brze provjere prije nego krenemo:

```bash
# 1. Virtualno okruženje je aktivno, openai paket je dovoljno nov (1.50+).
source .venv/bin/activate
.venv/bin/python -c "import anthropic, openai; print(anthropic.__version__, openai.__version__)"

# 2. .env ima ključeve za put koji testiraš. Anthropic put treba
#    ANTHROPIC_API_KEY; PWR put treba PWR_API_KEY i PWR_BASE_URL.
grep -E "^(ANTHROPIC_API_KEY|LLM_BACKEND|PWR_API_KEY|PWR_BASE_URL)=" .env

# 3. Port 7778 je slobodan. (Na WSL2 Docker proxy često zauzima 8000-8090
#    pa biramo bezbjednu vrijednost.)
ss -tln | grep ":7778" && echo "ZAUZET" || echo "slobodno"
```

## Test plan

### 1. Pytest — provjera da nismo ništa pokvarili

Pokrećemo cijeli postojeći set automatskih testova bez ikakvog override-a.
Ovo je sigurnosna mreža: ako bilo šta od 106 testova padne, naše izmjene
su pokvarile nešto u produkcijskom toku. U tom slučaju ne idemo dalje
dok ne nađemo zašto.

```bash
.venv/bin/python -m pytest tests/ -m "not anthropic_api" -q
```

Očekujemo: **106 passed, 10 deselected, 0 failed**.

### 2. Učitavanje config-a i pomoćnih funkcija (bez HTTP-a)

Ovaj test ne ide preko servera — direktno učitavamo settings objekat i
naše dvije pomoćne funkcije u Python interpreter, i tražimo da pokažu šta
su pročitali. Cilj je dokazati tri stvari:

1. Da li env varijable koje postavimo kroz komandu stvarno stignu do
   `settings` objekta (potvrda da pydantic_settings pravilno mapira
   `CHAT_MODEL_EFFORT` iz okruženja na `settings.chat_model_effort`).
2. Da li resolver (`_default_effort_for_channel`) razlikuje kanale —
   chat i voice moraju dati istu vrijednost (jer dijele polje), a email
   mora biti nezavisan.
3. Da li helper za Anthropic (`_anthropic_thinking_kwargs`) pravi tačnu
   strukturu koju ćemo poslije proslijediti API pozivu — `low` mora
   vratiti praznu strukturu (znači "ne šalji nikakve thinking parametre"),
   a `medium`/`high` moraju vratiti thinking config plus uvećan
   `max_tokens` broj (Anthropic zahtjeva da `max_tokens` bude veći od
   thinking budžeta).

```bash
CHAT_MODEL_EFFORT=medium EMAIL_MODEL_EFFORT=high \
PWR_CHAT_MODEL_EFFORT=high PWR_EMAIL_MODEL_EFFORT=medium \
.venv/bin/python -c "
from app.config import settings
from app.agent import _default_effort_for_channel, _anthropic_thinking_kwargs

print('settings: chat=%s email=%s pwr_chat=%s pwr_email=%s' % (
  settings.chat_model_effort, settings.email_model_effort,
  settings.pwr_chat_model_effort, settings.pwr_email_model_effort,
))

print('resolver anthropic: chat=%s voice=%s email=%s' % (
  _default_effort_for_channel('chat', 'anthropic'),
  _default_effort_for_channel('voice', 'anthropic'),
  _default_effort_for_channel('email', 'anthropic'),
))

print('resolver pwr: chat=%s email=%s' % (
  _default_effort_for_channel('chat', 'pwr'),
  _default_effort_for_channel('email', 'pwr'),
))

print('thinking low:', _anthropic_thinking_kwargs('low', 1024))
print('thinking medium:', _anthropic_thinking_kwargs('medium', 1024))
print('thinking high:', _anthropic_thinking_kwargs('high', 1024))
"
```

Očekujemo:

```
settings: chat=medium email=high pwr_chat=high pwr_email=medium
resolver anthropic: chat=medium voice=medium email=high
resolver pwr: chat=high email=medium
thinking low: {}
thinking medium: {'thinking': {'type': 'enabled', 'budget_tokens': 1024}, 'max_tokens': 2048}
thinking high: {'thinking': {'type': 'enabled', 'budget_tokens': 4096}, 'max_tokens': 5120}
```

Ako prvi red ne pokaže `medium/high/high/medium` u tom redoslijedu — env
varijable ne stižu do `settings` objekta i treba provjeriti naziv polja
u `app/config.py`.

### 3. Anthropic put bez override-a (produkcija)

Simuliramo produkciju kakvu imamo danas. Ne smije se ništa pokvariti:
agent treba pozvati tool za pretragu proizvoda i vratiti odgovor sa
konkretnim proizvodom u 2-5 sekundi.

**`.env` prije ovog testa:**
- Bez `LLM_BACKEND=pwr` (zakomentarisati ili obrisati — default je Anthropic).
- Bez `CHAT_MODEL_EFFORT` i `EMAIL_MODEL_EFFORT` override-a.
- Restartuj server u drugom tab-u nakon izmjene.

```bash
time curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam laptop do 1500 KM","channel":"chat"}' \
  | jq '{tools_used, iterations, reply: (.reply | .[0:120])}'
```

Očekujemo: HTTP 200, `tools_used: ["search_products"]`, `iterations >= 2`,
odgovor sa imenom proizvoda. Trajanje 2-5 sekundi.

### 4. Anthropic put sa effort `medium`

Šaljemo identičan upit kao u testu 3, ali ovaj put sa uključenim
thinking budžetom. Pratimo dvije stvari:

1. Da nema HTTP greške. Posebno ne onu o "max_tokens must be greater
   than budget_tokens" — ako se ta pojavi, znači da naš auto-bump kod
   za `max_tokens` ne radi i Anthropic odbije zahtjev.
2. Da je trajanje **primjetno duže** nego u testu 3. Razlog: model sad
   razmišlja prije odgovora, što troši vrijeme.

**`.env` prije ovog testa:**
- Bez `LLM_BACKEND=pwr` (Anthropic put).
- Postavi `CHAT_MODEL_EFFORT=medium`.
- Restartuj server u drugom tab-u.

```bash
time curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam laptop do 1500 KM","channel":"chat"}' \
  | jq '{tools_used, iterations, reply: (.reply | .[0:120])}'
```

Očekujemo: HTTP 200, `tools_used: ["search_products"]`. Trajanje duže
nego u testu 3.

### 5. Kanali se ne miješaju — email i chat nezavisni

Postavljamo različite effort-e za chat i email u istom server run-u.
Cilj: dokazati da kanali ne cure jedan u drugog (npr. da email ne
preuzima vrijednost od chat-a). Ako je sve OK, chat upit ostaje brz
(low, bez thinking-a), a email upit treba biti znatno duži (high,
budget 4096).

**`.env` prije ovog testa:**
- Bez `LLM_BACKEND=pwr` (Anthropic put).
- Postavi `CHAT_MODEL_EFFORT=low`.
- Postavi `EMAIL_MODEL_EFFORT=high`.
- Restartuj server u drugom tab-u.

```bash
echo "--- chat (low, no thinking) ---"
time curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam tastaturu","channel":"chat"}' | jq '.iterations'

echo "--- email (high, thinking budget 4096) ---"
time curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam tastaturu","channel":"email"}' | jq '.iterations'
```

Očekujemo: chat trajanje ~2-5s, email trajanje primjetno veće (>10s).
Email odgovor počinje sa "Poštovani" (postojeće email kanal pravilo).

### 6. PWR put — provjera da prihvata reasoning_effort

Sada prebacujemo backend na PWR i šaljemo upit sa visokim effort-om.
Glavni cilj nije latency (PWR je već po prirodi spor) nego da PWR
endpoint **uopšte prihvati** naš parametar bez greške. Ako pukne sa
porukom o nepoznatom parametru, znači da treba `reasoning_effort` slati
kroz `extra_body` umjesto kao direktan argument funkcije.

**`.env` prije ovog testa:**
- Postavi `LLM_BACKEND=pwr`.
- Postavi `PWR_API_KEY` (vrijednost iz `playwright-router/.env`).
- Postavi `PWR_BASE_URL=http://127.0.0.1:8765/v1`.
- Postavi `PWR_CHAT_MODEL_EFFORT=high`.
- `PWR_CHAT_MODEL` ostavi nepostavljeno (default `claude-sonnet-4-6`)
  ili postavi na neki drugi PWR routing ključ.
- Restartuj server u drugom tab-u.

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam laptop do 1500 KM","channel":"chat"}' \
  | jq '{tools_used, iterations}'
```

Očekujemo: HTTP 200 i `tools_used: ["search_products"]`. Trajanje će
biti 60-90s (to je normalno za PWR).

### 7. (Opciono) Provjera kroz network proxy

Ovaj korak je za one koji žele svojim očima vidjeti da Anthropic SDK
zaista šalje thinking parametar u request body-ju kad postavimo
`effort=medium`. Koristi `mitmproxy` alat koji presretne HTTPS
saobraćaj i pokaže ti sadržaj request-a.

```bash
mitmweb --listen-port 8888 --set ssl_insecure=true &
HTTPS_PROXY=http://localhost:8888 \
SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem \
CHAT_MODEL_EFFORT=medium \
.venv/bin/python -c "
from app.agent import run_agent
print(run_agent([{'role':'user','content':'Test'}], 'chat')['_trace']['model'])
"
```

Otvori `http://localhost:8081` u browser-u, klikni request `POST
/v1/messages`, otvori "Request" tab. U JSON body-ju treba da vidiš
polje `thinking` sa vrijednošću `{"type": "enabled", "budget_tokens":
1024}`.

Ako nemaš mitmproxy instaliran, preskoči ovaj korak — test 2 (helper
output) je dovoljna garancija.

## Gdje su izmjene u kodu

Ovo je referentna lista za one koji žele pogledati izvor:

- `app/config.py:15` — definicija dozvoljenih vrijednosti za effort
  (`Literal["low", "medium", "high"]`).
- `app/config.py:41,43` — polja za Anthropic kanale (`chat_model_effort`,
  `email_model_effort`).
- `app/config.py:54,56` — polja za PWR kanale (`pwr_chat_model_effort`,
  `pwr_email_model_effort`).
- `app/agent.py:158` — funkcija koja vraća effort za kanal i backend.
- `app/agent.py:180` — funkcija koja od effort vrijednosti pravi
  Anthropic thinking kwargs.
- `app/agent.py:237,247` — mjesto gdje se thinking kwargs prosljeđuju
  Anthropic API pozivu.
- `app/agent.py:371` — mjesto gdje se `reasoning_effort` prosljeđuje
  PWR API pozivu.

## Kako se vratiti u staro stanje

Ako želiš poništiti efekat ove kartice — ne diraš .env, ili u njemu
postaviš sve effort vrijednosti na `low`. Helper za Anthropic tada
vraća praznu strukturu (isto ponašanje kao i prije kartice). Za PWR
efekat je isti: prosljeđujemo `reasoning_effort="low"`, što je
podrazumijevana vrijednost na PWR strani.

Za potpuno vraćanje na čistu Anthropic produkciju (PWR isključen),
postavi `LLM_BACKEND=anthropic` u .env ili obriši taj red — Anthropic
je default.
