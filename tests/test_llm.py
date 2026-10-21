import httpx, pytest
from types import SimpleNamespace as NS
from groq import RateLimitError, BadRequestError
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

    
def bad_request(text):
    resp = httpx.Response(400, request=httpx.Request("POST", "http://x"))
    return BadRequestError(text, response=resp, body=None)

class Spy(Fake):
    def _create(self, **kw):
        self.last = kw
        return super()._create(**kw)

def test_with_signatures_marks_only_first_call_and_copies():
    calls = [{"id": "a", "function": {"name": "x"}}, {"id": "b", "function": {"name": "y"}}]
    history = [{"role": "user", "content": "hi"},
               {"role": "assistant", "content": "", "tool_calls": calls}]
    out = llm._with_signatures(history)
    sent = out[1]["tool_calls"]
    assert sent[0]["extra_content"]["google"]["thought_signature"] == llm.PLACEHOLDER_SIG
    assert "extra_content" not in sent[1]
    assert "extra_content" not in calls[0]
    assert out[0] == history[0]

def test_with_signatures_keeps_real_signature():
    call = {"id": "a", "extra_content": {"google": {"thought_signature": "REAL"}}}
    out = llm._with_signatures([{"role": "assistant", "content": "", "tool_calls": [call]}])
    assert out[0]["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "REAL"

def test_parse_failure_retries_then_falls_back_with_signatures(monkeypatch):
    groq = Spy([bad_request("Parsing failed. The model generated output that could not be parsed.")])
    google = Spy(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    history = [{"role": "assistant", "content": "",
                "tool_calls": [{"id": "c0", "type": "function", "function": {"name": "run_command", "arguments": "{}"}}]}]
    assert llm.chat_with_tools(history, []) == "google-msg"
    assert groq.calls == 3
    sent = google.last["messages"][0]["tool_calls"][0]
    assert sent["extra_content"]["google"]["thought_signature"] == llm.PLACEHOLDER_SIG
    assert "extra_content" not in history[0]["tool_calls"][0]

def test_unrelated_bad_request_is_not_retried(monkeypatch):
    groq, google = Spy([bad_request("The model does not exist.")]), Spy(["google-msg"])
    monkeypatch.setattr(llm, "client", groq)
    monkeypatch.setattr(llm, "_fallback", google)
    monkeypatch.setattr(llm, "GEMINI_MODEL", "m")
    with pytest.raises(BadRequestError):
        llm.chat_with_tools([], [])
    assert groq.calls == 1 and google.calls == 0