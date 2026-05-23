"""Smoke test za regression sloj.

Regression set raste sa svakim PASS entry-jem iz eval suite-a — snapshot
ponašanja koje NIKAD ne smije da padne. Placeholder dok prvi eval entry
ne PASS u Fazi 1.
"""

import pytest

pytestmark = pytest.mark.regression


def test_regression_layer_alive() -> None:
    """Sanity — pytest dohvata regression marker i pokreće test."""
    assert True
