"""
Regression test: kad korisnik traži proizvod kojeg nema direktno u katalogu
(npr. gaming desktop PC, custom konfiguracija), agent MORA odgovoriti
toplo i pozvati na custom build kroz BitLab tim — ne suho "nemamo to".

Sesija 8 production demo: korisnik se žalio da je odgovor "previše šturo"
kad je tražio gaming PC. Pravilo 8a u BITLAB_BASE sad zahtjeva tri
elementa u tom odgovoru:
1. Iskrena prepoznavanje da nemamo direktno
2. Poziv na custom build sa BitLab timom
3. Konkretan kontakt + bonus alternative

Ovi testovi koriste pravi Claude API. Mark anthropic_api za skip u CI.
"""
from __future__ import annotations

import pytest

from app.agent import run_agent

pytestmark = pytest.mark.anthropic_api


SCENARIOS = [
    "Trebam gaming desktop PC do 1500 KM, šta imate?",
    "Hoću računar za gejming, ne laptop, do 2000 KM",
    "Imate li desktop sa RTX 4070 i Ryzen 7?",
]


@pytest.mark.parametrize("query", SCENARIOS)
def test_custom_build_response_has_warm_call_to_action(query: str):
    """Reply mora pomenuti custom build / sklapanje konfiguracije, MORA
    sadržati kontakt podatke, NE smije biti samo "nemamo"."""
    result = run_agent([{"role": "user", "content": query}], "chat")
    reply = result["reply"].lower()

    # Anti-pattern: suho "nemamo X" bez drugog sadržaja — minimum 30 riječi
    # garantuje topao odgovor (custom build + kontakt + dalji koraci).
    word_count = len(reply.split())
    assert word_count >= 30, (
        f"Reply prekratak ({word_count} riječi) za upit '{query}': "
        f"očekuje se topao odgovor sa custom build pozivom + kontaktom.\n"
        f"Reply: {result['reply'][:200]}"
    )

    # Custom build keyword — bar jedan od:
    custom_keywords = [
        "sklop", "konfigura", "po želji", "po vaš",
        "custom", "build", "tim će", "tim može", "tim sklopi",
        "izać", "susret",
    ]
    has_custom = any(kw in reply for kw in custom_keywords)
    assert has_custom, (
        f"Reply ne pominje custom build / konfiguraciju za '{query}'.\n"
        f"Očekivane riječi: {custom_keywords}\n"
        f"Reply: {result['reply'][:300]}"
    )

    # Kontakt — telefon ili email
    has_contact = "066 516 174" in reply or "prodaja@bitlab.rs" in reply
    assert has_contact, (
        f"Reply ne sadrži kontakt podatke za '{query}'.\n"
        f"Reply: {result['reply'][:300]}"
    )


def test_short_reply_for_in_stock_product_unaffected():
    """Sanity: za proizvod KOJI imamo, agent NE treba ubaciti custom
    build poziv (to je samo za out-of-catalog scenarije)."""
    result = run_agent(
        [{"role": "user", "content": "Imate li ASUS laptop do 1500 KM?"}],
        "chat",
    )
    reply = result["reply"].lower()
    # Za in-stock upite ne očekujemo poziv na custom konfiguraciju
    # (može pomenuti tim, ali ne smije biti centralna poruka)
    # Ovaj test je labav — verifikuje da reply ima cijene KM što znači
    # da je search vratio rezultat
    assert "km" in reply, f"Očekuje cijene proizvoda, dobio: {result['reply'][:200]}"
