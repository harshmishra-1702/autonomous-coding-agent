import os, time, openai
from dotenv import load_dotenv
from groq import (Groq, BadRequestError, RateLimitError, APIConnectionError, APIStatusError)
from openai import OpenAI

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
_fallback = None

def _fb():
    """Google client via its OpenAI-compatible endpoint (same message format as Groq.)"""
    global _fallback
    if _fallback is None and os.getenv("GOOGLE_API_KEY"):
        _fallback = OpenAI(api_key=os.environ["GOOGLE_API_KEY"],
                           base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

    return _fallback



BAD_OUTPUT = ("tool_use_failed", "Parsing failed", "could not be parsed")
PLACEHOLDER_SIG = "skip_thought_signature_validator"

def _with_signatures(messages):
    out = []
    for m in messages:
        calls = m.get("tool_calls")
        if m.get("role") == "assistant" and calls:
            first = dict(calls[0])
            extra = dict(first.get("extra_content") or {})
            google = dict(extra.get("google") or {})
            google.setdefault("thought_signature", PLACEHOLDER_SIG)
            extra["google"] = google
            first["extra_content"] = extra
            m = {**m, "tool_calls": [first] + list(calls[1:])}
        out.append(m)
    return out


def _call(c, model, messages, tools):
    r = c.chat.completions.create(model=model, messages=messages,
                                  tools=tools, tool_choice="auto")

    return r.choices[0].message

def _retryable(e):
    if isinstance(e, (RateLimitError, APIConnectionError)):
        return True
    if isinstance(e, APIStatusError) and e.status_code >= 500:
        return True
    return isinstance(e, BadRequestError) and any(s in str(e) for s in BAD_OUTPUT)
    

def chat(messages):
    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content

def _call_fallback(fb, messages, tools, tries=3):
    msgs = _with_signatures(messages)
    for i in range(tries):
        try:
            return _call(fb, GEMINI_MODEL, msgs, tools)
        except (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError) as e:
            print(f"[google retry {i + 1}/{tries}] {type(e).__name__}")
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def chat_with_tools(messages, tools, retries=2, delay=2):
    last = None
    for i in range(retries + 1):
        try:
            return _call(client, MODEL, messages, tools)
        except Exception as e:
            if not _retryable(e):
                raise
            last = e
            if i < retries:
                time.sleep(delay * (i+1))
    fb =_fb()
    if not (fb and GEMINI_MODEL):
        raise last
    print(f"[fallback] Groq failed ({type(last).__name__}); using Google")
    return _call_fallback(fb, messages, tools) 


if __name__ == "__main__":
    print(chat([{"role":"user", "content": "Say hi in 5s words."}]))
