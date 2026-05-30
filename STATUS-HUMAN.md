# STATUS — ljudska verzija

Prevod `STATUS.md` na prirodan jezik. `STATUS.md` ostaje zvanični (sa ID-jevima
i tehničkim detaljima koje čitaju alati/skill-ovi); ovaj fajl je da se brzo
podsjetiš **šta koja kartica zapravo znači**. Ako se razlikuju — `STATUS.md` je
mjerodavan. ID u zagradi (npr. `setp`) je da karticu nađeš u `STATUS.md`.

## U čemu je cijela priča

Asistent za webshop bitlab.rs treba da, kad ga korisnik nešto pita, **pozove
alat** koji vuče prave podatke iz kataloga — umjesto da sam izmišlja proizvode i
cijene. Postoje dva alata: `category_overview` (pregled široke kategorije, npr.
"Mobiteli") i `search_products` (konkretna pretraga kad upit ima brend, model ili
cijenu).

Imamo automatski test od 250 upita koji mjeri koliko tačno asistent rutira —
svaki upit je PASS ili FAIL, rezultat je procenat. To zovemo **eval**.

Problem koji rješavamo: u jednoj verziji (iter17) procenat je pao sa 84.4% na
79.2%. Kad smo to raščlanili, ispalo je da model u lošim slučajevima **prestane
da zove alat i počne da izmišlja katalog**. Krivac nije logika nego prompt — bio
je prenatrpan prozom ("OBAVEZNO uradi X") umjesto da model mehanički natjeramo da
pozove alat. Cijeli plan ispod popravlja tačno to, korak po korak.

**Kako mjerimo (važno):** pun eval od 250 traje ~15h i skup je — glupo ga je
vrtjeti na svaku sitnu izmjenu. Zato dok **podešavamo prompt mjerimo na malom
uzorku teških slučajeva** (oni koji su baš pukli u iter17 — ~37 upita, par
minuta), a **pun test od 250 pustimo tek na kraju** kao završnu provjeru.
Napomena: NE koristimo nasumičnih 30 — to je već jednom slagalo (pokazalo
93-100% dok je stvarno bilo 79%), jer promaši baš teške slučajeve.

## Šta je već urađeno

- **Dijagnoza pada** (`i17r`) — Detaljno upoređena stara verzija (84.4%) i nova
  (79.2%). Svih 29 pogoršanih slučajeva = model nije pozvao alat nego izmislio
  katalog; nijedan nije bio pogrešno rutiran. Zaključak: kriva je proza u
  promptu, ne logika rutiranja.
- **Temelji** (`fz00`) — Postavljena cijela infrastruktura: autonomna petlja
  (Ralph), testovi sa mock-ovima i eval framework koji mjeri procenat.

## Šta slijedi (ovim redom)

1. **Brzi uvid** (`setp`) — *nije pod testom*
   Pokreneš `scripts/smoke.py` (već napisan) — pusti agenta na par upita i ispiše:
   je li pozvao alat, koliko iteracija, šta je vratio. Samo da vidiš ponašanje na
   oko, bez ocjene. Komanda: `.venv/bin/python scripts/smoke.py`.

2. **Napravi mali test-uzorak** (`dsmp`) — *alat za sve naredne korake*
   Sklopi `categories_dev.jsonl`: ~29 upita koji su baš pukli u iter17 + par
   "ne smije zvati alat" kontrolnih. To je naš brzi/jeftin test na kojem
   podešavamo prompt. Pokreće se isto kao pun eval, samo na ovom malom setu.

3. **Vrati zdrav prompt** (`rvpr`) — *prva prava izmjena*
   Zamijeni naduveni prompt kratkom, čistom verzijom iz `bck/app/system_prompts.py`
   (samo logika: široka kategorija vs. konkretan proizvod). **Samo prompt, ništa
   drugo.** Mjeri na malom uzorku — očekujemo ~84-86%, bez novih padova.

4. **Mehanički natjeraj poziv alata** (`frtl`)
   Dodaj poseban alat `respond_to_user` (za odgovore van kataloga) i postavku koja
   TJERA model da nešto pozove. Model više ne može da "ćuti i izmišlja": ili pozove
   pravi alat, ili eksplicitno odgovori kroz `respond_to_user`. Mjeri na malom uzorku.

5. **Stezanje** (`tght`)
   Dvije sitne izmjene, svaka zasebno mjerena na malom uzorku: "temperatura" na ~0
   (manje nasumičnosti, predvidljivije) i ograniči `category_id` na stvarne kategorije.

6. **Prihvatanje / kraj** (`acpt`) — *odluka, ne kodiranje*
   Tek kad je mali uzorak zelen, pusti **pun test od 250 jednom** (~15h). Cilj
   **≥95%**, ILI svjesna odluka da puštamo na ~85% uz fallback "nisam siguran, evo
   opcija" za dvosmislene slučajeve.

## Mali pojmovnik

- **eval** — test od 250 upita; vraća procenat tačnih (PASS).
- **dev-uzorak** — mali izbor teških upita (~37) na kojem brzo i jeftino
  podešavamo prompt; pun eval (250) ide tek na kraju.
- **prompt** — uputstvo koje model dobije na startu; definiše kako se ponaša.
- **alat (tool)** — funkcija koju model pozove da dobije prave podatke; suprotno
  od izmišljanja.
- **forsiranje alata (`tool_choice`)** — postavka koja tjera model da pozove alat
  umjesto da sam bira hoće li.
- **baseline** — referentni rezultat s kojim poredimo (84.4%).
- **regresija** — kad nova izmjena pogorša rezultat u odnosu na prije.
