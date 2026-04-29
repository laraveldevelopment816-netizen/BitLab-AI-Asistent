"""
DEMO 1 — AI AGENT (AI Forward Dan 4)
Pokazuje razliku između CHATBOT-a (samo odgovara) i AGENTA (djeluje).

Agent ima 3 alata:
1. provjeri_zalihe(proizvod) - simulira bazu zaliha
2. izracunaj_dostavu(grad, kg) - simulira kalkulator dostave
3. zakazi_termin(klijent, datum) - simulira CRM

Pokretanje: python demo_agent.py
Predavač uživo testira sa pitanjima.
"""
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# === SIMULIRANI PODACI (umjesto prave baze) ===
ZALIHE = {
    "Alba ormar": 12,
    "Royal sto": 5,
    "Royal stolica": 24,
    "Minimal radni sto": 8,
    "Alba krevet": 0,
}

CIJENE_DOSTAVE = {
    "Banja Luka": 0,
    "Sarajevo": 200,
    "Mostar": 250,
    "Zagreb": 350,
    "Beograd": 300,
}

TERMINI = []

# === TOOL FUNKCIJE — ŠTO AGENT MOŽE STVARNO DA URADI ===

def provjeri_zalihe(proizvod: str) -> str:
    """Provjerava trenutne zalihe za dati proizvod."""
    if proizvod in ZALIHE:
        kolicina = ZALIHE[proizvod]
        if kolicina == 0:
            return f"❌ Nema zaliha: {proizvod} (0 komada)"
        return f"✓ Zalihe za '{proizvod}': {kolicina} komada"
    return f"⚠ Proizvod '{proizvod}' nije u našoj bazi."


def izracunaj_dostavu(grad: str, kilogrami: float) -> str:
    """Računa cijenu dostave za grad i težinu."""
    if grad not in CIJENE_DOSTAVE:
        return f"⚠ Ne dostavljamo za grad '{grad}'. Dostupni: {', '.join(CIJENE_DOSTAVE.keys())}"
    osnovna = CIJENE_DOSTAVE[grad]
    if kilogrami > 50:
        osnovna += 100  # dodatak za teški namještaj
    return f"✓ Dostava do {grad} ({kilogrami}kg): {osnovna} KM"


def zakazi_termin(klijent: str, datum: str) -> str:
    """Zakazuje termin u CRM."""
    termin = {"klijent": klijent, "datum": datum}
    TERMINI.append(termin)
    return f"✓ Termin zakazan: {klijent} dana {datum}. Ukupno aktivnih termina: {len(TERMINI)}"


# Težine proizvoda (za info Claude-u kroz description)
TEZINE = {
    "Alba ormar": 80,
    "Royal sto": 60,
    "Royal stolica": 8,
    "Minimal radni sto": 35,
    "Alba krevet": 70,
}


# === DEFINICIJE ALATA ZA CLAUDE (TOOL USE FORMAT) ===

TOOLS = [
    {
        "name": "provjeri_zalihe",
        "description": "Provjerava trenutne zalihe za dati proizvod u skladištu.",
        "input_schema": {
            "type": "object",
            "properties": {
                "proizvod": {
                    "type": "string",
                    "description": "Tačan naziv proizvoda (npr. 'Alba ormar')"
                }
            },
            "required": ["proizvod"]
        }
    },
    {
        "name": "izracunaj_dostavu",
        "description": "Računa cijenu dostave za dati grad i ukupnu težinu narudžbe u kilogramima. Težine: Alba ormar=80kg, Royal sto=60kg, Royal stolica=8kg, Minimal radni sto=35kg, Alba krevet=70kg.",
        "input_schema": {
            "type": "object",
            "properties": {
                "grad": {
                    "type": "string",
                    "description": "Grad dostave (npr. 'Sarajevo')"
                },
                "kilogrami": {
                    "type": "number",
                    "description": "Ukupna težina u kg (saberite težine svih proizvoda × količina)"
                }
            },
            "required": ["grad", "kilogrami"]
        }
    },
    {
        "name": "zakazi_termin",
        "description": "Zakazuje termin sa klijentom u CRM sistem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "klijent": {
                    "type": "string",
                    "description": "Ime klijenta"
                },
                "datum": {
                    "type": "string",
                    "description": "Datum termina (npr. '2026-05-03 14:00')"
                }
            },
            "required": ["klijent", "datum"]
        }
    }
]


