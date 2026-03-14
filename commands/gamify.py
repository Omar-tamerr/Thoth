"""
THOTH — VPN detect, share, gamification
- Auto VPN IP detection (tun0)
- thoth share — session summary
- Streak, badges, ratings
"""

import re, subprocess, json, os, hashlib
from datetime import datetime, date
from core.colors import c, C, header, ok, err, info, warn
from core import db

# ── VPN Detection ──
def get_vpn_ip():
    """Detect tun0/tun1 IP automatically."""
    for iface in ["tun0","tun1","tap0","vpn0"]:
        try:
            r = subprocess.run(
                ["ip","addr","show", iface],
                capture_output=True, text=True, timeout=5
            )
            m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', r.stdout)
            if m: return m.group(1), iface
        except: pass
    return None, None

def cmd_vpn(args):
    """thoth vpn — show VPN status and IP."""
    ip, iface = get_vpn_ip()
    print()
    if ip:
        ok(f"VPN connected — {iface}: {ip}")
        print()
        info("This IP is used automatically in:")
        print(c(C.GRAY,"    thoth revshell  ·  thoth pivot  ·  thoth scan  ·  thoth script"))
        print()
        # Save to profile for other commands
        db.profile_set("vpn_ip", ip)
        db.profile_set("vpn_iface", iface)
    else:
        err("No VPN interface detected (tun0/tun1/tap0)")
        print(c(C.GRAY,"  Connect to your VPN first:"))
        print(c(C.GRAY,"  THM: ") + c(C.WHITE,"sudo openvpn your-thm.ovpn"))
        print(c(C.GRAY,"  HTB: ") + c(C.WHITE,"sudo openvpn your-htb.ovpn"))
        print()

