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
pozove alat. Cijeli plan ispod popravlja tačno to, korak po korak. Pravilo:
poslije svake izmjene pokrećemo pun test, i **ništa ne smije da padne** ispod
84.4%.

## Šta je već urađeno

- **Dijagnoza pada** (`i17r`) — Detaljno upoređena stara verzija (84.4%) i nova
  (79.2%). Svih 29 pogoršanih slučajeva = model nije pozvao alat nego izmislio
  katalog; nijedan nije bio pogrešno rutiran. Zaključak: kriva je proza u
  promptu, ne logika rutiranja.
- **Temelji** (`fz00`) — Postavljena cijela infrastruktura: autonomna petlja
  (Ralph), testovi sa mock-ovima i eval framework koji mjeri procenat.

## Šta slijedi (ovim redom)

1. **Brzi uvid / spike** (`setp`) — *nije pod testom, baci poslije*
   Cilj je samo da uđemo u kod i vidimo uživo kako se model ponaša. Privremeno
   ubacimo čist prompt i natjeramo poziv alata, pa napravimo **jedan** poziv i
   zapišemo tri stvari: je li pozvao alat, koliko iteracija, šta je vratio. Kod
   za ovo je **već u** `app/agent.py` (označen "throwaway — ne commitovati").
   Ostaje samo da se taj jedan poziv pokrene i prijavi.

2. **Vrati zdrav prompt iz backupa** (`rvpr`) — *prva prava izmjena*
   Trenutni prompt je naduven. Zamijenimo ga kratkom, čistom verzijom iz
   `bck/app/system_prompts.py` (samo logika: široka kategorija vs. konkretan
   proizvod), bez viška i bez alata kojih ovdje nema. **Mijenja se samo prompt,
   ništa drugo** — da znamo da je baš prompt zaslužan. Očekujemo povratak na
   ~84-86%, bez novih padova.

3. **Mehanički natjeraj poziv alata** (`frtl`)
   Dodamo poseban alat `respond_to_user` (za slučajeve kad treba samo odgovoriti
   tekstom — npr. pitanje van kataloga) i uključimo postavku koja TJERA model da
   nešto pozove. Time model više ne može da "ćuti i izmišlja": ili pozove pravi
   alat, ili eksplicitno odgovori kroz `respond_to_user`. Upiti van kataloga i
   dalje moraju da prolaze test.

4. **Stezanje** (`tght`)
   Dvije sitne izmjene, svaka mjerena zasebno: spustimo "temperaturu" na ~0
   (manje nasumičnosti, predvidljivije ponašanje) i ograničimo `category_id` na
   listu stvarno postojećih kategorija (model ne može da upiše nepostojeću).

5. **Prihvatanje / kraj** (`acpt`) — *odluka, ne kodiranje*
   Dovedemo rezultat na **≥95%**, ILI svjesno odlučimo da puštamo na ~85% uz
   fallback "nisam siguran, evo opcija" za dvosmislene slučajeve.

## Mali pojmovnik

- **eval** — test od 250 upita; vraća procenat tačnih (PASS).
- **prompt** — uputstvo koje model dobije na startu; definiše kako se ponaša.
- **alat (tool)** — funkcija koju model pozove da dobije prave podatke;
  suprotno od izmišljanja.
- **forsiranje alata (`tool_choice`)** — postavka koja tjera model da pozove
  alat umjesto da sam bira hoće li.
- **baseline** — referentni rezultat s kojim poredimo (84.4%).
- **regresija** — kad nova izmjena pogorša rezultat u odnosu na prije.
- **gate** — pravilo "poslije izmjene pokreni pun test; ako je pao, vrati izmjenu".
