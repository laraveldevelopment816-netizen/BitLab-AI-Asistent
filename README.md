# BitLab AI Asistent — Projektni Brief

---

## Naziv projekta

**BitLab AI Asistent**
*Inteligentni chatbot widget za webshop.bitlab.rs*

---

## Cilj projekta

Implementirati AI asistenta na webshop.bitlab.rs koji automatski odgovara na uobičajena pitanja kupaca — 24 sata dnevno, 7 dana u sedmici — bez angažovanja prodajnog osoblja, i time smanjiti pritisak na Viber/email podršku, povećati stopu konverzije i pružiti bolji korisnički doživljaj.

---

## Opis projekta

BitLab AI Asistent je chatbot widget koji se ugrađuje u postojeći webshop kao jedan HTML/JavaScript blok koda. Posjetilac sajta u donjem desnom uglu ekrana vidi plutajuće dugme "Pitaj AI", klikne, i odmah dobije odgovor na pitanje — bez čekanja, bez pretraživanja stranica, bez poziva.

Asistent je obučen specifično za BitLab: zna sve o kategorijama proizvoda, brendovima, načinima plaćanja, dostavi, garancijama, B2B procedurama i kontakt informacijama. Razumije prirodan jezik na BCS govornom području i odgovara kratko, precizno i profesionalno.

Tehnološki se oslanja na Claude Haiku model (Anthropic) koji prima pitanje posjetioca i generiše odgovor u realnom vremenu, direktno u browseru posjetioca.

---

## Šta BitLab AI Asistent radi

**Odgovara na pitanja o dostavi**
"Dostavljate li u Mostar?", "Koliko košta dostava?" → odmah, tačno, bez čekanja.

**Objašnjava načine plaćanja**
Žiralno, pouzećem, gotovinski, plaćanje na rate putem MKD Partner — asistent zna sve opcije i upućuje kupca na pravi put.

**Informiše o garanciji i servisiranju**
"Šta ako se pokvari?", "Koliko traje garancija?" — standardni odgovori dostupni u sekundi.

**Vodi B2B kupce kroz proces**
Firme koje trebaju predračun, JIB/PIB fakturu i prateću dokumentaciju dobivaju jasne upute odmah.

**Preusmjerava složene upite**
Kad kupac pita nešto što zahtijeva provjeru stanja na lageru ili individualne pregovore, asistent ljubazno upućuje na Viber (066 516 174) ili email (prodaja@bitlab.rs).

**Radi non-stop**
Kupac u 23h, vikendom, ili za vrijeme praznika dobiva isti kvalitet odgovora kao u radno vrijeme.

**Čuva kontekst razgovora**
Asistent pamti šta je rečeno ranije u istoj sesiji, što omogućava prirodan, višepotezni razgovor.

---

## Benefiti

### Za BitLab tim

| Benefiti | Procjena |
|---|---|
| Smanjenje repetitivnih upita na Viberu/emailu | 60–70% |
| Ušteđeno radno vrijeme tjedno | 4–6 sati |
| Dostupnost podrške | 24/7 umjesto 7–22h |
| Trošak Claude API-ja | ~$10–30 / mjesečno |

**Manje prekida u radu.** Prodajni tim se može fokusirati na složene upite, B2B pregovore i zatvaranje prodaje, umjesto da odgovaraju na "Koliko košta dostava?".

**Instant odgovor = veća konverzija.** Istraživanja pokazuju da kupac koji ne dobije odgovor u 60 sekundi napušta stranicu. AI asistent odgovara za 2–3 sekunde.

**Pokritost van radnog vremena.** Kupci naručuju i u 22h ili nedeljom — AI ne spava.

### Za kupce

**Brz odgovor bez čekanja.** Nema telefona koji zvoni, nema reda za odgovor na email.

**Lako pronalaženje informacija.** Umjesto pretraživanja po stranicama, jedan direktan razgovor.

**Prirodan jezik.** Kupac piše onako kako bi rekao prodavaču, ne mora znati gdje je koji meni.

### Strateški

**Skalabilnost bez troška zapošljavanja.** Broj kupaca može porasti 10x, asistent se ne umara.

**Profesionalan dojam.** AI chatbot na webshopu signalizira da je firma inovativna i orijentisana na korisnika.

**Osnova za nadogradnju.** Widget je prvi korak — lako se nadograđuje Voice AI podrškom, agentom koji provjeri dostupnost u realnom vremenu, ili integracijom sa CRM sistemom.

---

## Tehnički stack

| Komponenta | Tehnologija |
|---|---|
| Frontend | HTML5 + CSS + Vanilla JavaScript |
| AI model | Claude Haiku (Anthropic API) |
| Integracija | Jedan `<script>` blok pred `</body>` tagom |
| Hosting | Bez promjena — radi na postojećem serveru |
| Backend (za produkciju) | PHP/Node.js proxy za API ključ (sigurnost) |

---

## Opseg MVP verzije

**Uključeno:**
- Chatbot widget sa BitLab brendingom
- System prompt sa kompletnim znanjem o BitLab-u
- Multi-turn razgovor (pamti kontekst)
- Typing indikator i smooth UX
- Uputa za webmastera za integraciju

**Nije uključeno u MVP (planirana nadogradnja):**
- Integracija sa live bazom proizvoda (realtime dostupnost)
- Voice AI komponenta
- n8n email auto-reply
- Admin panel za praćenje razgovora
- Backend proxy za sigurno upravljanje API ključem

---

## Rok isporuke

**MVP:** Isti dan (u toku obuke)
**Produkcijska integracija:** 1–2 radna dana (webmaster)
**Puna verzija sa backendom:** 1–2 sedmice

---

*Projekat realizovan u okviru AI Forward Faza 2 programa — ICBL Banja Luka + Bloomteq*
*Predavač: Đuro Grubišić*
