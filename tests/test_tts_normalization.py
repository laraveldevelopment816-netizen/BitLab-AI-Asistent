"""
Regression test za TTS normalizaciju cijena (Sesija 8 hotfix).

Production demo otkrio bug: "1.936 KM" → TTS čita "jedna marka" umjesto
"hiljadu devetsto trideset šest maraka". Razlog: u BCS formatu tačka je
separator hiljada (1.936 = hiljadu devetsto trideset šest), ali stari
kod ju je tretirao kao decimalnu (int(float("1.936")) = 1).
"""
from __future__ import annotations

import pytest

from app.main import _normalize_for_tts


@pytest.mark.parametrize("price_in,expected_substr", [
    # Tačka kao separator hiljada (Sesija 8 fix)
    ("1.936 KM",    "hiljadu devetsto trideset"),
    ("1.315 KM",    "hiljadu trista petnaest"),
    ("1.799 KM",    "hiljadu sedamsto devedeset"),
    ("1.849 KM",    "hiljadu osamsto"),
    ("2.500 KM",    "dvije hiljade petsto"),
    # Već radilo prije fix-a
    ("929 KM",      "devetsto dvadeset devet maraka"),
    ("500 KM",      "petsto maraka"),
    # Zarez kao decimalni separator (BCS standard)
    ("389,99 KM",   "trista osamdeset devet maraka"),
    ("1.450,00 KM", "hiljadu četiristo pedeset maraka"),
    # Singular
    ("1 KM",        "jedan marka"),
])
def test_price_normalization(price_in: str, expected_substr: str):
    """Cijena u rasponu od stotina do hiljada mora se ispravno izgovoriti."""
    out = _normalize_for_tts(price_in)
    assert expected_substr.lower() in out.lower(), (
        f"Loš TTS output za '{price_in}': dobio {out!r}, "
        f"očekivao da sadrži '{expected_substr}'"
    )
    # Eksplicitno: nikad ne smije biti "jedna marka" / "1 marka" za
    # višestotinaštinu (osnovna provjera regression-a)
    if "1." in price_in or any(c.isdigit() for c in price_in.split()[0][1:]):
        if int(price_in.split()[0].replace(".", "").replace(",", "")[:1]) > 1 or len(price_in.split()[0]) > 1:
            assert "jedna marka" not in out, (
                f"REGRESSION: '{price_in}' → '{out}' sadrži 'jedna marka'"
            )


def test_unit_normalization_unchanged():
    """RAM/storage/freq jedinice ne smiju regresovati."""
    assert "gigabajta" in _normalize_for_tts("16GB").lower()
    assert "terabajta" in _normalize_for_tts("1TB").lower()
    assert "gigaherca" in _normalize_for_tts("3.5GHz").lower()
