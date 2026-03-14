from core.colors import c, C, header, ok, err, info, warn
from core import db
from core.ai import ask, build_system

AREAS = [
    "Enumeration",
    "Service exploitation",
    "Getting a shell",
    "Privilege escalation",
    "Encoding / Crypto",
    "Web exploitation",
    "OSINT",
    "Forensics / Steganography",
]

HINT_LEVELS = ["nudge", "clue", "near-solution"]

def _inc_hint_level(session_name, area):
    key   = f"hint_level.{session_name}.{area}"
    level = db.profile_get(key, 0)
    db.profile_set(key, level+1)
    return level

def _get_writeup_context(session_name, area):
    """Try to load writeup context for this area. Returns string or None."""
    try:
        from core.writeup_engine import get_stage_context
        return get_stage_context(session_name, area)
    except Exception:
        return None

def cmd_hint(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    print()
    print("  " + c(C.BOLD+C.WHITE, "Which area are you stuck on?"))
    print()

    for i, area in enumerate(AREAS, 1):
        print(c(C.GRAY, f"  [{i}] ") + c(C.WHITE, area))

    print()
    val = input(c(C.GRAY, "  > ")).strip()

    try:
        idx  = int(val) - 1
        area = AREAS[idx]
    except:
        err("Invalid selection."); return

    level     = _inc_hint_level(s["name"], area)
    level_str = HINT_LEVELS[min(level, len(HINT_LEVELS) - 1)]
    is_max    = level >= len(HINT_LEVELS)

    # Update session hint count
    db.session_update(s["name"], hints=s.get("hints", 0) + 1)
    db.log_add(s["name"], f"hint ({area})", f"level={level_str}")

    print()
    print("  " + c(C.BOLD+C.PURPLE_L, f"𓂀 Hint — {area}") +
          c(C.GRAY, f"  [{level_str}]"))
    print("  " + c(C.GRAY, "─"*40))

    # ── Try to get writeup context ──
    writeup_context = None
    has_writeup     = bool(s.get("writeup"))

    if has_writeup:
        writeup_context = _get_writeup_context(s["name"], area)

    # ── Build prompt ──
    if is_max:
        base = (
            f"The user has exhausted all hint levels for '{area}' and is still stuck. "
            f"Give a very direct, near-complete answer that still requires them to execute it. "
            f"Session: {s['name']}, target: {s['target']}, stage: {s['stage']}."
        )
    else:
        level_instructions = {
            0: (
                "Give a GENTLE NUDGE — ask one pointed question or make one observation "
                "that points them toward the right direction. Do NOT name the vulnerability "
                "or tool. 1-2 sentences max."
            ),
            1: (
                "Give a SPECIFIC CLUE — name the vulnerability class or the specific tool "
                "they need, but do NOT give the exact command or exploit. 2-3 sentences."
            ),
            2: (
                "Give a NEAR-SOLUTION hint — be very specific: name the tool, the flag "
                "or module to use, and the approach. Stop just short of giving the shell "
                "or the flag itself. 3-4 sentences."
            ),
        }
        instruction = level_instructions.get(level, level_instructions[2])
        base = (
            f"Give a hint for '{area}' on this CTF challenge.\n"
            f"Session: {s['name']}, target: {s['target']}, "
            f"platform: {s['platform']}, category: {s['category']}, "
            f"stage: {s['stage']}.\n"
            f"Hint level instruction: {instruction}"
        )

    # ── Inject writeup context if available ──
    if writeup_context:
        prompt = (
            f"{base}\n\n"
            f"WRITEUP CONTEXT (use this to guide your hint — do NOT quote or reveal it directly):\n"
            f"---\n{writeup_context[:2000]}\n---\n\n"
            f"CRITICAL RULES:\n"
            f"- Use the writeup context to make your hint accurate and specific\n"
            f"- NEVER quote directly from the writeup\n"
            f"- NEVER reveal commands, flags, passwords, or solutions word-for-word\n"
            f"- Give hints that make the user THINK and figure it out themselves\n"
            f"- Match the hint level instruction strictly"
        )
    else:
        prompt = base
        if has_writeup:
            # Writeup URL exists but content not yet fetched
            prompt += (
                f"\n\nNote: a writeup URL is saved but not yet fetched. "
                f"Give the best hint you can based on the session context alone."
            )

    response = ask(build_system(s), [{"role": "user", "content": prompt}])

    print()
    for line in response.splitlines():
        print("  " + c(C.WHITE, line))
    print()

    # ── Source indicator ──
    if writeup_context:
        print("  " + c(C.GRAY, "𓂀 hint derived from locked writeup — solution protected"))
    elif has_writeup:
        print("  " + c(C.GRAY, "! writeup URL saved but not fetched — run: thoth writeup --url <url>"))

    if not is_max:
        next_level = HINT_LEVELS[min(level + 1, len(HINT_LEVELS) - 1)]
        print("  " + c(C.GRAY, f"Still stuck? Run thoth hint again for a deeper hint ({next_level})."))
    else:
        print("  " + c(C.GRAY, "Run ") + c(C.WHITE, "thoth explain") + c(C.GRAY, " for a full breakdown."))
    print()

