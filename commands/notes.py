import re
from core.colors import c, C, header, ok, err, info, warn
from core import db

FLAG_PATTERNS = {
    "HackTheBox":  r"^[a-f0-9]{32}$",
    "TryHackMe":   r"^THM\{.+\}$",
    "PicoCTF":     r"^picoCTF\{.+\}$",
    "CTFTime":     r"^.+\{.+\}$",
    "VulnHub":     r"^.{5,}$",
    "PWNABLE":     r"^.{5,}$",
    "Root-Me":     r"^.{5,}$",
    "Custom":      r"^.{5,}$",
}

STAGES = ["recon","enumeration","foothold","privesc","flag"]

def _advance_stage(session_name, current_stage):
    idx = STAGES.index(current_stage) if current_stage in STAGES else 0
    next_stage = STAGES[min(idx+1, len(STAGES)-1)]
    db.session_update(session_name, stage=next_stage)
    return next_stage

def cmd_note(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    text = " ".join(args).strip().strip('"').strip("'")
    if not text:
        err("Usage: thoth note \"your note here\"")
        return

    db.note_add(s["name"], s["stage"], text)
    db.log_add(s["name"], "note", text[:60])

    ok(f"Note saved to stage: {s['stage']}")
    print()

def cmd_notes(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    notes = db.notes_get(s["name"])
    header(f"Notes — {s['name']}")
    print()

    if not notes:
        info("No notes yet. Use: thoth note \"your note\"")
        print()
        return

    current_stage = None
    for n in notes:
        if n["stage"] != current_stage:
            current_stage = n["stage"]
            print("  " + c(C.BOLD+C.CYAN_L, f"[{current_stage}]"))
        ts   = c(C.GRAY, n["timestamp"].ljust(8))
        text = c(C.WHITE, n["content"])
        print(f"    {ts}  {text}")

    print()
    info(f"{len(notes)} total notes")
    print()

def cmd_log(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    logs = db.log_get(s["name"])
    header(f"Activity Log — {s['name']}")
    print()

    if not logs:
        info("No activity yet.")
        print()
        return

    for entry in logs:
        ts     = c(C.GRAY,   entry["timestamp"].ljust(10))
        action = c(C.CYAN_L, entry["action"].ljust(22))
        detail = c(C.GRAY,   entry["detail"][:50]) if entry["detail"] else ""
        print(f"  {ts}  {action}  {detail}")

    print()
    info(f"{len(logs)} log entries")
    print()

def cmd_flag(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    flag = " ".join(args).strip().strip('"').strip("'")
    if not flag:
        err("Usage: thoth flag <value>")
        print(c(C.GRAY,"  Example: thoth flag THM{abc123}"))
        return

    platform = s.get("platform","Custom")
    pattern  = FLAG_PATTERNS.get(platform, FLAG_PATTERNS["Custom"])

    header("Flag Submission")
    print()
    info(f"Platform  : {platform}")
    info(f"Flag      : {flag}")
    print()

    if re.match(pattern, flag, re.IGNORECASE):
        ok("Flag format valid!")
    else:
        warn(f"Flag format may be incorrect for {platform}.")
        print(c(C.GRAY,f"  Expected pattern: {pattern}"))

    # Mark solved
    db.session_update(s["name"], status="solved", stage="flag")
    db.note_add(s["name"], "flag", f"FLAG: {flag}")
    db.log_add(s["name"], "flag submitted", flag)

    # Show stats
    print()
    print("  " + c(C.BOLD+C.GREEN_L, "Session complete!"))
    print()

    from core.session import _elapsed_str
    notes  = db.notes_get(s["name"])
    hints  = s.get("hints",0)
    time_s = _elapsed_str(s.get("elapsed",0))

    info(f"Session   : {s['name']}")
    info(f"Time      : {time_s}")
    info(f"Hints     : {hints}")
    info(f"Notes     : {len(notes)}")
    print()
    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth writeup --generate") + c(C.GRAY," to auto-generate your writeup."))
    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth review") + c(C.GRAY," for an AI performance review."))
    print()
