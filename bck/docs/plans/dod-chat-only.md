# DoD — BitLab AI Asistent (Chat-only faza)

## Cilj

Ovaj dokument definiše šta znači "gotovo" za chat-only deploy BitLab AI
Asistenta. Voice i email kanali nisu u opsegu ove faze i posmatraju se kao
kasnije proširenje.

## 1. Isključivanje voice modula iz aplikacije

U chat-only deploy-u, voice komponente (TTS, STT, voice status endpoint)
ne treba da se učitavaju pri startu aplikacije. Voice import-i i pripadajuće
rute se komentarišu tako da runtime ne nosi voice dependency-je, ne pokušava
Whisper inicijalizaciju i ne otvara TTS konekcije.

Voice kod ostaje u repozitorijumu, ali fizički ne učestvuje u aktivnom
servisu. Reaktivacija voice modula se planira kao zaseban korak u kasnijoj
fazi projekta.

## 2. Strukturisani izlaz iz AI pretrage

AI tok koji vraća rezultate pretrage trenutno ne garantuje konzistentan
oblik podataka. Rezultati istog tipa upita mogu doći u različitim
strukturama, što stvara prostor za bug-ove u prikazu i otežava održavanje
widget-a.

Uspostavlja se trostepena arhitektura koja garantuje predvidljiv izlaz:

**JSON shema** — formalna definicija oblika "search result" objekta.
Specificira polja, tipove, obavezna i opcionalna polja. Funkcioniše kao
ugovor između AI sloja i UI sloja.

**Pydantic validator** — runtime provjera da AI output prolazi shemu. Ako
output ne prolazi, sistem fail-fast-uje sa jasnom dijagnostikom umjesto da
neispravne podatke prosljeđuje dalje u widget.

**Layout** — komponenta widget-a koja konzumira validan output i prikazuje
ga konzistentno. Pošto je ulaz garantovan u poznatom obliku, layout je
deterministički, bez defanzivnih grananja za odsutna ili neočekivana polja.

Tri sloja zajedno eliminišu klasu bug-ova vezanih za inkonzistentne AI
odgovore.

## 3. Hijerarhijske kategorije (parent_id)

Webshop-ova taksonomija ima hijerarhijsku strukturu kroz `parent_id` polje
u `categories.csv` — kategorije imaju parent-child odnose. Trenutna
implementacija pretrage tretira kategorije kao ravnu listu i ne koristi
ovu strukturu.

Cilj je da AI pretraga razumije i koristi hijerarhijsku strukturu pri
klasifikaciji upita i ranking-u rezultata.

## 4. PlaywrightRouter kao test infrastruktura

PlaywrightRouter je interni servis sa OpenAI-kompatibilnim SDK interfejsom
koji ruta pozive ka DeepSeek i Claude nalozima (plaćeni i besplatni
tier-ovi). Postoji kao infrastruktura prije ove faze.

Cilj je iskoristiti PlaywrightRouter kao test backend, tako da
automatizovani testovi mogu da idu kroz dostupne provider-e i tier-ove
prema potrebi, umjesto da se test coverage oslanja isključivo na
produkciono skupe pozive.

## 5. Sistematsko pokrivanje edge case-ova

Aplikacija mora dokazano podnositi i ivične scenarije, ne samo standardne
"happy path" tokove. Uvodi se eksplicitan test set za niže navedene
slučajeve.

### Funkcionalni testovi

**Pretraga ponude (RAG):** testovi koji provjeravaju da AI ispravno
pretražuje katalog proizvoda za različite tipove upita — po brendu,
kategoriji, atributu, ili kombinaciji.

**Pretraga baze znanja (FAQ):** testovi koji provjeravaju da AI nalazi
relevantne odgovore u FAQ-u za pitanja koja se ne odnose na konkretne
proizvode — uslovi poslovanja, garancija, dostava i slično.

**Prompt injection (safety instructions):** testovi koji provjeravaju
otpornost sistema na pokušaje manipulacije instrukcijama — da ne otkriva
system prompt, ne mijenja personu, ne izvršava instrukcije skrivene
unutar sadržaja proizvoda ili FAQ-a.

### Edge case ponašanja

**Kada provider nema kredita:** kad upstream LLM provider odbija zahtjev
jer je kvota potrošena, sistem mora vratiti razumljivu poruku korisniku
umjesto tehničke greške ili stack trace-a.

**Prazni rezultati pretrage:** kad AI ispravno klasifikuje upit ali
katalog ne sadrži proizvode koji odgovaraju, korisnik dobija smislen
odgovor — prijedlog alternative, eskalaciju, ili jasnu negativnu potvrdu
— umjesto praznog odgovora ili izmišljenih proizvoda.

**Nema informacija u bazi znanja:** kad pitanje izlazi izvan obuhvata
kataloga i FAQ-a, sistem prepoznaje granicu svog znanja i eskalira na
čovjeka umjesto da izmišlja odgovor.
