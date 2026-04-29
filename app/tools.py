"""
Definicije alata (Anthropic tool use schema).

Sesija 1: SAMO definicije (JSON schema). Implementacije i dispatcher dolaze u Sesiji 2.
"""
from __future__ import annotations

from typing import Any


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