# ── Share ──
def cmd_share(args):
    """thoth share — generate shareable session summary."""
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    notes    = db.notes_get(s["name"])
    logs     = db.log_get(s["name"])
    badges   = _get_badges(s, notes, logs)

    from core.session import _elapsed_str
    elapsed  = _elapsed_str(s.get("elapsed", 0))

    header(f"Session Share — {s['name']}")
    print()

    # Build summary card
    lines = []
    lines.append(f"𓂀 THOTH Session Summary")
    lines.append(f"{'─'*40}")
    lines.append(f"Room      : {s['name']}")
    lines.append(f"Platform  : {s.get('platform','')}")
    lines.append(f"Category  : {s.get('category','')}")
    lines.append(f"Status    : {s.get('status','active').upper()}")
    lines.append(f"Time      : {elapsed}")
    lines.append(f"Hints     : {s.get('hints',0)}")
    lines.append(f"Stage     : {s.get('stage','')}")
    if badges:
        lines.append(f"Badges    : {' '.join(b['icon']+' '+b['name'] for b in badges)}")
    lines.append(f"{'─'*40}")
    lines.append(f"Solved with THOTH CTF AI Mentor")
    lines.append(f"github.com/omar-tamerr/thoth")

    # Print card
    for line in lines:
        print("  " + c(C.WHITE, line))

    print()

    # Save as markdown file
    export_dir = os.path.expanduser("~/thoth-exports")
    os.makedirs(export_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(export_dir, f"{s['name']}-share-{date_str}.md")

    with open(path, "w") as f:
        f.write("```\n")
        for line in lines:
            f.write(line + "\n")
        f.write("```\n")

    print()
    ok(f"Share card saved: {path}")
    print()
    print(c(C.GRAY,"  Copy the card above and post it on:"))
    print(c(C.GRAY,"  Reddit r/tryhackme · r/hackthebox · LinkedIn · Discord"))
    print()
    if s: db.log_add(s["name"], "share", "")

# ── Badges ──
BADGE_DEFS = [
    {
        "id":    "no_hints",
        "name":  "Pure Solve",
        "icon":  "⚡",
        "desc":  "Solved without using any hints",
        "check": lambda s,n,l: s.get("hints",0) == 0 and s.get("status")=="solved",
    },
    {
        "id":    "speed_solve",
        "name":  "Speed Demon",
        "icon":  "🔥",
        "desc":  "Solved in under 30 minutes",
        "check": lambda s,n,l: s.get("elapsed",0) < 1800 and s.get("status")=="solved",
    },
    {
        "id":    "note_taker",
        "name":  "Note Taker",
        "icon":  "📝",
        "desc":  "Saved 5 or more notes in a session",
        "check": lambda s,n,l: len(n) >= 5,
    },
    {
        "id":    "explorer",
        "name":  "Explorer",
        "icon":  "🗺",
        "desc":  "Used thoth map and thoth paths",
        "check": lambda s,n,l: any("map" in e.get("action","") for e in l) and
                                any("paths" in e.get("action","") for e in l),
    },
    {
        "id":    "writeup_locked",
        "name":  "Locked In",
        "icon":  "🔒",
        "desc":  "Used a locked writeup for hints",
        "check": lambda s,n,l: bool(s.get("writeup")),
    },
    {
        "id":    "exploit_hunter",
        "name":  "Exploit Hunter",
        "icon":  "🎯",
        "desc":  "Used ExploitDB during the session",
        "check": lambda s,n,l: any("exploit" in e.get("action","") for e in l),
    },
    {
        "id":    "veteran",
        "name":  "Veteran",
        "icon":  "🏆",
        "desc":  "Solved 10 or more rooms total",
        "check": lambda s,n,l: len([x for x in db.session_all()
                                    if x.get("status")=="solved"]) >= 10,
    },
    {
        "id":    "streak_7",
        "name":  "On Fire",
        "icon":  "🔥",
        "desc":  "7-day solving streak",
        "check": lambda s,n,l: _get_streak() >= 7,
    },
]

def _get_badges(session, notes=None, logs=None):
    if notes is None: notes = db.notes_get(session["name"])
    if logs  is None: logs  = db.log_get(session["name"])
    earned = []
    for badge in BADGE_DEFS:
        try:
            if badge["check"](session, notes, logs):
                earned.append(badge)
        except: pass
    return earned

def cmd_badges(args):
    """thoth badges — show all earned badges."""
    sessions = db.session_all()
    header("Achievement Badges")
    print()

    if not sessions:
        info("Complete sessions to earn badges.")
        print(); return

    # Collect all earned badges across all sessions
    all_earned = {}
    for s in sessions:
        notes = db.notes_get(s["name"])
        logs  = db.log_get(s["name"])
        for badge in _get_badges(s, notes, logs):
            all_earned[badge["id"]] = badge

    # Display
    print("  " + c(C.BOLD+C.CYAN_L, "Earned badges:"))
    print()
    if not all_earned:
        info("No badges yet — keep solving!")
    else:
        for badge in all_earned.values():
            print("  " + c(C.BOLD+C.GOLD_L, badge["icon"]) + "  " +
                  c(C.BOLD+C.WHITE, badge["name"]) +
                  c(C.GRAY, f"  —  {badge['desc']}"))
        print()
        ok(f"{len(all_earned)} badge(s) earned")

    print()
    print("  " + c(C.BOLD+C.CYAN_L, "All available badges:"))
    print()
    for badge in BADGE_DEFS:
        earned = badge["id"] in all_earned
        icon   = badge["icon"] if earned else c(C.GRAY,"○")
        name   = c(C.WHITE if earned else C.GRAY, badge["name"])
        desc   = c(C.GRAY, badge["desc"])
        print(f"  {icon}  {name}  —  {desc}")
    print()

# ── Streak ──
def _get_streak():
    """Calculate current solving streak in days."""
    sessions = [s for s in db.session_all() if s.get("status")=="solved"]
    if not sessions: return 0

    # Get solve dates from updated field
    solve_dates = set()
    for s in sessions:
        updated = s.get("updated","")
        if updated:
            try:
                d = datetime.fromisoformat(updated).date()
                solve_dates.add(d)
            except: pass

    if not solve_dates: return 0

    today  = date.today()
    streak = 0
    check  = today
    while check in solve_dates:
        streak += 1
        check = date.fromordinal(check.toordinal()-1)
    return streak

def cmd_streak(args):
    """thoth streak — show current streak."""
    streak = _get_streak()
    sessions = db.session_all()
    solved   = [s for s in sessions if s.get("status")=="solved"]

    print()
    print("  " + c(C.BOLD+C.WHITE,"𓂀  Streak"))
    print("  " + c(C.GRAY,"─"*30))
    print()

    if streak == 0:
        warn("No active streak — solve a room today to start one!")
    elif streak < 3:
        print("  " + c(C.GOLD_L,"🔥"*streak + f"  {streak} day streak"))
    elif streak < 7:
        print("  " + c(C.BOLD+C.GOLD_L,"🔥"*min(streak,5) + f"  {streak} day streak — keep going!"))
    else:
        print("  " + c(C.BOLD+C.RED,"🔥"*5 + f"  {streak} day streak — ON FIRE!"))

    print()
    info(f"Total rooms solved : {len(solved)}")
    info(f"Best streak        : {streak} days")
    print()

# ── Leaderboard (GitHub Gist based) ──
def cmd_leaderboard(args):
    """thoth leaderboard — view or update public leaderboard."""
    sessions = db.session_all()
    solved   = [s for s in sessions if s.get("status")=="solved"]
    hints    = sum(s.get("hints",0) for s in sessions)
    streak   = _get_streak()
    badges   = set()
    for s in sessions:
        notes = db.notes_get(s["name"])
        logs  = db.log_get(s["name"])
        for b in _get_badges(s,notes,logs):
            badges.add(b["id"])

    header("Public Leaderboard")
    print()

    if "--share" in args:
        # Generate shareable stats card
        username = db.profile_get("config.username") or "hacker"
        card = {
            "username": username,
            "solved":   len(solved),
            "hints":    hints,
            "streak":   streak,
            "badges":   list(badges),
            "updated":  datetime.now().isoformat(),
        }
        card_json = json.dumps(card, indent=2)
        print(c(C.GRAY,"  Your stats card (paste to GitHub Gist or Discord):"))
        print()
        print("  " + c(C.GRAY,"─"*40))
        for line in card_json.splitlines():
            print("  " + c(C.WHITE, line))
        print("  " + c(C.GRAY,"─"*40))
        print()
        info("Share this on:")
        print(c(C.GRAY,"  · GitHub Gist: gist.github.com"))
        print(c(C.GRAY,"  · Discord: paste in #achievements channel"))
        print(c(C.GRAY,"  · Reddit: include in your writeup posts"))
        print()
        return

    # Show local stats
    print(c(C.BOLD+C.WHITE, f"  Your stats:"))
    print()
    info(f"Rooms solved : {len(solved)}")
    info(f"Hints used   : {hints}")
    info(f"Streak       : {streak} days")
    info(f"Badges       : {len(badges)}")
    print()
    print(c(C.GRAY,"  Share your stats:"))
    print(c(C.WHITE,"    thoth leaderboard --share"))
    print()
    print(c(C.GRAY,"  Set your username:"))
    print(c(C.WHITE,"    thoth config username YourName"))
    print()

# ── Room rating ──
def cmd_rate(args):
    """thoth rate <1-5> — rate the current room after solving."""
    s = db.get_active()
    if not s:
        err("No active session."); return

    rating = None
    for a in args:
        try:
            r = int(a)
            if 1 <= r <= 5: rating = r; break
        except: pass

    if rating is None:
        print()
        print(c(C.BOLD+C.WHITE, f"  Rate: {s['name']}"))
        print()
        print(c(C.GRAY,"  [1] ★☆☆☆☆  Too easy / boring"))
        print(c(C.GRAY,"  [2] ★★☆☆☆  Below average"))
        print(c(C.GRAY,"  [3] ★★★☆☆  Good room"))
        print(c(C.GRAY,"  [4] ★★★★☆  Great room"))
        print(c(C.GRAY,"  [5] ★★★★★  Excellent / learned a lot"))
        print()
        try:
            val = input(c(C.GRAY,"  Your rating [1-5]: ")).strip()
            rating = int(val)
            if not 1 <= rating <= 5: raise ValueError
        except (ValueError, KeyboardInterrupt):
            err("Invalid rating."); return

    stars = "★"*rating + "☆"*(5-rating)
    labels = {1:"Too easy",2:"Below average",3:"Good room",
              4:"Great room",5:"Excellent"}

    db.profile_set(f"rating.{s['name']}", rating)
    db.log_add(s["name"], "rated", f"{rating}/5")
    print()
    ok(f"Rating saved: {stars}  {labels[rating]}")
    print()
    print(c(C.GRAY,"  This rating helps improve the THOTH library."))
    print(c(C.GRAY,"  Run: ") + c(C.WHITE,"thoth library --rate") +
          c(C.GRAY," to see community ratings."))
    print()
