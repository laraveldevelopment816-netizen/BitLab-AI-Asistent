"""
Anthropic tool use schema + handler implementacije.
"""
from __future__ import annotations

import json
from typing import Any

from .contacts import EMAIL, TEL


SEARCH_PRODUCTS: dict[str, Any] = {
    "name": "search_products",
    "description": (
        "Pretraži BitLab katalog (5.287 proizvoda) hibridnom pretragom (semantička + "
        "leksička). Koristi za sva pitanja o tome šta firma prodaje, koliko košta, "
        "šta ima na zalihi, uporedbe, ili 'imate li X'. Vraća listu proizvoda sa "
        "imenom, cijenom u KM, oznakom dostupnosti i URL-om. NE koristi za politike "
        "(dostava, plaćanje, garancija) — za to koristi `get_faq`."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Korisnikov upit. Može biti prirodni jezik ('brz disk za laptop'), "
                    "brand+model ('Patriot SSD 240GB'), ili kategorija ('SSD diskovi 1TB')."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "Koliko proizvoda da vrati (1–10).",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
            "max_price_km": {
                "type": "number",
                "description": "Opciono: gornja granica cijene u KM. Filtrira rezultate.",
            },
        },
        "required": ["query"],
    },
}


GET_FAQ: dict[str, Any] = {
    "name": "get_faq",
    "description": (
        "Pretraži BitLab FAQ za informacije o politikama firme: dostava, plaćanje, "
        "garancija, B2B procedura, kontakt, radno vrijeme, povraćaj robe, JIB/PIB, "
        "reklamacije, MKD Partner (rate). Koristi za sva pitanja koja NISU o "
        "konkretnim proizvodima."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": (
                    "Tema upita na BCS jeziku — npr. 'dostava u Sarajevo', "
                    "'plaćanje na rate', 'garancija servis', 'B2B faktura JIB'."
                ),
            }
        },
        "required": ["topic"],
    },
}


CHECK_AVAILABILITY: dict[str, Any] = {
    "name": "check_availability",
    "description": (
        "Provjeri trenutnu dostupnost konkretnog proizvoda po šifri (sifra). Koristi "
        "nakon `search_products` kad korisnik pita 'imate li ovo na zalihi' za "
        "specifičan proizvod iz prethodnih rezultata."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sifra": {
                "type": "string",
                "description": "Šifra proizvoda iz prethodnog `search_products` poziva.",
            }
        },
        "required": ["sifra"],
    },
}


ESCALATE_TO_HUMAN: dict[str, Any] = {
    "name": "escalate_to_human",
    "description": (
        "Pozovi kad upit prevazilazi mogućnosti AI-ja: B2B ponude sa JIB-om, "
        "individualni popusti, reklamacije, neispravni proizvodi, kompleksne "
        "pregovore, ili kad si dva puta u nizu pokušao i nisi pomogao. Ovaj poziv "
        "obavještava prodajni tim i vraća korisniku Viber/email kontakt."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": [
                    "b2b_ponuda",
                    "reklamacija",
                    "individualna_cijena",
                    "tehnicki_savjet",
                    "ostalo",
                ],
                "description": "Kategorija razloga za eskalaciju.",
            },
            "summary": {
                "type": "string",
                "description": (
                    "Sažetak razgovora i šta tačno korisnik traži (1–3 rečenice). "
                    "Prodajni tim koristi ovo da brzo odgovori."
                ),
            },
        },
        "required": ["reason", "summary"],
    },
}


ALL_TOOLS: list[dict[str, Any]] = [
    SEARCH_PRODUCTS,
    GET_FAQ,
    CHECK_AVAILABILITY,
    ESCALATE_TO_HUMAN,
]


TOOL_NAMES: list[str] = [t["name"] for t in ALL_TOOLS]


# ── Lazy loaders ─────────────────────────────────────────────

def _get_index():
    from .rag import get_index
    return get_index()


_faq_sections = None

def _get_faq():
    global _faq_sections
    if _faq_sections is None:
        from .faq import load_faq
        from .config import settings
        _faq_sections = load_faq(settings.faq_path)
    return _faq_sections


# ── Handleri ─────────────────────────────────────────────────

def handle_search_products(
    query: str,
    top_k: int = 5,
    max_price_km: float | None = None,
) -> str:
    results = _get_index().search(query, top_k=top_k, max_price_km=max_price_km)
    if not results:
        return "Nema proizvoda koji odgovaraju upitu."
    return json.dumps(results, ensure_ascii=False)


def handle_get_faq(topic: str) -> str:
    from .faq import search_faq
    sections = search_faq(_get_faq(), topic, top_k=3)
    if not sections:
        return "Nije pronađena relevantna FAQ sekcija za temu."
    parts = []
    for s in sections:
        parts.append(f"## {s.title}\n{s.content}")
    return "\n\n---\n\n".join(parts)


def handle_check_availability(sifra: str) -> str:
    meta = _get_index().sifra_map.get(sifra.strip())
    if not meta:
        return f"Proizvod sa šifrom '{sifra}' nije pronađen u katalogu."
    return (
        f"Naziv: {meta['name']}\n"
        f"Šifra: {meta['sifra']}\n"
        f"Cijena: {meta['price_km']} KM\n"
        f"Dostupnost: {meta['availability_label']}\n"
        f"URL: {meta.get('url', 'N/A')}"
    )


def handle_escalate_to_human(reason: str, summary: str) -> str:
    return (
        f"Eskalacija inicirana — razlog: {reason}\n"
        f"Sažetak: {summary}\n\n"
        "Kontakti za korisnika:\n"
        f"• Viber / Tel: {TEL}\n"
        f"• Email: {EMAIL}\n"
        "Prodajni tim je obaviješten i javit će se u toku radnog vremena."
    )


_HANDLERS = {
    "search_products": lambda inp: handle_search_products(**inp),
    "get_faq": lambda inp: handle_get_faq(**inp),
    "check_availability": lambda inp: handle_check_availability(**inp),
    "escalate_to_human": lambda inp: handle_escalate_to_human(**inp),
}


def dispatch(name: str, tool_input: dict[str, Any]) -> str:
    handler = _HANDLERS.get(name)
    if not handler:
        return f"Nepoznat alat: {name}"
    try:
        return handler(tool_input)
    except Exception as exc:
        # Loguj puni traceback u server konzolu da možemo dijagnozirati root cause
        import traceback
        print(f"[TOOL ERROR] {name}({tool_input!r}) → {type(exc).__name__}: {exc}")
        traceback.print_exc()
        # Vrati neutralnu poruku Claude-u — ne "tehnička greška u bazi" jer to
        # tjera Claude-a da paniči i odbija korisnika. Umjesto toga, daj mu
        # info da pokuša ponovo ili predloži alternative.
        if name == "search_products":
            return ("Pretraga trenutno vraća prazan rezultat za ovaj upit. "
                    "Predloži korisniku da preformuliše upit (npr. konkretniji brand, "
                    "specifikacije, cjenovni opseg) ili da pita o nekoj drugoj kategoriji.")
        if name == "get_faq":
            return ("FAQ pretraga nije pronašla relevantnu sekciju. "
                    "Odgovori iz opšteg znanja o BitLab politikama ili predloži kontakt "
                    "prodajnom timu.")
        return f"Alat '{name}' privremeno nedostupan. Pokušaj alternativni pristup."