def izvrsi_alat(ime_alata: str, ulazi: dict) -> str:
    """Mapiranje imena alata na stvarnu Python funkciju."""
    if ime_alata == "provjeri_zalihe":
        return provjeri_zalihe(ulazi["proizvod"])
    elif ime_alata == "izracunaj_dostavu":
        return izracunaj_dostavu(ulazi["grad"], ulazi["kilogrami"])
    elif ime_alata == "zakazi_termin":
        return zakazi_termin(ulazi["klijent"], ulazi["datum"])
    return f"❌ Nepoznati alat: {ime_alata}"


SYSTEM_PROMPT = """Ti si AI agent firme GMP Kompani iz Banja Luke.
Imaš 3 alata: provjeri_zalihe, izracunaj_dostavu, zakazi_termin.

Dostupni proizvodi u bazi: Alba ormar, Royal sto, Royal stolica, Minimal radni sto, Alba krevet.
Dostupni gradovi za dostavu: Banja Luka, Sarajevo, Mostar, Zagreb, Beograd.

Pravila:
1. Kad korisnik pita za zalihe, dostavu ili zakazivanje - KORISTI alat, ne odgovaraj iz glave.
2. Kod provjeri_zalihe: pošalji SAMO naziv proizvoda iz baze (npr. "Alba ormar"), bez količine ("2 Alba ormara" je POGREŠNO).
3. Možeš koristiti više alata u nizu da odgovoriš na složeno pitanje.
4. Ako alat vraća rezultat, koristi ga u odgovoru.
5. Odgovaraj na BCS jeziku, kratko i profesionalno."""


def agent_korak(razgovor: list) -> list:
    """Jedan korak agenta: pošalji Claude-u, dobij odgovor, izvrši alate ako treba."""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=razgovor
    )

    # Dodaj Claude odgovor u razgovor
    razgovor.append({"role": "assistant", "content": response.content})

    # Ako Claude želi da koristi alate
    if response.stop_reason == "tool_use":
        rezultati_alata = []
        for blok in response.content:
            if blok.type == "tool_use":
                print(f"   🔧 Agent zove: {blok.name}({json.dumps(blok.input, ensure_ascii=False)})")
                rezultat = izvrsi_alat(blok.name, blok.input)
                print(f"   ↩  Rezultat: {rezultat}")
                rezultati_alata.append({
                    "type": "tool_result",
                    "tool_use_id": blok.id,
                    "content": rezultat
                })

        # Vrati rezultate alata Claude-u da napiše finalni odgovor
        razgovor.append({"role": "user", "content": rezultati_alata})
        return agent_korak(razgovor)  # rekurzivno - možda treba još alata

    return razgovor


def chat(pitanje: str):
    """Pokreni agent za jedno pitanje."""
    print(f"\n{'='*60}")
    print(f"👤 KORISNIK: {pitanje}")
    print(f"{'='*60}")

    razgovor = [{"role": "user", "content": pitanje}]
    razgovor = agent_korak(razgovor)

    # Posljednji Claude odgovor (tekst)
    posljednji = razgovor[-1]["content"]
    if isinstance(posljednji, list):
        for blok in posljednji:
            if hasattr(blok, "type") and blok.type == "text":
                print(f"\n🤖 AGENT: {blok.text}\n")
    else:
        print(f"\n🤖 AGENT: {posljednji}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("AI AGENT DEMO — GMP Kompani")
    print("=" * 60)
    print("\nAgent ima 3 alata:")
    print("  1. provjeri_zalihe(proizvod)")
    print("  2. izracunaj_dostavu(grad, kg)")
    print("  3. zakazi_termin(klijent, datum)")

    # === DEMO PITANJA — koje predavač pokazuje ===

    # PITANJE 1: Jednostavno - jedan alat
    chat("Imamo li Alba ormar na zalihi?")

    # PITANJE 2: Više alata - kombinacija
    chat("Klijent iz Sarajeva želi 2 Alba ormara. Koliko je dostava? Imaju li oni na zalihi?")

    # PITANJE 3: Akcija - mijenja stanje
    chat("Zakaži mi termin sa klijentom Marko Petrović za 2026-05-03 u 14h.")

    # PITANJE 4: Test halucinacije - alat NEMA odgovor
    chat("Koja je cijena dostave do Pariza?")

    print("\n" + "=" * 60)
    print(f"DEMO ZAVRŠEN. Aktivni termini: {len(TERMINI)}")
    print("=" * 60)
