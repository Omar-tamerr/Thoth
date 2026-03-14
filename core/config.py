from core.colors import c, C, header, ok, info, err
from core import db

DEFAULTS = {
    "hint_timing":        "normal",
    "preferred_fuzzer":   "gobuster",
    "preferred_scanner":  "nmap",
    "ai_provider":        "groq",
    "ai_model":           "llama-3.3-70b-versatile",
    "theme":              "dark",
    "searchsploit_path":  "searchsploit",
    "groq_api_key":       "",
}

def get(key):
    val = db.profile_get(f"config.{key}")
    return val if val is not None else DEFAULTS.get(key)

def set_val(key, value):
    db.profile_set(f"config.{key}", value)

def cmd_config(args):
    if not args:
        header("Configuration")
        print()
        for k,v in DEFAULTS.items():
            current = get(k)
            key_str = c(C.WHITE, k.ljust(24))
            val_str = c(C.CYAN_L, str(current))
            print(f"  {key_str} {val_str}")
        print()
        print(c(C.GRAY,"  Set a value: ") + c(C.WHITE,"thoth config <key> <value>"))
        print()
        return

    if len(args) == 1:
        key = args[0]
        val = get(key)
        if val is None:
            err(f"Unknown config key: {key}")
        else:
            info(f"{key} = {val}")
        return

    if len(args) >= 2:
        key, value = args[0], " ".join(args[1:])
        if key not in DEFAULTS:
            err(f"Unknown config key: {key}")
            print(c(C.GRAY,"  Valid keys: ") + c(C.WHITE, ", ".join(DEFAULTS.keys())))
            return
        set_val(key, value)
        ok(f"{key} = {value}")
        print()
