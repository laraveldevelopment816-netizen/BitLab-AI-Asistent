# Prompt best practices — webshop asistent (istraživanje 2026-05-29)

> Istraživanje na zahtjev: kako se gradi sistem prompt za e-commerce/webshop
> asistenta sa tool callingom — **standard, ne ad-hoc**. Vezano za eval regresiju
> iz `EVAL_REGRESIJA_iter17.md` (model prestaje da zove tool i halucinira katalog).

## Ukratko — šta je standard

Webshop asistent koji odgovara na upite o katalogu je **RAG + tool-calling**
pattern, ne "veliki sistem prompt pun pravila". Tri stuba:

1. **Forsiraj tool poziv mehanički, ne molbom u promptu.** Naš bug (29/29 bez
   tool poziva) se NE rješava boljom prozom — rješava se `tool_choice`
   parametrom: OpenAI `tool_choice:"required"` (mora neki tool) ili named tool;
   Anthropic ekvivalent `tool_choice:{"type":"any"}` ili
   `{"type":"tool","name":...}`. Standardni pattern: **forsiraj tool na početku**
   (kad znaš da je prvi korak "pretraži katalog"), pa pređi na `auto`. Ovo je
   garancija, ne nadanje da će model poslušati "OBAVEZNO PROBAJ TOOL".
2. **Logika rutiranja ide u tool schemu, ne u sistem prompt.** Opis svakog toola
   piši kao junioru: šta radi, KAD se koristi, kad NE. Parametre stegni `enum`-om
   (npr. validni `category_id`-evi) — manje halucinacije parametara. Leaf-vs-parent
   disambiguacija = enum + jasan opis toola, ne 36 linija imperativa u promptu.
3. **Grounding: odgovaraj SAMO iz tool rezultata; ako nema — odbij.** E-commerce
   istraživanje ("Cite Before You Speak", arXiv) pokazuje da citiranje + "refusal
   signal" kad retrieval ne vrati dovoljno **smanjuje halucinaciju** (+13.83%
   grounding). Kod nas: prazan tool rezultat → "trenutno nemam podatke", BEZ
   izmišljanja. Najbolje arhitekturno (forsiran tool + post-validacija da svaki
   pomen proizvoda/cijene ima tool rezultat iza sebe), ne samo prozom — Group B je
   probao prozom i pao.

## Detaljnije (best practices + izvori)

