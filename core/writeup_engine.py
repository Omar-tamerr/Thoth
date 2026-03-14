"""
THOTH Writeup Engine
Fetches a writeup URL, strips HTML, splits into stages,
and stores the content locked in the DB.
Hints are derived from the content — never revealed directly.
"""

import urllib.request
import urllib.error
import re
import json
from core import db
from core.colors import c, C, ok, err, info, warn

# ── HTML stripping ──
def _strip_html(html):
    # remove scripts and styles entirely
    html = re.sub(r'<(script|style)[^>]*>.*?</(script|style)>', '', html, flags=re.DOTALL|re.IGNORECASE)
    # replace block tags with newlines
    html = re.sub(r'<(br|p|div|li|h[1-6]|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
    # strip remaining tags
    html = re.sub(r'<[^>]+>', '', html)
    # decode common entities
    html = html.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>') \
               .replace('&quot;','"').replace('&#39;',"'").replace('&nbsp;',' ')
    # collapse whitespace
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r'[ \t]+', ' ', html)
    return html.strip()

# ── Fetch URL ──
def _fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            # try utf-8 then latin-1
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1")
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {e.reason}")
    except Exception as e:
        raise Exception(str(e))

# ── Stage splitter ──
# Looks for common CTF writeup section headings
STAGE_PATTERNS = {
    "recon":       r"(nmap|recon|reconnaissance|port.?scan|initial.?scan)",
    "enumeration": r"(enum|enumerat|footprint|discover|gobust|dirb|smbclient|ftp)",
    "foothold":    r"(foothold|initial.?access|exploit|shell|rce|reverse.?shell|metasploit|burp)",
    "privesc":     r"(priv.?esc|privilege|root|escalat|sudo|suid|cron|lpe|local)",
    "flag":        r"(flag|proof|loot|user\.txt|root\.txt|capture)",
}

def _split_stages(text):
    """
    Split writeup text into stage buckets.
    Returns dict: { stage_name: [list of relevant paragraphs] }
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 40]

    stages = {k: [] for k in STAGE_PATTERNS}
    stages["general"] = []

    for para in paragraphs:
        matched = False
        para_lower = para.lower()
        for stage, pattern in STAGE_PATTERNS.items():
            if re.search(pattern, para_lower):
                stages[stage].append(para)
                matched = True
                break
        if not matched:
            stages["general"].append(para)

    # Remove empty stages
    return {k: v for k, v in stages.items() if v}

# ── Key facts extractor ──
def _extract_key_facts(text):
    """
    Pull out the most CTF-relevant lines:
    CVEs, ports, tool names, credentials, flags, hashes
    """
    facts = []
    patterns = [
        r'CVE-\d{4}-\d+',
        r'port\s+\d+',
        r'\d+/(tcp|udp)',
        r'(nmap|gobuster|metasploit|burp|sqlmap|hydra|enum4linux|smbclient|dirb|ffuf)[^\n]{0,80}',
        r'(username|password|cred)[^\n]{0,60}',
        r'(flag|proof)\{[^\}]{0,60}\}',
        r'[a-f0-9]{32}',  # md5 hashes
        r'exploit[^\n]{0,80}',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            fact = match.group(0).strip()
            if fact not in facts and len(fact) > 5:
                facts.append(fact)

    return facts[:30]  # cap at 30 facts

# ── Main: fetch and store ──
def fetch_and_store(session_name, url):
    """
    Fetch the writeup, parse it, and store in DB.
    Returns (success: bool, message: str)
    """
    info(f"Fetching writeup...")

    try:
        html = _fetch(url)
    except Exception as e:
        return False, f"Could not fetch writeup: {e}"

    text = _strip_html(html)

    if len(text) < 200:
        return False, "Page content too short — may be blocked or require login."

    stages    = _split_stages(text)
    key_facts = _extract_key_facts(text)

    # Store in DB as JSON — locked, not shown to user
    writeup_data = {
        "url":       url,
        "stages":    stages,
        "key_facts": key_facts,
        "full_text": text[:8000],  # cap storage at 8KB
        "locked":    True,
    }

    db.profile_set(f"writeup.{session_name}", json.dumps(writeup_data))
    db.log_add(session_name, "writeup fetched", url)

    stage_count = len([k for k,v in stages.items() if v and k != "general"])
    return True, f"{stage_count} stages parsed, {len(key_facts)} key facts extracted."

# ── Load stored writeup ──
def load_writeup(session_name):
    """Returns the stored writeup dict or None."""
    raw = db.profile_get(f"writeup.{session_name}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except:
        return None

# ── Get stage content for hint engine ──
def get_stage_context(session_name, area):
    """
    Returns relevant writeup paragraphs for a given hint area.
    Maps hint areas to writeup stages.
    Never returns the full text — just the relevant section.
    """
    AREA_TO_STAGE = {
        "Enumeration":             ["enumeration", "recon", "general"],
        "Service exploitation":    ["foothold", "enumeration", "general"],
        "Getting a shell":         ["foothold", "general"],
        "Privilege escalation":    ["privesc", "general"],
        "Encoding / Crypto":       ["general", "foothold"],
        "Web exploitation":        ["enumeration", "foothold", "general"],
        "OSINT":                   ["recon", "general"],
        "Forensics / Steganography": ["general", "recon"],
    }

    writeup = load_writeup(session_name)
    if not writeup:
        return None

    stages_to_check = AREA_TO_STAGE.get(area, ["general"])
    content_parts   = []

    for stage in stages_to_check:
        paras = writeup.get("stages", {}).get(stage, [])
        # Take first 3 paragraphs from each relevant stage
        content_parts.extend(paras[:3])
        if len(content_parts) >= 5:
            break

    if not content_parts:
        # Fallback: use key facts
        return "\n".join(writeup.get("key_facts", [])[:10])

    return "\n\n".join(content_parts[:5])
