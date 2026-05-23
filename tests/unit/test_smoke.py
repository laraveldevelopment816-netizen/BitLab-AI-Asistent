"""Smoke test — unit sloj radi, markers funkcionišu, app paket importable."""

import pytest

pytestmark = pytest.mark.unit


def test_python_arithmetic_basic() -> None:
    assert 2 + 2 == 4


def test_app_module_importable() -> None:
    """Sanity check: app paket se može importovati bez side effects."""
    import app
    import app.agent
    import app.config
    import app.main

    assert app is not None
    assert hasattr(app.agent, "run_agent")
    assert hasattr(app.config, "settings")
    assert hasattr(app.main, "app")
