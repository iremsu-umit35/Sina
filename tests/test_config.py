from pathlib import Path

import pytest
from dotenv import load_dotenv as load_test_dotenv

import sina.config as config


@pytest.fixture(autouse=True)
def isolate_project_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: False)


def test_get_gemini_api_key_returns_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    assert config.get_gemini_api_key() == "test-key"


def test_get_gemini_api_key_raises_when_environment_value_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        config.get_gemini_api_key()


def test_get_gemini_api_key_loads_value_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("GEMINI_API_KEY=dotenv-test-key\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        config,
        "load_dotenv",
        lambda: load_test_dotenv(dotenv_path=dotenv_path),
    )

    assert config.get_gemini_api_key() == "dotenv-test-key"


def test_environment_value_takes_precedence_over_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("GEMINI_API_KEY=dotenv-test-key\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "environment-test-key")
    monkeypatch.setattr(
        config,
        "load_dotenv",
        lambda: load_test_dotenv(dotenv_path=dotenv_path),
    )

    assert config.get_gemini_api_key() == "environment-test-key"
