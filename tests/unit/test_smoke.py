"""Smoke test — unit sloj radi, markers funkcionišu, app paket importable."""

import pytest

pytestmark = pytest.mark.unit


def test_python_arithmetic_basic() -> None:
    assert 2 + 2 == 4


def test_app_module_importable() -> None:
    """Sanity check: app paket importable bez side effects.

    Verifikuje da agent ima OBA backend runnera + dispatch helper-i
    (memorija llm_backend_pwr_imperative)."""
    import app
    import app.agent
    import app.config
    import app.main

    assert app is not None
    assert hasattr(app.agent, "run_agent")
    assert hasattr(app.agent, "_run_anthropic")
    assert hasattr(app.agent, "_run_pwr")
    assert hasattr(app.agent, "_use_pwr")
    assert hasattr(app.config, "settings")
    assert hasattr(app.config.settings, "llm_backend")
    assert hasattr(app.config.settings, "pwr_api_key")
    assert hasattr(app.main, "app")
