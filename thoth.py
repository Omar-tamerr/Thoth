#!/usr/bin/env python3
"""
THOTH — CTF AI Mentor
Entry point and CLI router
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.banner   import banner
from core.session  import cmd_new, cmd_sessions, cmd_resume, cmd_delete, cmd_export
from core.config   import cmd_config
from commands.scan     import cmd_scan
from commands.hint     import cmd_hint
from commands.exploit  import cmd_exploit
from commands.notes    import cmd_note, cmd_notes, cmd_log, cmd_flag
from commands.progress import cmd_progress, cmd_stats, cmd_map
from commands.enum_cmd import cmd_enum, cmd_paths, cmd_cheat
from commands.decode   import cmd_decode
from commands.tools    import cmd_tools
from commands.explain  import cmd_explain
from commands.writeup  import cmd_writeup
from commands.library  import cmd_library
from commands.pivot    import cmd_pivot
from commands.gamify   import cmd_vpn, cmd_share, cmd_badges, cmd_streak, cmd_leaderboard, cmd_rate
from commands.ai_cmds  import cmd_ask, cmd_analyze, cmd_rabbit, cmd_review, cmd_mindset, cmd_script
from core.colors   import c, C

def usage():
    import shutil
    w = shutil.get_terminal_size((80,20)).columns

    def line(cmd, desc, example=""):
        cmd_s   = c(C.BOLD+C.WHITE,  f"  thoth {cmd:<30}")
        desc_s  = c(C.GRAY,           desc)
        ex_s    = (c(C.GRAY, "  e.g. ") + c(C.DIM+C.WHITE, example)) if example else ""
        print(cmd_s + desc_s + ex_s)

    def section(title, icon):
        print()
        print("  " + c(C.BOLD+C.CYAN_L, icon + "  " + title))
        print("  " + c(C.GRAY, "─"*50))

    def tip(text):
        print("  " + c(C.GOLD_L,"  tip: ") + c(C.GRAY, text))

    print()
    print(c(C.BOLD+C.WHITE,   "  𓂀  THOTH — CTF AI Mentor"))
    print(c(C.GRAY,           "  Egyptian God of Wisdom & Hidden Knowledge"))
    print(c(C.GRAY,           "  ═"*26))
    print()
    print(c(C.GRAY,   "  THOTH guides you through CTF challenges without spoiling them."))
    print(c(C.GRAY,   "  It uses progressive hints, locked writeups, and AI to teach — not tell."))
    print()

    # ── QUICK START ──
    print("  " + c(C.BOLD+C.GOLD_L, "★  Quick Start — New to THOTH?"))
    print("  " + c(C.GRAY, "─"*50))
    print()
    print(c(C.GRAY,   "    1. ") + c(C.WHITE, "thoth new") +
          c(C.GRAY,   "          Create a session for your machine"))
    print(c(C.GRAY,   "    2. ") + c(C.WHITE, "thoth scan") +
          c(C.GRAY,   "         Scan the target — auto-loads service playbooks"))
    print(c(C.GRAY,   "    3. ") + c(C.WHITE, "thoth writeup --url <url>") +
          c(C.GRAY,   "  Lock a writeup (hints come from it, not spoilers)"))
    print(c(C.GRAY,   "    4. ") + c(C.WHITE, "thoth hint") +
          c(C.GRAY,   "         Get a progressive hint when stuck"))
    print(c(C.GRAY,   "    5. ") + c(C.WHITE, "thoth flag <value>") +
          c(C.GRAY,   "    Submit your flag and close the session"))
    print()

    # ── SESSION ──
    section("Session Management", "◈")
    line("new",              "Start a new named session",           "thoth new")
    line("sessions",         "List all sessions with status",       "thoth sessions")
    line("resume <name>",    "Resume any past session",             "thoth resume HTB-Lame")
    line("delete <name>",    "Delete a session permanently",        "thoth delete HTB-Lame")
    line("export <name>",    "Export session as JSON backup",       "thoth export HTB-Lame")
    tip("Sessions are saved locally in ~/.thoth/thoth.db — you never lose progress")

    # ── SCANNING ──
    section("Scanning & Enumeration", "◈")
    line("scan",                   "Smart nmap scan + auto-load playbooks",  "thoth scan")
    line("scan --fast",            "Quick scan (-F) for speed",               "thoth scan --fast")
    line("scan --ai",              "Scan + AI analysis of results",           "thoth scan --ai")
    line("enum --port <N>",        "Full service playbook for a port",        "thoth enum --port 445")
    line("paths",                  "Ranked attack paths from scan data",      "thoth paths")
    line("map",                    "ASCII mind map of target + tried paths",  "thoth map")
    line("cheat --category <n>",   "Category cheatsheet pre-filled w/ target","thoth cheat --category web")
    tip("thoth enum --port shows default creds, CVEs, and exact commands for any service")

    # ── EXPLOITDB ──
    section("ExploitDB Integration", "◈")
    line("exploit --search <q>",   "Search ExploitDB by text",               "thoth exploit --search \'vsftpd 2.3.4\'")
    line("exploit --cve <id>",     "Search exploits by CVE ID",              "thoth exploit --cve CVE-2007-2447")
    line("exploit --id <edb-id>",  "Full exploit details + usage",           "thoth exploit --id 16320")
    line("exploit --auto",         "Auto-search all services from last scan","thoth exploit --auto")
    tip("Run thoth exploit --auto right after thoth scan for instant exploit lookup")

    # ── GUIDANCE ──
    section("Guidance System", "◈")
    line("hint",                   "Progressive hint — choose your stuck area","thoth hint")
    line("library",                "Browse built-in writeup library",        "thoth library")
    line("library --load <slug>",  "Load a writeup into active session",     "thoth library --load THM-Wgel")
    line("library --update",       "Fetch latest writeups from GitHub",      "thoth library --update")
    line("writeup --url <url>",    "Fetch + lock a custom writeup URL",              "thoth writeup --url https://...")
    line("writeup --generate",     "Auto-generate a Markdown writeup",        "thoth writeup --generate")
    line("tools",                  "Context-aware tool suggestions",           "thoth tools")
    line("explain <topic>",        "Deep explanation tied to your challenge",  "thoth explain CVE-2007-2447")
    line("decode <string>",        "Auto-detect encoding and decode it",       "thoth decode aGVsbG8=")
    tip("Hint levels: nudge (1st) → clue (2nd) → near-solution (3rd) → run again for max")
    print()
    print(c(C.GRAY,"    Hint areas you can choose from:"))
    areas = ["Enumeration","Service exploitation","Getting a shell",
             "Privilege escalation","Encoding / Crypto","Web exploitation","OSINT","Forensics"]
    for i,a in enumerate(areas,1):
        print(c(C.GRAY,f"      [{i}] ") + c(C.WHITE, a))

    # ── NOTES ──
    section("Notes & Logging", "◈")
    line("note \"text\"",           "Save a timestamped note to current stage","thoth note \"found anon FTP\"")
    line("notes",                  "View all notes grouped by stage",         "thoth notes")
    line("log",                    "Full session activity log",               "thoth log")
    line("flag <value>",           "Submit flag — validates format + saves",  "thoth flag THM{abc123}")
    tip("Notes are tied to your current stage automatically — use them to build your writeup")

    # ── PROGRESS ──
    section("Progress & Learning", "◈")
    line("progress",               "Stage timeline for current session",      "thoth progress")
    line("stats",                  "Full stats dashboard — all sessions",     "thoth stats")
    line("profile",                "Skill map built from your hint history",  "thoth profile")
    tip("thoth stats shows solve rate, hint efficiency, category breakdown, and streaks")

    # ── AI ──
    section("AI Commands  (requires Groq API key)", "◈")
    line("ask \"question\"",        "Free-form AI chat about your challenge",  "thoth ask \"why is my shell dying?\"")
    line("analyze --output \"...\"","AI reads + explains command output",      "thoth analyze --output \"NT_STATUS_ACCESS_DENIED\"")
    line("rabbit",                 "Detect if you are in a rabbit hole",     "thoth rabbit")
    line("review",                 "Post-solve AI performance review",        "thoth review")
    line("mindset",                "Stuck? Get a direct redirect",            "thoth mindset")
    line("script \"task\"",         "Generate shell scripts from English",     "thoth script \"scan all ports then check vulns\"")
    tip("All AI commands inject your full session context — THOTH always knows where you are")

    # ── CONFIG ──
    section("Config & Setup", "◈")
    line("config",                 "View all settings",                       "thoth config")
    line("config <key> <value>",   "Set a config value",                      "thoth config groq_api_key gsk_...")
    line("setup",                  "Interactive API key setup wizard",        "thoth setup")
    line("help",                   "Show this help screen",                   "thoth help")
    print()
    print("  " + c(C.GRAY, "─"*50))
    print()
    print(c(C.GRAY,   "  AI provider  : ") + c(C.WHITE, "Groq (free) — https://console.groq.com"))
    print(c(C.GRAY,   "  Sessions     : ") + c(C.WHITE, "~/.thoth/thoth.db"))
    print(c(C.GRAY,   "  Writeups     : ") + c(C.WHITE, "~/thoth-writeups/"))
    print(c(C.GRAY,   "  Made by      : ") + c(C.WHITE, "Omar Tamer  ·  EG"))
    print()


def _get_api_key():
    from core.config import get as cfg
    import os
    key = cfg("groq_api_key") or os.environ.get("GROQ_API_KEY","")
    if not key:
        for path in [".env", os.path.expanduser("~/.thoth/.env")]:
            try:
                with open(path) as f2:
                    for line in f2:
                        if line.strip().startswith("GROQ_API_KEY="):
                            key = line.strip().split("=",1)[1].strip()
                            if key: return key
            except FileNotFoundError:
                pass
    return key

def _setup_wizard():
    print()
    print(c(C.BOLD+C.GOLD_L, "  𓂀  THOTH First-Run Setup"))
    print(c(C.GRAY,           "  ─────────────────────────────────────────"))
    print()
    print(c(C.WHITE,  "  THOTH needs a free Groq API key for AI features."))
    print(c(C.GRAY,   "  Groq is 100% free — no credit card required."))
    print()
    print(c(C.BOLD+C.WHITE, "  1.") + c(C.GRAY, " Go to: ") + c(C.CYAN_L, "https://console.groq.com"))
    print(c(C.BOLD+C.WHITE, "  2.") + c(C.GRAY, " Sign up with Google or email"))
    print(c(C.BOLD+C.WHITE, "  3.") + c(C.GRAY, " Click API Keys -> Create API Key"))
    print(c(C.BOLD+C.WHITE, "  4.") + c(C.GRAY, " Paste it below (starts with gsk_...)"))
    print()
    try:
        key = input(c(C.GRAY, "  Paste key here (Enter to skip): ")).strip()
    except (KeyboardInterrupt, EOFError):
        print(); return
    if not key:
        print()
        print(c(C.GRAY, "  Skipped. Set it later: ") + c(C.WHITE, "thoth config groq_api_key gsk_..."))
        print()
        return
    from core.config import set_val
    set_val("groq_api_key", key)
    print()
    print(c(C.GREEN_L, "  ✓ API key saved! THOTH AI is now active."))
    print()

def main():
    args = sys.argv[1:]

    if not args:
        banner()
        if not _get_api_key():
            _setup_wizard()
        return

    cmd  = args[0].lower()
    rest = args[1:]

    # Intercept AI commands if key missing
    ai_cmds = {"hint","ask","analyze","rabbit","review","mindset","script","tools","explain"}
    if cmd in ai_cmds and not _get_api_key():
        print()
        print(c(C.GOLD_L, "  ! THOTH AI key not configured."))
        print(c(C.GRAY,   "  Free key at: ") + c(C.CYAN_L,"https://console.groq.com"))
        print(c(C.GRAY,   "  Then run: ") + c(C.WHITE,"thoth config groq_api_key gsk_..."))
        print()
        try:
            yn = input(c(C.GRAY,"  Set it up right now? [Y/n]: ")).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(); return
        if yn != "n":
            _setup_wizard()
            if not _get_api_key(): return
        else:
            return



    # ── Session ──
    if cmd == "new":           cmd_new(rest)
    elif cmd == "sessions":    cmd_sessions(rest)
    elif cmd == "resume":      cmd_resume(rest)
    elif cmd == "delete":      cmd_delete(rest)
    elif cmd == "export":      cmd_export(rest)

    # ── Scanning ──
    elif cmd == "scan":        cmd_scan(rest)
    elif cmd == "enum":        cmd_enum(rest)
    elif cmd == "paths":       cmd_paths(rest)
    elif cmd == "map":         cmd_map(rest)
    elif cmd == "cheat":       cmd_cheat(rest)

    # ── ExploitDB ──
    elif cmd == "exploit":     cmd_exploit(rest)

    # ── Guidance ──
    elif cmd == "hint":        cmd_hint(rest)
    elif cmd == "writeup":     cmd_writeup(rest)
    elif cmd == "library":     cmd_library(rest)
    elif cmd == "pivot":       cmd_pivot(rest)
    elif cmd == "vpn":         cmd_vpn(rest)
    elif cmd == "share":       cmd_share(rest)
    elif cmd == "badges":      cmd_badges(rest)
    elif cmd == "streak":      cmd_streak(rest)
    elif cmd == "leaderboard": cmd_leaderboard(rest)
    elif cmd == "rate":        cmd_rate(rest)
    elif cmd == "tools":       cmd_tools(rest)
    elif cmd == "explain":     cmd_explain(rest)
    elif cmd == "decode":      cmd_decode(rest)

    # ── Notes ──
    elif cmd == "note":        cmd_note(rest)
    elif cmd == "notes":       cmd_notes(rest)
    elif cmd == "log":         cmd_log(rest)
    elif cmd == "flag":        cmd_flag(rest)

    # ── Progress ──
    elif cmd == "progress":    cmd_progress(rest)
    elif cmd == "stats":       cmd_stats(rest)
    elif cmd == "profile":     from commands.progress import cmd_profile; cmd_profile(rest)

    # ── AI ──
    elif cmd == "ask":         cmd_ask(rest)
    elif cmd == "analyze":     cmd_analyze(rest)
    elif cmd == "rabbit":      cmd_rabbit(rest)
    elif cmd == "review":      cmd_review(rest)
    elif cmd == "mindset":     cmd_mindset(rest)
    elif cmd == "script":      cmd_script(rest)

    # ── Config ──
    elif cmd == "config":      cmd_config(rest)
    elif cmd == "setup":        _setup_wizard()
    elif cmd in ("help", "--help", "-h"): usage()

    else:
        print(c(C.GRAY, f"\n  Unknown command: ") + c(C.WHITE, cmd))
        print(c(C.GRAY,  "  Run ") + c(C.WHITE, "thoth help") + c(C.GRAY, " for all commands\n"))

if __name__ == "__main__":
    main()
