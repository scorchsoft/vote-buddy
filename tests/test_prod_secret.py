import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import importlib
import config
import app


def test_secret_key_required_in_production(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'change-me')
    importlib.reload(config)
    importlib.reload(app)
    with pytest.raises(RuntimeError):
        app.create_app()
