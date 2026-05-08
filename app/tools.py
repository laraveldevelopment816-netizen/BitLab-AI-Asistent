"""
Anthropic tool use schema + handler implementacije.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contacts import EMAIL, TEL


# ── Kategorije + brendovi — load jednom pri import-u ─────────
# AI vidi listu validnih cat_id-ova i brand_id-ova u tool description-u +
# kao enum, tako da single-call zaokruži klasifikaciju + tool decision atomski.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CATEGORIES_PATH = _DATA_DIR / "categories.json"
_BRAND_PATH = _DATA_DIR / "brend.json"


def _load_categories() -> dict[str, dict[str, Any]]:
    if not _CATEGORIES_PATH.exists():
        return {}
    return json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))


def _load_brands() -> list[dict[str, Any]]:
    """phpMyAdmin export → lista {id, name, priority}. Sortirano po priority
    (1–20), pa po imenu. Brendovi sa priority idu na vrh tool description-a
    da AI brže nađe najtraženije."""
    if not _BRAND_PATH.exists():
        return []
    raw = json.loads(_BRAND_PATH.read_text(encoding="utf-8"))
    for entry in raw:
        if entry.get("type") == "table" and entry.get("name") == "brend":
            data = entry.get("data", [])
            out: list[dict[str, Any]] = []
            for row in data:
                bid = (row.get("id") or "").strip()
                name = (row.get("name") or "").strip()
                if not bid or not name or name.lower() == "ostalo":
                    continue
                pri_raw = row.get("priority")
                priority = int(pri_raw) if pri_raw and pri_raw != "NULL" else 999
                out.append({"id": bid, "name": name, "priority": priority})
            out.sort(key=lambda b: (b["priority"], b["name"]))
            return out
    return []


CATEGORIES: dict[str, dict[str, Any]] = _load_categories()
_CATEGORY_IDS: list[str] = list(CATEGORIES.keys())
_CATEGORIES_BLOCK = "\n".join(
    f"- {cid}: {info['label']}" for cid, info in CATEGORIES.items()
)

BRANDS: list[dict[str, Any]] = _load_brands()
_BRAND_IDS: list[str] = [b["id"] for b in BRANDS]
_BRANDS_BLOCK = "\n".join(
    f"- {b['id']}: {b['name']}" for b in BRANDS
)


SEARCH_PRODUCTS: dict[str, Any] = {
    "name": "search_products",
    "description": (
        "Pretraži BitLab katalog (5.287 proizvoda) hibridnom pretragom (semantička + "
        "leksička). Koristi za sva pitanja o tome šta firma prodaje, koliko košta, "
        "šta ima na zalihi, uporedbe, ili 'imate li X'. Vraća listu proizvoda sa "
        "imenom, cijenom u KM, oznakom dostupnosti i URL-om. NE koristi za politike "
        "(dostava, plaćanje, garancija) — za to koristi `get_faq`.\n\n"
        "VALIDNE KATEGORIJE (popuni `category_id` kad je upit kategorijski):\n"
        f"{_CATEGORIES_BLOCK}\n\n"
        "VALIDNI BRENDOVI (popuni `brand_id` kad korisnik imenuje brend):\n"
        f"{_BRANDS_BLOCK}\n\n"
        "Pravila klasifikacije:\n"
        "1. **Kategorijski upit** ('tastatura', 'laptop do 1500 KM', 'monitor 27\"', "
        "'gaming miš') — popuni `category_id`. Filter odsijeca accessory šum (npr. "
        "torbe za laptop kad korisnik traži laptop).\n"
        "2. **Brand-only upit** ('Apple', 'Asus', 'Xiaomi') — popuni `brand_id` ali "
        "pusti `category_id` prazan (brendovi pokrivaju više kategorija).\n"
        "3. **Brand + kategorija** ('Apple iPhone', 'Asus laptop', 'Samsung TV', "
        "'Logitech miš') — popuni OBA: `category_id` + `brand_id`. Najtačniji rezultat.\n"
        "4. **Brand + model** ('iPhone 15 Pro', 'Patriot SSD 240GB') — možeš dati "
        "samo `brand_id` ili oba; `query` sa modelom najviše utiče."
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
            "category_id": {
                "type": "string",
                "enum": _CATEGORY_IDS,
                "description": (
                    "Opciono: ID kategorije iz liste validnih kategorija (vidi opis "
                    "tool-a). Filtrira pretragu samo na proizvode iz te kategorije."
                ),
            },
            "brand_id": {
                "type": "string",
                "enum": _BRAND_IDS,
                "description": (
                    "Opciono: ID brenda iz liste validnih brendova (vidi opis tool-a). "
                    "Filtrira pretragu samo na proizvode tog brenda. Kombinuje se sa "
                    "category_id za pretragu poput 'Apple iPhone' (cat=mobiteli, "
                    "brand=APPLE). Ne popuni za 'Ostalo' brendove ili kad korisnik ne "
                    "imenuje brend eksplicitno."
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
    category_id: str | None = None,
    brand_id: str | None = None,
) -> str:
    results = _get_index().search(
        query,
        top_k=top_k,
        max_price_km=max_price_km,
        category_id=category_id,
        brand_id=brand_id,
    )
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
    """Eskalacija u dashboard log + opciono stvarni email notifikacija.

    Bug fix Sesija 8: ranije je tool vraćao "Prodajni tim je obaviješten"
    iako ništa stvarno nije slano — laž koju je AI ponavljao korisniku.
    Sad: ako je ESCALATION_EMAIL_TO + SMTP konfigurisan u .env, šaljemo
    pravi email; inače honest tekst "vaš upit je zabilježen, kontaktirajte
    tim direktno za brz odgovor"."""
    from .config import settings

    notified = False
    notify_target = getattr(settings, "escalation_email_to", None) or settings.smtp_user
    if notify_target and settings.smtp_host and settings.smtp_user and settings.smtp_password:
        try:
            import smtplib
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["From"] = settings.smtp_user
            msg["To"] = notify_target
            msg["Subject"] = f"[BitLab AI] Eskalacija: {reason}"
            msg.set_content(
                f"Razlog: {reason}\n\n"
                f"Sažetak korisnikovog upita:\n{summary}\n\n"
                f"-- automatski iz BitLab AI Asistenta"
            )
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            notified = True
        except Exception as exc:
            print(f"[ESCALATE] Email send failed: {exc!r}")
            # Ne padaj — tool i dalje treba da vrati instrukcije korisniku

    if notified:
        notify_status = "Prodajni tim je obaviješten putem emaila — javit će se u toku radnog vremena."
    else:
        # Honest fallback: NE tvrdi obavještenje koje nije poslano
        notify_status = (
            "Vaš upit je zabilježen u sistemu. Za brz odgovor kontaktirajte tim DIREKTNO "
            "(email notifikacija nije poslata)."
        )

    return (
        f"Eskalacija inicirana — razlog: {reason}\n"
        f"Sažetak: {summary}\n\n"
        "Kontakti za korisnika:\n"
        f"• Viber / Tel: {TEL}\n"
        f"• Email: {EMAIL}\n"
        f"{notify_status}"
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
