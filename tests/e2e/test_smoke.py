"""Smoke test za E2E sloj. Skipuje se ako Playwright nije instaliran.

Default `pytest -q` ne pokreće e2e (addopts isključuje marker). Pokreni
eksplicitno: `pytest -m e2e -q`. Zahtjeva `pip install -e ".[e2e]" && playwright install chromium`.
"""

import pytest

pytestmark = pytest.mark.e2e

pytest.importorskip("playwright.sync_api")


def test_playwright_importable() -> None:
    """Verifikuje da je Playwright dostupan u e2e okruženju."""
    from playwright.sync_api import sync_playwright

    assert sync_playwright is not None
