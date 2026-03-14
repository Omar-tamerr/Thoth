import json, time
from core.colors import c, C, header, ok, err, info, warn, ai
from core import db
from core.ai import ask, build_system

def _print_ai(response):
    print()
    for line in response.splitlines():
        print("  " + c(C.WHITE, line))
    print()

# ── thoth ask ──
def cmd_ask(args):
    s = db.get_active()
    question = " ".join(args).strip().strip('"').strip("'")

    if not question:
        err("Usage: thoth ask \"your question\"")
        return

    if not s:
        warn("No active session — answering without context.")

    print()
    print("  " + c(C.BOLD+C.PURPLE_L,"𓂀 THOTH"))
    print("  " + c(C.GRAY,"─"*40))

    prompt = question
    if s:
        db.log_add(s["name"], "ask", question[:60])

    response = ask(build_system(s), [{"role":"user","content":prompt}])
    _print_ai(response)

# ── thoth analyze ──
def cmd_analyze(args):
    s = db.get_active()

    output = ""
    if "--output" in args:
        idx = args.index("--output")
        output = " ".join(args[idx+1:]).strip().strip('"').strip("'")

    if not output:
        print()
        print(c(C.GRAY,"  Paste your command output (press Enter twice when done):"))
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        output = "\n".join(lines).strip()

    if not output:
        err("No output provided."); return

    header("AI Output Analysis")
    print()

    prompt = (
        f"Analyze this command output from a CTF challenge and tell me:\n"
        f"1. What it means\n"
        f"2. What to do next\n"
        f"3. Any red flags or important details\n\n"
        f"Output:\n{output}"
    )
    if s:
        prompt += f"\n\nSession context: target={s['target']}, stage={s['stage']}, category={s['category']}"
        db.log_add(s["name"], "analyze", output[:60])

    response = ask(build_system(s), [{"role":"user","content":prompt}])
    _print_ai(response)

# ── thoth rabbit ──
def cmd_rabbit(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    header("Rabbit Hole Detector")
    print()

    logs     = db.log_get(s["name"])
    notes    = db.notes_get(s["name"])
    scan_raw = s.get("scan_data","")
    ports    = []
    try: ports = json.loads(scan_raw)
    except: pass

    # Build context
    recent_actions = [f"{l['action']} {l['detail']}" for l in logs[-15:]]
    hints_used     = s.get("hints", 0)

    prompt = (
        f"Analyze this CTF session and determine if the player is stuck in a rabbit hole.\n\n"
        f"Session: {s['name']}\n"
        f"Target: {s['target']}\n"
        f"Stage: {s['stage']}\n"
        f"Hints used: {hints_used}\n"
        f"Open ports: {[str(p['port'])+'/'+p['service'] for p in ports]}\n"
        f"Recent activity: {recent_actions}\n"
        f"Notes: {[n['content'] for n in notes[-5:]]}\n\n"
        f"Be direct. Tell them:\n"
        f"1. Are they in a rabbit hole? (yes/no and why)\n"
        f"2. What they should pivot to if yes\n"
        f"3. One concrete next step\n"
        f"Keep it under 100 words."
    )

    response = ask(build_system(s), [{"role":"user","content":prompt}])
    _print_ai(response)
    db.log_add(s["name"], "rabbit check", "")

# ── thoth review ──
def cmd_review(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    if s.get("status") != "solved":
        warn("Session not yet solved. Complete the challenge first for a full review.")
        yn = input(c(C.GRAY,"  Review anyway? [y/N]: ")).strip().lower()
        if yn != "y": return

    header(f"Performance Review — {s['name']}")
    print()

    logs  = db.log_get(s["name"])
    notes = db.notes_get(s["name"])

    from core.session import _elapsed_str
    elapsed = _elapsed_str(s.get("elapsed",0))

    prompt = (
        f"Give a constructive performance review for this CTF solve.\n\n"
        f"Session: {s['name']}\n"
        f"Platform: {s['platform']}, Category: {s['category']}\n"
        f"Time: {elapsed}\n"
        f"Hints used: {s.get('hints',0)}\n"
        f"Notes: {[n['content'] for n in notes]}\n"
        f"Activity: {[l['action']+': '+l['detail'] for l in logs]}\n\n"
        f"Structure your review:\n"
        f"1. What they did well (specific)\n"
        f"2. What to improve (specific, constructive)\n"
        f"3. One thing to study before the next session\n"
        f"Be honest but encouraging. Under 150 words."
    )

    response = ask(build_system(s), [{"role":"user","content":prompt}])
    _print_ai(response)
    db.log_add(s["name"], "review", "")

# ── thoth mindset ──
def cmd_mindset(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    header("Mindset Check")
    print()

    logs = db.log_get(s["name"])
    recent = [l["action"] + " " + l["detail"] for l in logs[-10:]]

    # Count repeated actions
    from collections import Counter
    action_counts = Counter(l["action"] for l in logs[-10:])
    repeated = [a for a,n in action_counts.items() if n >= 3]

    prompt = (
        f"A CTF player seems frustrated or stuck. Give them a brief, direct motivational "
        f"redirect — not generic cheerleading.\n\n"
        f"Session: {s['name']}, stage: {s['stage']}, hints: {s.get('hints',0)}\n"
        f"Recent actions: {recent}\n"
        f"Repeated actions (possible loops): {repeated}\n\n"
        f"Acknowledge the struggle, then redirect with ONE concrete thing to try. "
        f"Be human, not robotic. Under 80 words."
    )

    response = ask(build_system(s), [{"role":"user","content":prompt}])
    _print_ai(response)
    db.log_add(s["name"], "mindset", "")

# ── thoth script ──
def cmd_script(args):
    s    = db.get_active()
    task = " ".join(args).strip().strip('"').strip("'")

    if not task:
        err("Usage: thoth script \"describe what you need\"")
        print(c(C.GRAY,'  Example: thoth script "scan all ports then run vuln scripts"'))
        return

    header("Script Generator")
    print()

    target = s["target"] if s else "<target>"

    prompt = (
        f"Generate a shell script or command sequence for this task: '{task}'\n"
        f"Target IP/URL: {target}\n"
        f"Output ONLY the commands/script — no explanation, no markdown fences. "
        f"Use bash. Include comments only if the logic is complex. "
        f"Make it copy-paste ready."
    )
    if s:
        prompt += f"\nContext: {s['platform']}, {s['category']}, stage: {s['stage']}"

    response = ask(build_system(s) if s else "You are THOTH, a CTF AI mentor.", [{"role":"user","content":prompt}])

    print()
    print("  " + c(C.GRAY,"─"*50))
    for line in response.splitlines():
        print("  " + c(C.CYAN_L, line))
    print("  " + c(C.GRAY,"─"*50))
    print()
    info("Copy and run in your terminal.")
    print()

    if s:
        db.log_add(s["name"], "script", task[:60])
