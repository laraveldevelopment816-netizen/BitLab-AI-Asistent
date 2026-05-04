"""
Regression test za voice/text XML tag sanitizaciju (Sesija 8 hotfix).

Production demo otkrio bug: Claude pošalje <voice>...</voice> blok čak
i u chat channel-u (jer prompt instrukcije curiju), ili pošalje samo
<voice> bez <text> wrappera u voice channel-u — u oba slučaja, raw tagovi
i sadržaj <voice> bloka su završavali u UI prikazu chat poruke.

Korisnikov očekivani UX: chat prikazuje paletu proizvoda, voice izgovara
sažetak. Sadržaj <voice> taga ide ISKLJUČIVO u TTS, ne u UI.
"""
from __future__ import annotations

import pytest

from app.agent import _strip_voice_tags, _parse_voice_xml


class TestStripVoiceTags:
    """_strip_voice_tags() je defensive layer u _finalize() — nikad ne smije
    pustiti raw <voice>/<text> tagove u UI bez obzira šta je channel."""

    def test_strips_complete_voice_block(self):
        """Voice blok kompletno uklonjen, ostalo zadržano."""
        inp = "Imam 3 laptopa.\n\n<voice>Imam tri laptopa.</voice>"
        out = _strip_voice_tags(inp)
        assert "<voice>" not in out
        assert "</voice>" not in out
        assert "Imam tri laptopa" not in out
        assert "Imam 3 laptopa." in out

    def test_extracts_text_block_when_present(self):
        """Kad ima <text>, koristi sadržaj (Claude poštuje voice format,
        ali smo u chat channel-u — uzmi text dio)."""
        inp = "<text>Lista proizvoda</text>\n<voice>Sažetak</voice>"
        out = _strip_voice_tags(inp)
        assert out == "Lista proizvoda"
        assert "<voice>" not in out
        assert "Sažetak" not in out

    def test_strips_orphan_open_tag(self):
        """Ostaci nepar tagova (npr. <voice> bez </voice>)."""
        inp = "Tekst\n<voice>"
        out = _strip_voice_tags(inp)
        assert "<voice>" not in out
        assert "Tekst" in out

    def test_strips_orphan_close_tag(self):
        inp = "Tekst</voice>"
        out = _strip_voice_tags(inp)
        assert "</voice>" not in out
        assert "Tekst" in out

    def test_idempotent_on_clean_text(self):
        """Bez tagova → no-op (samo trim)."""
        inp = "Imamo 5 laptopa do 2000 KM."
        assert _strip_voice_tags(inp) == inp

    def test_handles_multiline_voice_block(self):
        """Realan production primjer (Sesija 8 demo)."""
        inp = (
            "Hvala i tebi! 😊 Ako ti zatreba pomoć — javi se.\n\n"
            "<voice>\nHvala tebi! Sretno!\n</voice>"
        )
        out = _strip_voice_tags(inp)
        assert "<voice>" not in out
        assert "</voice>" not in out
        assert "Sretno!" not in out
        assert "Hvala i tebi" in out

    def test_case_insensitive(self):
        """Tagovi su case-insensitive."""
        inp = "Test\n<VOICE>govor</VOICE>"
        out = _strip_voice_tags(inp)
        assert "VOICE" not in out.upper().replace("VOICE", "", 0) or "<VOICE>" not in out
        assert "<voice>" not in out.lower()


class TestParseVoiceXml:
    """_parse_voice_xml() je za voice channel — vraća (reply_text, reply_voice)."""

    def test_both_tags_present(self):
        inp = "<text>Vizuelni</text>\n<voice>Govorni</voice>"
        text, voice = _parse_voice_xml(inp)
        assert text == "Vizuelni"
        assert voice == "Govorni"

    def test_only_voice_no_text_wrapper(self):
        """Bug fix: bez <text>, raw tag ne smije procuriti u reply_text."""
        inp = "Glavni odgovor sa proizvodima.\n<voice>Sažetak.</voice>"
        text, voice = _parse_voice_xml(inp)
        assert "<voice>" not in text
        assert "Sažetak" not in text
        assert "Glavni odgovor sa proizvodima" in text
        assert voice == "Sažetak."

    def test_only_voice_with_no_other_text(self):
        """Edge case: Claude pošalje SAMO <voice> blok."""
        inp = "<voice>Samo govor</voice>"
        text, voice = _parse_voice_xml(inp)
        assert "<voice>" not in text
        assert voice == "Samo govor"
        # Fallback: text dobije isti sadržaj jer drugog nema
        assert text == "Samo govor"

    def test_no_tags_at_all(self):
        """Backwards compat: ako Claude vrati clean tekst, fallback na 2 rečenice."""
        inp = "Imam 3 laptopa. Najjeftiniji je 929 KM. Pogledaj listu."
        text, voice = _parse_voice_xml(inp)
        assert text == inp
        # Voice = prve 2 rečenice
        assert "Imam 3 laptopa" in voice
        assert "Najjeftiniji" in voice
