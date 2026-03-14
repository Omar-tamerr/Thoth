import json, os
from datetime import datetime
from core.colors import c, C, header, ok, err, info, warn
from core import db
from core.ai import ask, build_system

def cmd_tools(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    header("Tool Suggestions")
    print()

    tried = json.loads(s.get("tried","[]"))
    scan_raw = s.get("scan_data")
    ports = []
    if scan_raw:
        try: ports = json.loads(scan_raw)
        except: pass

    prompt = (
        f"Suggest the most relevant tools for this CTF session. "
        f"Session: {s['name']}, target: {s['target']}, "
        f"platform: {s['platform']}, category: {s['category']}, "
        f"stage: {s['stage']}, "
        f"open ports: {[p['port'] for p in ports if p.get('state')=='open']}, "
        f"already tried: {tried}. "
        f"List 4-6 specific tools with exact command syntax using {s['target']} as the target. "
        f"Do NOT suggest any tool from: {tried}."
    )
    response = ask(build_system(s), [{"role":"user","content":prompt}])
    for line in response.splitlines():
        print("  " + c(C.WHITE, line))
    print()
    db.log_add(s["name"], "tools", "")

def cmd_explain(args):
    topic = " ".join(args).strip()
    s = db.get_active()

    if not topic:
        err("Usage: thoth explain <topic>")
        print(c(C.GRAY,"  Example: thoth explain CVE-2007-2447"))
        print(c(C.GRAY,"  Example: thoth explain SQL injection"))
        return

    header(f"Explain: {topic}")
    print()

    prompt = (
        f"Explain '{topic}' for a CTF player. "
    )
    if s:
        prompt += (
            f"They are working on session '{s['name']}', target {s['target']}, "
            f"platform {s['platform']}, stage {s['stage']}. "
            f"Tie the explanation to their current challenge where relevant. "
        )
    prompt += (
        "Be clear, educational, and practical. Include what it is, "
        "why it matters in CTF, and how to exploit/use it. "
        "Use code examples where helpful. Keep it under 200 words."
    )

    response = ask(build_system(s) if s else "You are THOTH, a CTF AI mentor.", [{"role":"user","content":prompt}])
    print()
    for line in response.splitlines():
        print("  " + c(C.WHITE, line))
    print()
    if s:
        db.log_add(s["name"], "explain", topic)

def cmd_writeup(args):
    # ── --url ──
    if "--url" in args:
        idx = args.index("--url")
        url = args[idx+1] if idx+1 < len(args) else ""
        if not url:
            err("Usage: thoth writeup --url <url>"); return

        s = db.get_active()
        if not s:
            err("No active session. Run thoth new or thoth resume first."); return

        from core.writeup_engine import fetch_and_store
        print()
        success, msg = fetch_and_store(s["name"], url)

        if not success:
            err(msg)
            print()
            return

        # Save URL to session
        db.session_update(s["name"], writeup=url)
        print()
        ok("Writeup fetched and locked.")
        info(f"URL    : {url}")
        info(f"Parsed : {msg}")
        info("THOTH will now use this writeup to guide your hints.")
        info("The solution is locked — you will only get nudges, not answers.")
        print()
        return

    # ── --generate ──
    if "--generate" in args:
        s = db.get_active()
        if not s:
            err("No active session. Run thoth new or thoth resume first."); return

        header(f"Generating Writeup — {s['name']}")
        print()
        info("Building from session data...")

        notes    = db.notes_get(s["name"])
        logs     = db.log_get(s["name"])
        scan_raw = s.get("scan_data","")
        ports    = []
        try: ports = json.loads(scan_raw)
        except: pass

        context = f"""
Session: {s['name']}
Target: {s['target']}
Platform: {s['platform']}
Category: {s['category']}
Stage reached: {s['stage']}
Hints used: {s.get('hints',0)}

Open ports: {[f"{p['port']}/{p['service']} {p['version']}" for p in ports]}

Notes by stage:
{chr(10).join(f"[{n['stage']}] {n['timestamp']}  {n['content']}" for n in notes)}

Activity log (key events):
{chr(10).join(f"{l['timestamp']}  {l['action']}  {l['detail']}" for l in logs[:20])}
"""

        prompt = (
            f"Write a professional CTF writeup based on this session data:\n{context}\n\n"
            "Format it in clean Markdown with sections: "
            "## Overview, ## Reconnaissance, ## Enumeration, ## Exploitation, ## Post-Exploitation, ## Flags. "
            "Write in first person, past tense. Be technical but clear. "
            "Fill in reasonable details based on the challenge context. "
            "Do NOT include any notes about what is missing."
        )

        writeup_md = ask(build_system(s), [{"role":"user","content":prompt}], max_tokens=2000)

        # Save to file
        export_dir = os.path.expanduser("~/thoth-writeups")
        os.makedirs(export_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(export_dir, f"{s['name']}-{date_str}.md")

        with open(path,"w") as f:
            f.write(f"# {s['name']} — CTF Writeup\n\n")
            f.write(f"**Platform:** {s['platform']}  \n")
            f.write(f"**Category:** {s['category']}  \n")
            f.write(f"**Date:** {date_str}  \n")
            f.write(f"**Author:** Omar Tamer  \n\n---\n\n")
            f.write(writeup_md)

        ok(f"Writeup saved to: {path}")
        print()
        db.log_add(s["name"], "writeup generated", path)
        return

    # No subcommand
    print()
    print(c(C.GRAY,"  Usage:"))
    print("  " + c(C.WHITE,"thoth writeup --url <url>       ") + c(C.GRAY,"Lock a writeup URL"))
    print("  " + c(C.WHITE,"thoth writeup --generate        ") + c(C.GRAY,"Auto-generate writeup from session"))
    print()
