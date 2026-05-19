# Lokalno testiranje — Strukturisani search output (JSON shema + Pydantic + Layout)

Test plan za STATUS karticu `srcv` — kako verifikovati postojeću infrastrukturu
(shema + validator + widget renderer) i pratiti kad se aktiviraju kroz live AI
output.

## Trenutno stanje (važno za interpretaciju testova)

`srcv` je trenutno **dormant infrastruktura** (per commit `c50c075`):

- ✅ Shema postoji — `app/schemas.py` (Pydantic V2 discriminated union).
- ✅ Validator postoji — `assistant_response_adapter: TypeAdapter`.
- ✅ Widget renderer postoji — `public/widget.js:renderStructuredReply`,
  `formatPriceKm`, `isStructuredReply`.
- ✅ Unit testovi prolaze — 14 Python (`tests/test_response_schema.py`)
  + 10 JS (`tests/test_widget_renderer.mjs`).
- ❌ **Sistem prompt još NE traži od Claude-a da emituje JSON** — produkcijski
  output je i dalje markdown tekst. Widget detektuje shape i radi
  fallback na postojeći markdown renderer (`isStructuredReply()` vraća
  false → klasični put).
- ❌ **Validator se NE primjenjuje na run_agent output** — ako Claude
  jednog dana pošalje validan JSON, validator ne hvata to (samo testovi
  ga koriste).

Posljedica: testovi ispod verifikuju **da je infrastruktura ispravna**, ne
da live produkcija već radi strukturisano. End-to-end aktivacija je
zadatak iz `pwrt` kartice (preostala tačka #1-2: prompt update +
validator wire-up).

## Pokretanje (gdje god treba)

```bash
source .venv/bin/activate
```

## Test plan

### 1. Pydantic unit testovi (14 testova)

```bash
.venv/bin/python -m pytest tests/test_response_schema.py -v
```

Očekivano: **14 passed**. Pokriva:

- Validan payload za `ProductsResponse` / `EmptyResponse` / `MessageResponse`.
- `products: []` (prazna lista) → rejection sa jasnom porukom (0 proizvoda
  ide u `EmptyResponse`, ne `ProductsResponse`).
- Missing required polja → `ValidationError`.
- `image_url: null` prolazi (legacy proizvodi bez slike).
- `int → float` coerce za `price_km` radi.
- `price_km < 0` → rejection.
- Nepoznat `type` discriminator → rejection.
- `validate_json` sa string input-om.
- Eksportovani JSON Schema sadrži sva 3 tipa.

### 2. Widget renderer unit testovi (10 testova, Node)

```bash
node --test tests/test_widget_renderer.mjs
```

Očekivano: **10 passed**. Pokriva:

- `formatPriceKm(929)` → `"929"` (integer bez separatora).
- `formatPriceKm(1450)` → `"1.450"` (BCS thousand separator).
- `formatPriceKm(929.99)` → `"929,99"` (decimalni zarez).
- `formatPriceKm(null)` / `NaN` → fallback (provjeri ne baca exception).
- `structuredReplyToText` za `ProductsResponse` / `EmptyResponse` /
  `MessageResponse` / unknown shape / null — flatten u string za history
  storage (server još očekuje stringove u prethodnim turn-ovima).

### 3. Schema export sanity check

```bash
.venv/bin/python -c "
from app.schemas import assistant_response_adapter
import json
schema = assistant_response_adapter.json_schema()
print(json.dumps(schema, indent=2, ensure_ascii=False))" | head -60
```

Očekivano: JSON Schema sa `oneOf: [ProductsResponse, EmptyResponse, MessageResponse]`
i discriminator-om na polju `type`. Svaki sub-tip ima svoja polja
(`Product` ima šifru/name/price_km/availability/url/image_url).

### 4. Ručno validan payload (validator-side)

```bash
.venv/bin/python -c "
from app.schemas import assistant_response_adapter
payload = {
    'type': 'products',
    'text': 'Evo 2 tastature:',
    'products': [
        {'sifra': '012345', 'name': 'Gembird KB-U-103', 'price_km': 17.0,
         'availability': 'Na lageru',
         'url': 'https://webshop.bitlab.rs/G41719-...', 'image_url': None},
        {'sifra': '098765', 'name': 'Rampage K11', 'price_km': 80,
         'availability': 'Na lageru',
         'url': 'https://webshop.bitlab.rs/G99999-...', 'image_url': 'https://...'}
    ]
}
out = assistant_response_adapter.validate_python(payload)
print(type(out).__name__, '— OK')
print(out.products[0].name, '→', out.products[0].price_km)
"
```

