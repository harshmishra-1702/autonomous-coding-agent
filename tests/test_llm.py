import httpx, pytest
from types import SimpleNamespace as NS
from groq import RateLimitError
import agent.llm as llm

def rate_limit():
    resp = httpx.Response(429, request=httpx.Request("POST", "http://x"))
    return RateLimitError("limited", response=resp, body=None)

class Fake:
    """Plays a script: each call either raises an exception or returns a message."""
    def __init__(self, script):
        self.script, self.calls = script, 0
        self.chat = NS(completions=NS(create=self._create))
    def _create(self, **kw):
        step = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(step, Exception):
            raise step
        return NS(choices=[NS(message=step)])

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)

def test_groq_ok_never_touches_fallback(monkeypatch):
    groq, google = Fake(["groq-msg"]), Fake(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    assert llm.chat_with_tools([], []) == "groq-msg"
    assert google.calls == 0

def test_recovers_after_one_rate_limit(monkeypatch):
    groq, google = Fake([rate_limit(), "groq-msg"]), Fake(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    assert llm.chat_with_tools([], []) == "groq-msg"
    assert groq.calls == 2 and google.calls == 0

def test_falls_back_after_retries_exhausted(monkeypatch):
    groq, google = Fake([rate_limit()]), Fake(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    assert llm.chat_with_tools([], []) == "google-msg"
    assert groq.calls == 3 and google.calls == 1

def test_raises_when_no_fallback_configured(monkeypatch):
    monkeypatch.setattr(llm, "client", Fake([rate_limit()]))
    monkeypatch.setattr(llm, "_fallback", None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RateLimitError):
        llm.chat_with_tools([], [])

def test_non_retryable_error_is_not_swallowed(monkeypatch):
    groq, google = Fake([ValueError("bug")]), Fake(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    with pytest.raises(ValueError):
        llm.chat_with_tools([], [])
    assert groq.calls == 1 and google.calls == 0

    