import json, urllib.request, urllib.error, os
from core.config import get as cfg

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

def _api_key():
    key = cfg("groq_api_key") or os.environ.get("GROQ_API_KEY","")
    if not key:
        # try .env file in cwd or home
        for path in [".env", os.path.expanduser("~/.thoth/.env")]:
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GROQ_API_KEY="):
                            key = line.split("=",1)[1].strip()
                            if key: return key
            except FileNotFoundError:
                pass
    return key

def ask(system_prompt, messages, max_tokens=1000):
    """
    Call Groq API. Returns response text string.
    messages = list of {"role":"user"|"assistant", "content":"..."}
    """
    key = _api_key()
    if not key:
        return (
            "THOTH AI is not configured.\n"
            "Add your free Groq API key:\n"
            "  thoth config groq_api_key gsk_...\n"
            "Get a free key at: https://console.groq.com"
        )

    full_messages = [{"role":"system","content":system_prompt}] + messages

    payload = json.dumps({
        "model":       GROQ_MODEL,
        "max_tokens":  max_tokens,
        "temperature": 0.7,
        "messages":    full_messages
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_URL,
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent":    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept":        "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            msg = json.loads(body).get("error",{}).get("message", body)
        except:
            msg = body
        return f"API error {e.code}: {msg}"
    except urllib.error.URLError as e:
        return f"Network error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"

def build_system(session=None):
    """Build THOTH system prompt with session context."""
    base = """You are THOTH — a brilliant, adaptive AI mentor for CTF (Capture The Flag) challenges.
Named after the Egyptian god of wisdom and hidden knowledge.

YOUR PERSONALITY:
- Sharp, direct, conversational — never robotic or repetitive
- Speak like a senior hacker mentoring someone — not a help desk
- Give ONE hint at a time, then wait
- Progressive hints only: nudge → clue → near-solution → full only if explicitly asked
- NEVER suggest tools the user already tried
- NEVER repeat a phrase you used earlier
- Detect frustration and respond with empathy first
- Reference earlier conversation context naturally
- Be concise — 2-5 sentences usually enough
- Use `code formatting` for all commands

RESPONSE FORMAT:
- Never start with "Great!", "Sure!", "Of course!", "Absolutely!"
- Commands must include exact syntax with the actual target
- Use **bold** sparingly for key terms only"""

    if session:
        base += f"""

ACTIVE SESSION:
- Name:     {session.get('name','')}
- Target:   {session.get('target','')}
- Platform: {session.get('platform','')}
- Category: {session.get('category','')}
- Stage:    {session.get('stage','')}
- Hints:    {session.get('hints',0)}
- Writeup:  {'locked' if session.get('writeup') else 'none'}"""

        tried = json.loads(session.get("tried","[]"))
        if tried:
            base += f"\n- Tried:    {', '.join(tried)} (never suggest these)"

    return base