Očekivano: `ProductsResponse — OK`, prvi proizvod ime + cijena.

### 5. Ručno NEvalidan payload (validator hvata)

```bash
.venv/bin/python -c "
from app.schemas import assistant_response_adapter
from pydantic import ValidationError
try:
    assistant_response_adapter.validate_python({
        'type': 'products', 'text': 'Test', 'products': []
    })
except ValidationError as e:
    print('REJECTED OK:', e.errors()[0]['msg'])
"
```

Očekivano: `REJECTED OK: List should have at least 1 item ...`. Empty
products lista je eksplicitno zabranjena (za 0 rezultata se koristi
`EmptyResponse`).

### 6. Widget renderer — vizuelni test u browser-u

Pripremi mock payload u dev tools console-u (sa otvorenim widget-om):

```javascript
// U DevTools Console:
const payload = {
  type: 'products',
  text: 'Evo 2 tastature do 100 KM:',
  products: [
    {sifra:'012345', name:'Gembird KB-U-103', price_km:17,
     availability:'Na lageru',
     url:'https://webshop.bitlab.rs/G41719-test',
     image_url:'https://webshop.bitlab.rs/files/products/img/0098811_test.jpeg'},
    {sifra:'098765', name:'Rampage K11', price_km:80,
     availability:'Na lageru',
     url:'https://webshop.bitlab.rs/G99999-test',
     image_url:null}
  ]
};
addMsg('bot', payload);  // ako je addMsg eksposovan globalno
```

Očekivano: u chat balon-u se renderuju 2 product card-a sa slikom (ili
placeholder-om za null image_url), ime, cijena formatirana kao "17 KM" /
"80 KM", availability tekst, link "Pogledaj".

Probaj i `type:'empty'` (sa `message: 'Nismo našli proizvode.'`) i
`type:'message'` (sa `content: 'Plain tekst odgovor.'`) — svaki tip ima
svoj layout.

### 7. End-to-end (kad se srcv aktivira — TBD)

**Trenutno NE radi** — sistem prompt nije ažuriran, validator nije
priključen u `run_agent`. Kad ovo bude gotovo (per `pwrt` kartica
preostali rad #1-2), provjera ovde se piše:

```bash
# Plan:
# 1. Postavi LLM_BACKEND=anthropic (ili pwr).
# 2. Pošalji curl koji bi normalno trigger-ovao search_products.
# 3. Server vraća JSON sa `reply` poljem koje je strukturisan objekat
#    (ne string), shape mečuje shemu, validator je već prošao na server-u.
# 4. Browser widget renderuje preko `renderStructuredReply`, ne markdown
#    fallback.

curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam tastaturu","channel":"chat"}' | jq '.reply'

# Očekivano (POSLIJE prompt update-a):
# {
#   "type": "products",
#   "text": "Evo X tastatura:",
#   "products": [...]
# }
#
# Trenutno: reply je markdown string sa proizvodima.
```

Test da widget koristi structured put a ne fallback:

```javascript
// U DevTools Console, posmatraj poslje POST-a na /api/chat:
// Ako je reply objekat sa `type`, ide kroz renderStructuredReply.
// Ako je string, ide kroz markdownToHtml fallback.
//
// Network tab → response body → reply field — provjeri da li je objekat.
```

## Kako da znaš koji put je aktivan u trenutku (production debugging)

`public/widget.js:isStructuredReply(reply)` je single source of truth:

```javascript
function isStructuredReply(x) {
  return x && typeof x === 'object'
    && typeof x.type === 'string'
    && ['products', 'empty', 'message'].includes(x.type);
}
```

Ako vraća `true` → structured renderer, validator je prošao na server-u.
Ako `false` → markdown fallback, server je vratio plain string. Možeš
break-pointirati ovu funkciju u DevTools-u ako želiš da pratiš tok.

## Preostali rad za pwrt #1-2 (srcv aktivacija)

1. **Sistem prompt** (`app/system_prompts.py`) — dopuniti chat prompt sa
   strogim "Ako pozoveš search_products, finalni odgovor je JSON objekat
   ovog oblika..." i embedded JSON Schema iz
   `assistant_response_adapter.json_schema()`.
2. **Validator wire-up** (`app/agent.py:_finalize`) — pokušaj
   `assistant_response_adapter.validate_json(reply_text)`. Na uspjeh:
   propagiraj objekat kao `reply` (ne string). Na fail: log error,
   degradiraj na string (postojeće ponašanje) — ne ruši UX.
3. Re-test sve gore (step 7 postaje aktivan).
