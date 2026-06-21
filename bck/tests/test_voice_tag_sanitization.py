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


from app.agent import (
    _strip_voice_tags, _parse_voice_xml,
    _strip_horizontal_rules, _strip_markdown_tables,
)


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


class TestStripHorizontalRules:
    """_strip_horizontal_rules() uklanja standalone --- footer/separator
    koji Sonnet voli da doda iako prompt zabranjuje."""

    def test_strips_hr_separator_between_products(self):
        inp = (
            "Evo 3 laptopa:\n\n"
            "1. **ASUS** — 929 KM\n"
            "2. **Lenovo** — 1.315 KM\n\n"
            "---\n\n"
            "Trebaš pomoć?"
        )
        out = _strip_horizontal_rules(inp)
        assert "---" not in out
        assert "ASUS" in out
        assert "Trebaš pomoć?" in out

    def test_strips_multiple_hr_styles(self):
        for hr in ["---", "***", "___", "----", "*****", "________"]:
            inp = f"Tekst\n\n{hr}\n\nDrugi"
            out = _strip_horizontal_rules(inp)
            assert hr not in out, f"HR '{hr}' nije uklonjen"

    def test_collapses_multiple_blank_lines(self):
        inp = "Tekst\n\n\n\n\nDrugi"
        out = _strip_horizontal_rules(inp)
        # Max 2 blank line-a (jedan paragraf separator)
        assert "\n\n\n" not in out
        assert "Tekst" in out and "Drugi" in out

    def test_does_not_strip_inline_dashes(self):
        """`---` u sredini reda (npr. em-dash u tekstu) ne smije biti diran."""
        inp = "Cijena — vrlo dobra. Lenovo --- najbolji izbor."
        out = _strip_horizontal_rules(inp)
        # Inline `---` ostaje (nije na vlastitom redu)
        assert "Lenovo --- najbolji" in out

    def test_idempotent_on_clean_text(self):
        inp = "Imam 5 laptopa do 2000 KM."
        assert _strip_horizontal_rules(inp) == inp

    def test_handles_empty_input(self):
        assert _strip_horizontal_rules("") == ""
        assert _strip_horizontal_rules("\n\n\n") == ""


class TestStripMarkdownTables:
    """_strip_markdown_tables() uklanja markdown tabele jer frontend
    renderer ih ne podržava i TTS čita pipe + crtice."""

    def test_strips_table_with_separator(self):
        inp = (
            "Evo laptopa:\n\n"
            "| # | Laptop | Cijena |\n"
            "|---|--------|--------|\n"
            "| 1 | ASUS   | 929 KM |\n"
            "| 2 | Lenovo | 1.315  |\n\n"
            "Treba li dodatne info?"
        )
        out = _strip_markdown_tables(inp)
        assert "|" not in out, f"Pipe ostala u outputu: {out!r}"
        assert "Evo laptopa" in out
        assert "Treba li dodatne info" in out

    def test_keeps_inline_pipe_in_text(self):
        """Pipe usred plain teksta (nije table line) ne treba dirati."""
        inp = "Možeš birati: A | B | C — koju opciju?"
        out = _strip_markdown_tables(inp)
        assert out == inp.strip()

    def test_idempotent(self):
        inp = "Imam 5 laptopa. Sve na lageru."
        assert _strip_markdown_tables(inp) == inp.strip()

    def test_handles_table_only_input(self):
        inp = "| a | b |\n|---|---|\n| 1 | 2 |"
        out = _strip_markdown_tables(inp)
        assert out == ""
