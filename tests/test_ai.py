import pytest

import sina.ai as ai


class FakeModels:
    def __init__(self, response_text: str | None) -> None:
        self.response_text = response_text
        self.calls: list[tuple[str, str]] = []

    def generate_content(self, *, model: str, contents: str) -> object:
        self.calls.append((model, contents))
        return type("FakeResponse", (), {"text": self.response_text})()


class FakeClient:
    def __init__(self, response_text: str | None) -> None:
        self.models = FakeModels(response_text)


def test_generate_with_ai_sends_prompt_and_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient("generated pytest code")
    monkeypatch.setattr(ai, "_create_client", lambda: client)

    result = ai.generate_with_ai("example prompt")

    assert result == "generated pytest code"
    assert client.models.calls == [
        ("gemini-3.5-flash-lite", "example prompt")
    ]


@pytest.mark.parametrize("response_text", [None, "", "   \n"])
def test_generate_with_ai_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
    response_text: str | None,
) -> None:
    monkeypatch.setattr(ai, "_create_client", lambda: FakeClient(response_text))

    with pytest.raises(RuntimeError, match="Gemini returned an empty response"):
        ai.generate_with_ai("example prompt")


def test_create_client_uses_api_key_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}
    sentinel_client = object()

    def fake_client(*, api_key: str) -> object:
        captured["api_key"] = api_key
        return sentinel_client

    monkeypatch.setattr(ai, "get_gemini_api_key", lambda: "config-test-key")
    monkeypatch.setattr(ai.genai, "Client", fake_client)

    assert ai._create_client() is sentinel_client
    assert captured == {"api_key": "config-test-key"}
