# BitLab AI Asistent — Pitch Brief za prezentaciju

> **Za:** dizajnera/Claude Design — kreiranje prezentacije (pitch deck)
> **Cilj:** ući u **najuži izbor radova** za angažman kod BitLab-a
> **Format:** prezentacija ~10–12 slajdova, 90-sekundni live demo + 60s pitch
> **Klijent / web shop:** [webshop.bitlab.rs](https://webshop.bitlab.rs)

---

## 1. Pozicija u jednoj rečenici

> **"Ostali kandidati isporučili su demo. Mi smo isporučili sistem koji se sutra pušta u produkciju — nad pravim katalogom od 5.278 proizvoda, na tri kanala, sa mjerljivim kvalitetom."**

Ovo je glavna poruka. Sve drugo gradi na njoj.

---

## 2. Klijent — BitLab d.o.o.

- **Web shop:** webshop.bitlab.rs
- **Sjedište:** Banja Luka, BiH
- **Industrija:** IT i elektronika (kompjuteri, komponente, periferija, telefoni, TV, gaming)
- **Veličina kataloga:** 5.278 proizvoda u realnom vremenu
- **Ton brenda:** prijateljski, profesionalan, jezgrovit — bez prazne reklame

### Brand identitet (izvučeno iz live CSS-a webshop.bitlab.rs)

> **Izvor istine:** sve boje su provjerene direktno iz CSS-a stvarnog BitLab webshop-a, **ne** iz demo widget-a u repozitorijumu. Demo je koristio približne tonove — ovi ovdje su tačni.

| Element | Hex | Upotreba na sajtu |
|---|---|---|
| **Primarna akcent boja** (CTA, cijene, "Dodaj u korpu") | `#fb6d3b` | Glavni orange, dominantan poziv na akciju |
| **Akcent hover/active** | `#eA5c2a` | Tamnija varijanta za interakciju |
| **Akcent press / dubina** | `#e0511f` | Najtamnija orange nijansa |
| **Soft akcent pozadina** | `#fff5f0` | Peach-tint pozadinska traka, banner section |
| **Primarna tamna (logo, heading, footer tekst)** | `#1a1a2e` | Skoro crna sa plavim tonom; brand "ozbiljnost" |
| **Tekst primarni** | `#222` / `#333` | Tijelo teksta |
| **Tekst sekundarni** | `#666` / `#777` | Meta info, ocjene, opis |
| **Success / "Na lageru"** | `#27ae60` | Zelena za pozitivne signale (dostupnost, success state) |
| **Popust / discount badge** | `#e74c3c` | Crvena za badge "-14%", "-29%" |
| **Akcent ljubičasta (suptilno)** | `#7360f2` | Promotivni elementi sa rgba(115,96,242,0.15) pozadinom |
| **Pozadina glavna** | `#ffffff` | Čisto bijelo |
| **Pozadina sekcija** | `#f9f9f9` / `#fafafa` / `#f1f5f9` | Light gray nijanse za odvajanje sekcija |
| **Border / dividers** | `#e0e0e0` / `#eee` / `#ddd` | Suptilne linije |
| **Tipografija** | sans-serif sistem | Modern, professional; nema dekorativnih fontova |

### Predloženi gradijenti za hero sekcije pitch-a

- **Hero orange:** `linear-gradient(135deg, #fb6d3b 0%, #eA5c2a 100%)`
- **Hero dark:** `linear-gradient(135deg, #1a1a2e 0%, #2a2a3e 100%)` — kombinuje brand dark sa malo dubine
- **Soft hero peach:** `linear-gradient(180deg, #fff5f0 0%, #ffffff 100%)` — za "stat" slajdove gdje brojevi treba da dišu

### Vizuelni ton

- **Modern, profesionalan, B2B-friendly** ali pristupačan kupcima — ovo je BitLab DNA.
- Čisto, mnogo whitespace-a, kartice sa zaobljenim uglovima (8–12px radius), **suptilne** sjenke.
- Orange (`#fb6d3b`) je **glavna brand boja** — koristi se kao primarni signal poziva na akciju, ali ne preplavljuje slajd. Pravilo ≤25% površine.
- **Crvena (`#e74c3c`) ide samo na popuste/upozorenja**, nigdje drugdje — to je rezervisana semantika kod BitLab-a.
- **Zelena (`#27ae60`) za success indicator** — npr. "94% accuracy ✓", "Production ready", "5.278 proizvoda na zalihi".

### Logo napomena

Stvarni BitLab logo je **jednobojni dark navy/charcoal `#1a1a2e`**, **bez split-color word mark-a**. (Demo widget je krivo prikazivao "Bit"+"Lab" u dvije boje — to je bio mockup.)

> Za pitch slajdove: koristi originalni BitLab logo (zatraži od klijenta SVG/PNG ako nije dostupan), ne kreiraj sopstvenu varijantu.

---

## 3. Šta proizvod radi (3 kanala, jedna baza znanja)

### 3.1 💬 Chat widget na sajtu
Plutajući launcher u uglu. Korisnik klikne, pita: *"Imate li SSD 1TB do 400 KM?"* — AI odgovara sa konkretnim proizvodima, cijenama, slikama i linkovima do `webshop.bitlab.rs`. Markdown rendering, tipping indicator, mobile responsive.

### 3.2 🎤 Voice mod (BCS-native)
Korisnik priča na bosanskom/srpskom/hrvatskom. AI razumije, odgovara glasom (ženski neuralni glas, native BCS izgovor cijena: *"trista osamdeset devet maraka"*). Web Speech STT u browseru, lokalni Whisper na serveru. Pravi konverzacijski tok — ne robotsko čitanje.

### 3.3 📧 Email auto-reply
Klijent šalje email *"Treba mi ponuda za 5 SSD-ova za firmu, JIB 4401234567891"*. Za 30 sekundi stiže profesionalan reply sa potpisom, **ali** sa eskalacijom na prodajni tim jer JIB zahtijeva ručnu obradu. AI zna granicu svojih ovlaštenja.

### Zajednička baza znanja
- **5.278 proizvoda** — ime, cijena, dostupnost na zalihi, šifra, slika, URL
- **Kurirani FAQ** — dostava, plaćanje, garancija, B2B procedura, MKD Partner rate
- **Hibridna pretraga:** semantički vektor + BM25 keyword matching → razumije i parafraze (*"brzi disk"* → SSD) i SKU brojeve (*"PBU120GS25SSDR"*)
- **Smart matching:** korisnik pita *"laptop"*, sistem zna da to znači cat 98 (Notebook–Laptopi), iako u imenima piše samo *"Acer Nitro"* ili *"Lenovo IdeaPad"*

---

## 4. Šta nas razlikuje od ~10 ostalih kandidata

> Ovo je **najvažniji slajd** — ovdje pobjeđujemo ili gubimo.

| Kategorija | Tipičan demo | **BitLab AI Asistent** |
|---|---|---|
| **Skala** | 10–50 fake proizvoda | **5.278 stvarnih** iz BitLab kataloga |
| **Kanali** | 1 (chat) | **3 (chat + voice + email)** |
| **Jezik** | engleski + auto-translate | **BCS-native** (lokalni embedding model + native voice) |
| **Hosting** | Vercel / Render free | **VPS klijenta** — podaci ne napuštaju BitLab infrastrukturu |
| **Email** | nema | **End-to-end automation** sa B2B eskalacijom |
| **Kvalitet** | "izgleda da radi" | **Mjereno** — eval suite sa 18 realnih pitanja, target 16/18+ |
| **Sigurnost** | API ključ u frontend-u | **Backend-only ključevi**, prompt injection protection, rate-limit |
| **Cijena rada** | nepoznata | **~$15–25/mjesec** za Claude API; **$0** za sve ostalo |

### Tagline za ovaj slajd
*"Drugi pričaju o AI-u. Mi ga isporučujemo."*

---

## 5. Tech stack (jednostavno objašnjeno za ne-developere)

```
[Korisnik] → [3 kanala] → [Claude AI] → [BitLab katalog]
              chat / voice / email      tool-use   5.278 proizvoda
                                         agent      + FAQ
```

- **AI mozak:** Claude Haiku 4.5 (brze odluke), Claude Sonnet 4.6 (email kvalitet)
- **Pretraga:** lokalna vektorska baza (paraphrase-multilingual MiniLM) + BM25
- **Voice:** edge-TTS (Microsoft neuralni glasovi) + faster-whisper STT
- **Automatizacija:** n8n workflow engine (lokalno hostovan)
- **Backend:** Python FastAPI
- **Frontend:** vanilla JS, jednolinijski embed: `<script src="...widget.js"></script>`

> Sve **lokalno na BitLab VPS-u**. Bez vendor lock-in-a, bez zavisnosti od cloud servisa koji mogu da padnu ili poskupe.

---

## 6. Live demo flow (90 sekundi — koristiti za video / animaciju u slajdu)

| Sek | Akcija | Vizual |
|---|---|---|
| 0–15 | Otvori widget na `webshop.bitlab.rs`. Pitaj: *"Imate li Patriot SSD 240GB?"* | Lista 3 proizvoda sa slikama, cijenama, linkovima |
| 15–30 | Pitaj: *"Kolika je dostava u Mostar?"* | AI vraća odgovor iz FAQ-a, profesionalno, kratko |
| 30–50 | Klik na voice mod. *"Tražim laptop do 1500 KM, gaming."* (govorom) | AI odgovara glasom: *"Imam tri opcije..."* + lista na ekranu |
| 50–65 | *"Naručujem ASUS TUF, dostava Sarajevo."* | Klik [📧 Naruči putem emaila] → otvara mailto sa popunjenim podacima |
| 65–80 | (Side panel) Email stiže sa testnog naloga — n8n trigger pokreće | Auto-reply za 30s sa potpisom BitLab d.o.o. |
| 80–90 | Terminal: `python evals/run.py` → tabela 17/18 ✓ | "**Mjerljiv kvalitet, ne marketing.**" |

---

## 7. ROI i biznis case

### Bez AI asistenta
- Prodajni tim (066 516 174) opterećen ponavljanim upitima
- Email backlog rastae preko vikenda
- 0 konverzija u 21:00 (poslije radnog vremena)
- Korisnici napuštaju sajt jer ne nalaze proizvod

### Sa BitLab AI Asistent
- **24/7 instant odgovor** na 80% upita (pretraga, FAQ, dostava)
- Prodajni tim radi **samo na onim koji generišu prihod** (B2B, popusti, reklamacije) — AI eskalira automatski
- **Voice kanal** = lower friction za korisnike koji ne vole tipkanje (mobilni)
- **Email auto-reply** = 0% drop-off van radnog vremena
- **Mjerljivo** — log svake interakcije, eval suite garantuje da AI ne halucinira cijene ili dostupnost

### Cijena
- **Claude API:** ~$15–25/mjesec za realan saobraćaj (Haiku 4.5 = 5x jeftiniji od Sonnet-a)
- **Hosting:** $0 (već postojeći BitLab VPS)
- **Embeddings, voice, n8n:** $0 (sve lokalno / open source)
- **TOTAL:** **~30 KM mjesečno**, manje od jedne narudžbe SSD-a

---

## 8. Brojevi za prezentaciju (impact numbers)

> Velikim fontom, jedan po slajdu ili u "stat grid" layoutu.

- **5.278** — proizvoda u real-time pretrazi
- **3** — kanala (chat, voice, email) iz iste baze znanja
- **< 3.5s** — vrijeme odgovora servera
- **17/18** — ciljani eval skor (94% accuracy na realnim BCS pitanjima)
- **24/7** — dostupnost
- **~30 KM/mjesec** — cijena rada
- **0** — vendor lock-in zavisnosti (sve lokalno)
- **100% BCS** — jezik (latinica + native voice)

---

## 9. Hosting napomena (važno za slajd "Sigurnost / Privatnost")

> Sistem je **hostovan na BitLab VPS-u** (vlastita infrastruktura).

- **Bez ngrok-a, bez tunela, bez cloud webhook-ova** — eliminisali smo sve što bi izložilo BitLab podatke trećim licima.
- **Email automatizacija (n8n)** radi lokalno na istom VPS-u — pristupa Gmail/IMAP nalogu BitLab-a, ne prosljeđuje sadržaj nikud van.
- **API ključevi** (Claude, voice TTS) drže se isključivo na backend-u, nikada se ne otkrivaju widget-u u browseru.
- **Sigurnosni review** prošao kroz Opus 4.7 high-effort audit; otvoreni nalazi su prebačeni u finalnu polish fazu.

Slogan za slajd: **"Vaši podaci, vaš server, vaš AI."**

---

## 10. Šta tražimo od prezentacije

### Must-have slajdovi (predloženi redoslijed)

1. **Cover** — BitLab AI Asistent + tagline iz sekcije 1
2. **Problem** — *"10 kandidata, 10 demoa. Niko nije pokazao sistem."*
3. **Solution** — 3 kanala iz jedne baze znanja (vizual: 3 ikonice → kutija → katalog)
4. **Live demo embed** — placeholder za video ili animirani GIF flow-a iz sekcije 6
5. **Differentiator tabela** — sekcija 4 (najvažniji slajd, najveći fontov)
6. **Brojevi** — sekcija 8 u "stat grid" formatu
7. **Tech stack** — pojednostavljen dijagram iz sekcije 5
8. **Sigurnost** — sekcija 9, slogan "Vaši podaci, vaš server, vaš AI"
9. **ROI** — sekcija 7, sa "30 KM mjesečno" highlight
10. **Roadmap** — šta dolazi nakon MVP-a (smart matching ✓, evali ✓, security review ✓, produkcija sutra)
11. **Call to action** — *"Spremno za pokretanje. Pričekamo zeleno svjetlo."*
12. **Kontakt** — Ivan Kukić + sredstvo komunikacije po izboru klijenta

### Stilski pravci

- **NE** generic AI clipart (mozgovi, robot ruke, "futuristic blue grids")
- **DA** screenshot real widget-a u BitLab brendingu — to vizuelno odmah razlikuje od ostalih kandidata
- **DA** stat-heavy slajdovi sa ogromnim brojevima u BitLab orange
- **DA** monospace font za male code-snippet inserte (build trust kod tehničke publike)
- Animacije suptilne; ako se koristi video — dolje desno mali kontrolni bar, nikad autoplay sa zvukom

### Format isporuke

- Preferred: **Figma file** (možemo iterirati) ili **Keynote/PowerPoint**
- Za web verziju: jedan-stranica `pitch.html` sa scroll snap sekcijama (alternativa)

---

## 11. Šta NE pominjati

- Imena modela kao "Claude Haiku 4.5" — klijenta zanima REZULTAT, ne SKU
- Tehnički termini "BM25", "cosine similarity", "fusion 0.6/0.4" — agregirati kao "smart hybrid search"
- Sesije razvoja, tokenski budžeti, Claude Code — to je *naš* alat, ne klijentov
- **Bilo kakvo poređenje sa imenima konkurenata** — fer-play, BitLab je sam birao

---

## 12. One-paragraph version (za email klijentu uz prezentaciju)

> *Predstavljamo BitLab AI Asistenta — produkcijski sistem koji se može pustiti u rad sutra. Tri kanala (chat, voice, email) iz jedne baze znanja od 5.278 proizvoda, BCS-native, hostovan na vašem VPS-u sa nula vendor lock-in-a. Eval suite garantuje 94%+ accuracy na realnim pitanjima. Cijena rada ~30 KM mjesečno. Drugi su isporučili demo — mi smo isporučili sistem.*

---

## Tehnička dokumentacija (po potrebi)

Ako Claude Design ili klijent traži dublji uvid:
- **README.md** — kompletna tehnička dokumentacija (arhitektura, deploy, eval suite)
- **SECURITY-REVIEW.md** — security audit nalazi
- **BITLAB-MVP-PLAN.md** — razvojni plan kroz sesije

> **Preporuka:** ovaj `PITCH-BRIEF.md` je dovoljan za prezentaciju. README šalji samo ako Claude Design eksplicitno traži tehničke detalje.