- **Tool descriptions su gdje se donosi odluka o rutiranju.** Piši eksplicitno
  "kad koristiti i kad NE"; koristi `required` polja i `enum` da smanjiš
  halucinaciju parametara. *(OpenAI function calling guide; Medium "Tool/Function
  calling best practices".)*
- **`tool_choice` modovi:** `auto` (0+ poziva), `required`/`any` (mora poziv),
  named (tačno taj tool), `none` (natjeraj tekstualni odgovor). Forsiraj na startu
  workflow-a, pa `auto` dalje. *(OpenAI API docs + community.)*
- **Niska temperatura (0.0–0.3)** za deterministički izbor toola i manje
  halucinacije parametara. *(Function-calling vodiči.)*
- **Struktura prompta (Anthropic 2025):** XML-tagovane sekcije (`<role>`,
  `<rules>`, `<examples>`), schema-first dizajn, role prompting, i 1–2
  demonstraciona tool poziva (few-shot). Claude 4.x uzima instrukcije **doslovno**
  — zato jasna struktura, ne gomila bulleta. *(Anthropic prompting best practices.)*
- **Nikad ne izmišljaj proizvode/cijene/stock** — ako katalog nema, reci. RAG drži
  odgovore tačnim; vektorska baza mora biti u sync-u sa katalogom (loš sync →
  high-confidence halucinacije). *(Algolia; Shopify; e-commerce grounding članci.)*
- **MCP / standardni "shopping verbs"** kao tools (`search_products`,
  `get_product`, …); potvrda akcije samo na eksplicitno "da". *(Opascope agentic
  commerce; AssemblyAI.)*

## Predlog way-forward za bitlab (da zajedno uskladimo)

1. **`tool_choice` = required/any** na catalog upitima (ili forsiraj prvi poziv).
   Direktno ubija 29 apstinencija. → provjeri da li **PWR** (OpenAI shape)
   prosljeđuje `tool_choice`; Anthropic put sigurno podržava.
2. **Temperatura ~0.0–0.2** za routing poziv.
3. **Premjesti category mapping u tool schemu** (enum imena→id), oslabi sistem
   prompt na čist XML-strukturiran `role` + 1–2 primjera poziva — suprotno od
   trenutnih 36 linija imperativa.
4. **Grounding guard:** prazan tool rezultat → odbij; opciono post-validacija
   (reply koji pominje proizvod bez prethodnog uspješnog tool poziva = auto-FAIL).
5. **Pa pun eval** (ne sample) da izmjerimo — očekivano: apstinencija nestaje.

Ovo miri tvoju poentu ("standardan problem — ne izmišljaj") i nalaz iz podataka
("apstinencija je bug"): popravka je **arhitekturna** (tool_choice + schema +
grounding), ne dalje štelovanje proze. Otvoreno pitanje za zajedno: ako uvedemo
forsiran tool + schema, da li je Ralph petlja uopšte potrebna za ovo, ili je
dovoljan jedan čist rebuild + pun eval.

## Izvori

- Anthropic — Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- OpenAI — Function calling guide: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI community — forcing `tool_choice:"required"`: https://community.openai.com/t/new-api-feature-forcing-function-calling-via-tool-choice-required/731488
- Tool/Function calling best practices (Medium, L. Kubaski): https://medium.com/@laurentkubaski/tool-or-function-calling-best-practices-a5165a33d5f1
- "Cite Before You Speak" — grounding e-commerce LLM agents (arXiv): https://arxiv.org/pdf/2503.04830
- Algolia — AI shopping assistants guide: https://www.algolia.com/blog/ecommerce/ai-shopping-assistants
- Opascope — AI shopping assistant / agentic commerce 2026: https://opascope.com/insights/ai-shopping-assistant-guide-2026-agentic-commerce-protocols/

---

## Dopuna nakon provjere repoa + gotovih referenci (2026-05-29)

**Vaš stari prompt JE najbolja baza — ne treba izmišljati.**
`bck/app/system_prompts.py` (versioniran u commit-u `6a90559`) je zreo, dobro
strukturisan multi-channel prompt: `BITLAB_BASE` (firma, uloga, pravila) +
`CHAT/VOICE/EMAIL_FORMAT`. Već ima:
- čistu **leaf/parent** logiku (pravilo 1b: golo ime parenta → `category_overview`;
  čim ima kvalifikator → `search_products`) — tačno ono što je current
  `SYSTEM_PROMPT_V1` pokvario;
- anti-halucinaciju (pravilo 1: "NIKAD ne izmišljaj… OBAVEZNO `search_products`");
- bogatiji tool set (`search_products`, `category_overview`, `get_faq`,
  `check_availability`, `escalate_to_human`);
- prompt-injection zaštitu, ton, format kartica.

Bolja polazna tačka od bilo kog generičkog online prompta (tailored na vaš katalog
i alate). → **revive bck prompt kao bazu**, ne piši iz nule.

**Ispravka o `tool_choice`:** provjereno — `tool_choice` NE postoji ni u starom
(`bck/app/agent.py:250`) ni u trenutnom (`app/agent.py:153`) kodu; oba zovu
`messages.create(... tools=...)` BEZ njega. `tool_choice` nije linija prompta nego
**API parametar** — fali svuda. Stari prompt se oslanja na PROZU ("OBAVEZNO koristi
alat") da izazove tool poziv, a baš to proza ne garantuje (otud 29 apstinencija).

**Gotova, provjerena referenca za naš bug — OpenAI Cookbook "tool required":**
- Svaki API poziv ide sa `tool_choice="required"` → model MORA pozvati neki tool,
  nikad ne odgovara slobodnim tekstom.
- Alati se dijele na: **non-response** (`get_instructions`; kod nas `search_products`,
  `category_overview`) → petlja se nastavlja, model dobije rezultat pa se ponovo
  pita; i **response** alat (`speak_to_user`) → time model "govori" korisniku i tek
  tad se potez završava.
- Posljedica: model NE MOŽE da proizvede odgovor o proizvodu a da prije nije pozvao
  katalog-tool. **Halucinacija postaje strukturno nemoguća** — dizajnom petlje, ne
  molbom. Tačan lijek za naših 29 NONE-regresija.
- GPT-4.1 guide: "uvijek pozovi tool prije faktografskog odgovora o
  proizvodima/ponudi/nalogu; koristi samo retrieved context" — isti princip.
- Sendbird `ecommerce-ai-chatbot` (GitHub) — konkretan open-source primjer za uporedbu.

**Rafiniran way-forward:**
1. **Baza = revive `bck` prompt** (čist, tailored), ne generički online ni current bloated.
2. **Dodaj `tool_choice` = required/any** (Anthropic `{"type":"any"}`) na catalog upite —
   fali svuda; glavni mehanički fix.
3. (Jako preporučeno) **`respond_to_user` tool** po cookbook patternu → user-facing
   odgovor gated iza tool poziva; halucinacija strukturno nemoguća.
4. **Category mapping u schemu** (enum imena→id), niska temperatura.
5. **Pun eval** (ne sample) za mjerenje.

Instinkt "ne izmišljaj, uzmi gotovo" je tačan — samo je "gotovo" ovdje (a) tvoj
vlastiti stari prompt + (b) cookbook tool-required pattern, ne generički webshop prompt.

### Dodatni izvori
- OpenAI Cookbook — Using tool required for customer service: https://developers.openai.com/cookbook/examples/using_tool_required_for_customer_service
- OpenAI Cookbook — GPT-4.1 Prompting Guide: https://cookbook.openai.com/examples/gpt4-1_prompting_guide
- Sendbird — ecommerce-ai-chatbot (GitHub): https://github.com/sendbird/ecommerce-ai-chatbot
