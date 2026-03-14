import base64, binascii, urllib.parse, json, re
from core.colors import c, C, header, ok, err, info, warn

def _try_base64(s):
    try:
        decoded = base64.b64decode(s + "==").decode("utf-8")
        if decoded.isprintable(): return decoded
    except: pass
    return None

def _try_hex(s):
    clean = s.replace(" ","").replace("0x","")
    try:
        decoded = bytes.fromhex(clean).decode("utf-8")
        if decoded.isprintable(): return decoded
    except: pass
    return None

def _try_rot13(s):
    result = ""
    for ch in s:
        if ch.isalpha():
            base  = ord('A') if ch.isupper() else ord('a')
            result += chr((ord(ch) - base + 13) % 26 + base)
        else:
            result += ch
    return result

def _try_url(s):
    try:
        decoded = urllib.parse.unquote(s)
        if decoded != s: return decoded
    except: pass
    return None

def _try_binary(s):
    clean = s.replace(" ","")
    if not all(c in "01" for c in clean): return None
    if len(clean) % 8 != 0: return None
    try:
        decoded = "".join(chr(int(clean[i:i+8],2)) for i in range(0,len(clean),8))
        if decoded.isprintable(): return decoded
    except: pass
    return None

def _try_morse(s):
    CODE = {
        ".-":"A", "-...":"B", "-.-.":"C", "-..":"D", ".":"E",
        "..-.":"F", "--.":"G", "....":"H", "..":"I", ".---":"J",
        "-.-":"K", ".-..":"L", "--":"M", "-.":"N", "---":"O",
        ".--.":"P", "--.-":"Q", ".-.":"R", "...":"S", "-":"T",
        "..-":"U", "...-":"V", ".--":"W", "-..-":"X", "-.--":"Y",
        "--..":"Z", ".----":"1", "..---":"2", "...--":"3",
        "....-":"4", ".....":"5", "-....":"6", "--...":"7",
        "---..":"8", "----.":"9", "-----":"0",
    }
    try:
        words = s.strip().split("   ")
        result = ""
        for word in words:
            for letter in word.split():
                if letter in CODE:
                    result += CODE[letter]
                else:
                    return None
            result += " "
        return result.strip()
    except: return None

def _try_jwt(s):
    parts = s.split(".")
    if len(parts) != 3: return None
    try:
        header_raw   = base64.b64decode(parts[0] + "==").decode()
        payload_raw  = base64.b64decode(parts[1] + "==").decode()
        header_json  = json.loads(header_raw)
        payload_json = json.loads(payload_raw)
        return f"Header: {json.dumps(header_json)}\nPayload: {json.dumps(payload_json)}"
    except: return None

def _try_caesar(s):
    """Try all ROT shifts"""
    results = []
    for shift in range(1,26):
        result = ""
        for ch in s:
            if ch.isalpha():
                base   = ord('A') if ch.isupper() else ord('a')
                result += chr((ord(ch) - base + shift) % 26 + base)
            else:
                result += ch
        results.append((shift, result))
    return results

def cmd_decode(args):
    if not args:
        err("Usage: thoth decode <string>")
        return

    text = " ".join(args).strip().strip('"').strip("'")
    header("Decode")
    print()
    info(f"Input: {text[:80]}")
    print()

    found = []

    # JWT
    r = _try_jwt(text)
    if r:
        found.append(("JWT", r))

    # Base64
    r = _try_base64(text)
    if r:
        found.append(("Base64", r))

    # Hex
    r = _try_hex(text)
    if r:
        found.append(("Hex", r))

    # URL encoded
    r = _try_url(text)
    if r:
        found.append(("URL encoded", r))

    # Binary
    r = _try_binary(text)
    if r:
        found.append(("Binary", r))

    # Morse
    r = _try_morse(text)
    if r:
        found.append(("Morse code", r))

    # ROT13
    r = _try_rot13(text)
    if r and r != text:
        found.append(("ROT13", r))

    if found:
        for encoding, result in found:
            print("  " + c(C.BOLD+C.GREEN_L, f"✓ {encoding}:"))
            for line in str(result).splitlines():
                print("    " + c(C.WHITE, line))
            print()
    else:
        warn("No common encoding detected.")
        print()
        # Show Caesar shifts anyway
        print("  " + c(C.GRAY, "Caesar cipher possibilities:"))
        for shift, result in _try_caesar(text)[:5]:
            print(c(C.GRAY,f"    ROT{shift:2d}: ") + c(C.WHITE, result))
        print()
