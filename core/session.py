import json, os
from datetime import datetime
from core.colors import c, C, header, ok, err, info, warn, divider
from core import db

PLATFORMS = ["HackTheBox","TryHackMe","PicoCTF","CTFTime","VulnHub","PWNABLE","Root-Me","Custom"]
CATEGORIES = ["general","web","forensics","osint","crypto","pwn","reversing","network","misc"]
STAGES     = ["recon","enumeration","foothold","privesc","flag"]

def _prompt(label, default=""):
    val = input(c(C.GRAY,"  > ")+c(C.WHITE,f"{label}: ")).strip()
    return val or default

def _choose(label, options):
    print(c(C.GRAY, f"\n  {label}:"))
    for i,o in enumerate(options,1):
        print(c(C.GRAY,f"    [{i}] ")+c(C.WHITE,o))
    val = input(c(C.GRAY,"  > ")).strip()
    try:
        idx = int(val)-1
        if 0 <= idx < len(options): return options[idx]
    except: pass
    return options[0]

def _elapsed_str(seconds):
    if not seconds: return "--"
    h,r = divmod(int(seconds),3600)
    m,s = divmod(r,60)
    if h: return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"

# ── thoth new ──
def cmd_new(args):
    header("New Session", C.BOLD+C.CYAN_L)
    print()

    name = _prompt("Session name (e.g. HTB-Lame)")
    if not name:
        err("Session name is required."); return

    if db.session_exists(name):
        err(f"Session '{name}' already exists.")
        print(c(C.GRAY,"  Use ") + c(C.WHITE,f"thoth resume {name}") + c(C.GRAY," to resume it."))
        return

    target   = _prompt("Target IP / URL")
    if not target:
        err("Target is required."); return

    platform = _choose("Platform", PLATFORMS)
    category = _choose("Category", CATEGORIES)
    writeup  = _prompt("Writeup URL (optional, press Enter to skip)")

    db.session_create(name, target, platform, category, writeup)
    db.set_active(name)
    db.log_add(name, "session created", f"target={target} platform={platform}")

    print()
    ok(f"Session '{name}' created.")
    info(f"Target    : {target}")
    info(f"Platform  : {platform}")
    info(f"Category  : {category}")
    if writeup:
        info(f"Writeup   : locked")
    print()
    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth scan") + c(C.GRAY," to start enumeration."))
    print()

# ── thoth sessions ──
def cmd_sessions(args):
    header("Sessions")
    sessions = db.session_all()

    if not sessions:
        print(c(C.GRAY,"  No sessions yet. Run ") + c(C.WHITE,"thoth new") + c(C.GRAY," to start."))
        print()
        return

    active_name = db.profile_get("active_session","")
    print()

    col_w = [18, 12, 12, 10, 8, 8]
    headers = ["NAME","PLATFORM","CATEGORY","STATUS","TIME","HINTS"]
    hdr = ""
    for i,h in enumerate(headers):
        hdr += c(C.GRAY, h.ljust(col_w[i]))
    print("  " + hdr)
    print("  " + c(C.GRAY,"─"*70))

    for s in sessions:
        status = s["status"]
        is_active = s["name"] == active_name

        name_col = c(C.BOLD+C.WHITE, s["name"][:16].ljust(col_w[0]))
        plat_col = c(C.GRAY, (s["platform"] or "")[:10].ljust(col_w[1]))
        cat_col  = c(C.GRAY, (s["category"] or "")[:10].ljust(col_w[2]))

        if status == "solved":
            stat_col = c(C.GREEN_L, "solved".ljust(col_w[3]))
        elif is_active:
            stat_col = c(C.CYAN_L, "active".ljust(col_w[3]))
        else:
            stat_col = c(C.GRAY, "open".ljust(col_w[3]))

        time_col  = c(C.GRAY, _elapsed_str(s.get("elapsed",0)).ljust(col_w[4]))
        hints_col = c(C.GRAY, str(s.get("hints",0)).ljust(col_w[5]))

        marker = c(C.BOLD+C.CYAN_L," ← ") if is_active else "    "
        print("  " + name_col + plat_col + cat_col + stat_col + time_col + hints_col + marker)

    print()
    total   = len(sessions)
    solved  = sum(1 for s in sessions if s["status"]=="solved")
    info(f"{solved}/{total} solved")
    print()

# ── thoth resume ──
def cmd_resume(args):
    if not args:
        # list sessions and prompt
        sessions = db.session_all()
        if not sessions:
            err("No sessions found. Run thoth new to create one.")
            return
        print()
        for i,s in enumerate(sessions,1):
            status = c(C.GREEN_L,"solved") if s["status"]=="solved" else c(C.CYAN_L,"active")
            print(c(C.GRAY,f"  [{i}] ")+c(C.WHITE,s["name"])+c(C.GRAY," — ")+status)
        print()
        val = input(c(C.GRAY,"  Choose session: ")).strip()
        try:
            idx = int(val)-1
            name = sessions[idx]["name"]
        except:
            err("Invalid selection."); return
    else:
        name = args[0]

    s = db.session_get(name)
    if not s:
        err(f"Session '{name}' not found."); return

    db.set_active(name)
    db.log_add(name, "session resumed")

    header(f"Resumed: {name}", C.BOLD+C.PURPLE_L)
    print()
    info(f"Target    : {s['target']}")
    info(f"Platform  : {s['platform']}")
    info(f"Category  : {s['category']}")
    info(f"Stage     : {s['stage']}")
    info(f"Elapsed   : {_elapsed_str(s.get('elapsed',0))}")
    info(f"Hints     : {s.get('hints',0)}")
    if s.get("writeup"):
        info(f"Writeup   : locked")

    notes = db.notes_get(name)
    if notes:
        info(f"Notes     : {len(notes)} saved")

    print()
    ok(f"Session '{name}' is now active.")
    print()

# ── thoth delete ──
def cmd_delete(args):
    if not args:
        err("Usage: thoth delete <session-name>"); return

    name = args[0]
    if not db.session_exists(name):
        err(f"Session '{name}' not found."); return

    print()
    confirm = input(c(C.GRAY,f"  Delete session '{name}'? This cannot be undone. [y/N]: ")).strip().lower()
    if confirm != "y":
        info("Cancelled."); return

    db.session_delete(name)
    active = db.profile_get("active_session","")
    if active == name:
        db.profile_set("active_session", "")

    ok(f"Session '{name}' deleted.")
    print()

# ── thoth export ──
def cmd_export(args):
    if not args:
        s = db.get_active()
        if not s:
            err("No active session. Run thoth resume <name> first."); return
        name = s["name"]
    else:
        name = args[0]

    s = db.session_get(name)
    if not s:
        err(f"Session '{name}' not found."); return

    notes    = db.notes_get(name)
    activity = db.log_get(name)

    export = {
        "session":  s,
        "notes":    notes,
        "activity": activity,
        "exported": datetime.now().isoformat()
    }

    export_dir = os.path.expanduser("~/thoth-exports")
    os.makedirs(export_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(export_dir, f"{name}-{date_str}.json")

    with open(path,"w") as f:
        json.dump(export, f, indent=2)

    print()
    ok(f"Session exported.")
    info(f"File: {path}")
    print()
