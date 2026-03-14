import json
from core.colors import c, C, header, ok, err, info, warn
from core import db

STAGES = ["recon","enumeration","foothold","privesc","flag"]

def _bar(pct, width=20):
    filled = int(pct/100 * width)
    bar    = "█" * filled + "░" * (width-filled)
    return bar

def cmd_progress(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    header(f"Progress — {s['name']}")
    print()

    current = s.get("stage","recon")
    logs    = db.log_get(s["name"])

    # Stage status
    for stage in STAGES:
        idx     = STAGES.index(stage)
        cur_idx = STAGES.index(current) if current in STAGES else 0

        if idx < cur_idx:
            icon  = c(C.GREEN_L, "✓")
            color = C.GRAY
            label = "done"
        elif idx == cur_idx:
            icon  = c(C.CYAN_L, "►")
            color = C.BOLD+C.WHITE
            label = "active"
        else:
            icon  = c(C.GRAY,   "○")
            color = C.GRAY
            label = ""

        # Count hints for this stage
        stage_hints = sum(1 for l in logs if f"hint ({stage}" in l.get("action","").lower())
        hint_str    = c(C.GRAY, f"  {stage_hints} hints") if stage_hints else ""
        label_str   = c(C.CYAN_L if label=="active" else C.GRAY, label)

        print(f"  {icon}  {c(color, stage.ljust(14))}  {label_str}{hint_str}")

    print()
    info(f"Hints used  : {s.get('hints',0)}")
    notes = db.notes_get(s["name"])
    info(f"Notes saved : {len(notes)}")
    info(f"Platform    : {s.get('platform','')}")
    info(f"Category    : {s.get('category','')}")
    print()

def cmd_stats(args):
    sessions = db.session_all()
    import shutil, datetime
    w = shutil.get_terminal_size((80,20)).columns

    print()
    print("  " + c(C.BOLD+C.WHITE, "𓂀  THOTH — Player Dashboard"))
    print("  " + c(C.GRAY, "═"*50))
    print()

    if not sessions:
        info("No sessions yet. Run thoth new to start your first session.")
        print()
        return

    total   = len(sessions)
    solved  = [s for s in sessions if s["status"]=="solved"]
    active  = [s for s in sessions if s["status"]=="active"]
    hints   = sum(s.get("hints",0) for s in sessions)
    avg_h   = round(hints/total, 1) if total else 0
    solve_r = int(len(solved)/total*100) if total else 0

    # ── OVERVIEW CARDS ──
    print("  " + c(C.BOLD+C.CYAN_L, "Overview"))
    print("  " + c(C.GRAY, "─"*50))
    print()

    def stat_card(label, value, sub="", color=C.BOLD+C.WHITE):
        val_s = c(color, str(value))
        lbl_s = c(C.GRAY, label)
        sub_s = c(C.GRAY, f"  {sub}") if sub else ""
        print(f"    {lbl_s:<22} {val_s}{sub_s}")

    stat_card("Sessions total",    total)
    stat_card("Solved",            len(solved),  f"{solve_r}% solve rate",
              C.GREEN_L if solve_r >= 70 else (C.GOLD_L if solve_r >= 40 else C.RED))
    stat_card("In progress",       len(active),  "", C.CYAN_L)
    stat_card("Total hints used",  hints,        f"avg {avg_h} per session")
    print()

    # ── SOLVE RATE BAR ──
    print("  " + c(C.BOLD+C.CYAN_L, "Solve Rate"))
    print("  " + c(C.GRAY, "─"*50))
    print()
    filled = int(solve_r / 100 * 40)
    bar    = c(C.GREEN_L, "█" * filled) + c(C.GRAY, "░" * (40-filled))
    print(f"    {bar}  {c(C.BOLD+C.WHITE, str(solve_r)+'%')}")
    print()

    # ── CATEGORY BREAKDOWN ──
    cats = {}
    for s in sessions:
        cat = s.get("category","general") or "general"
        if cat not in cats:
            cats[cat] = {"total":0,"solved":0,"hints":0}
        cats[cat]["total"]  += 1
        cats[cat]["solved"] += 1 if s["status"]=="solved" else 0
        cats[cat]["hints"]  += s.get("hints",0)

    if cats:
        print("  " + c(C.BOLD+C.CYAN_L, "By Category"))
        print("  " + c(C.GRAY, "─"*50))
        print()
        print("  " + c(C.GRAY,
              "  CATEGORY".ljust(18) +
              "SESSIONS".ljust(10) +
              "SOLVED".ljust(10) +
              "HINTS".ljust(8) +
              "RATE"))
        print("  " + c(C.GRAY, "  " + "─"*52))

        for cat, stats in sorted(cats.items(), key=lambda x: -x[1]["solved"]):
            rate  = int(stats["solved"]/stats["total"]*100) if stats["total"] else 0
            bar_w = 12
            filled_c = int(rate/100*bar_w)
            mini_bar = c(C.GREEN_L,"█"*filled_c) + c(C.GRAY,"░"*(bar_w-filled_c))

            cat_s  = c(C.WHITE,  f"  {cat:<16}")
            tot_s  = c(C.GRAY,    str(stats["total"]).ljust(10))
            sol_s  = c(C.GREEN_L if stats["solved"] else C.GRAY,
                       str(stats["solved"]).ljust(10))
            hint_s = c(C.GRAY,    str(stats["hints"]).ljust(8))
            rate_s = mini_bar + c(C.GRAY, f" {rate}%")
            print(f"  {cat_s}{tot_s}{sol_s}{hint_s}{rate_s}")
        print()

    # ── PLATFORM BREAKDOWN ──
    plats = {}
    for s in sessions:
        p = s.get("platform","Unknown") or "Unknown"
        plats[p] = plats.get(p,0)+1

    if plats:
        print("  " + c(C.BOLD+C.CYAN_L, "By Platform"))
        print("  " + c(C.GRAY, "─"*50))
        print()
        for p, cnt in sorted(plats.items(), key=lambda x:-x[1]):
            bar_w = int(cnt/total*20)
            bar   = c(C.PURPLE_L,"█"*bar_w) + c(C.GRAY,"░"*(20-bar_w))
            print(f"    {c(C.WHITE,p):<20} {bar}  {c(C.GRAY,str(cnt))}")
        print()

    # ── HINT EFFICIENCY ──
    print("  " + c(C.BOLD+C.CYAN_L, "Hint Efficiency"))
    print("  " + c(C.GRAY, "─"*50))
    print()

    if avg_h == 0:
        eff_label = c(C.GREEN_L, "Perfect  ") + c(C.GRAY, "No hints used!")
        eff_tip   = "You are solving without hints. Impressive."
    elif avg_h <= 1:
        eff_label = c(C.GREEN_L, "Elite    ") + c(C.GRAY, f"avg {avg_h} hint/session")
        eff_tip   = "Minimal hint usage — strong independent solving."
    elif avg_h <= 3:
        eff_label = c(C.GOLD_L,  "Good     ") + c(C.GRAY, f"avg {avg_h} hints/session")
        eff_tip   = "Healthy hint usage. Try reducing for harder boxes."
    elif avg_h <= 5:
        eff_label = c(C.GOLD_L,  "Average  ") + c(C.GRAY, f"avg {avg_h} hints/session")
        eff_tip   = "Consider locking writeups earlier to guide hints better."
    else:
        eff_label = c(C.RED,     "High     ") + c(C.GRAY, f"avg {avg_h} hints/session")
        eff_tip   = "Focus on enumeration first — most stucks are enum issues."

    print(f"    {eff_label}")
    print(f"    {c(C.GRAY, eff_tip)}")
    print()

    # ── RECENT SESSIONS ──
    recent = sorted(sessions, key=lambda x: x.get("updated",""), reverse=True)[:5]
    print("  " + c(C.BOLD+C.CYAN_L, "Recent Sessions"))
    print("  " + c(C.GRAY, "─"*50))
    print()
    print("  " + c(C.GRAY,
          "  NAME".ljust(20) +
          "PLATFORM".ljust(14) +
          "STATUS".ljust(10) +
          "HINTS"))
    print("  " + c(C.GRAY, "  " + "─"*46))

    for s in recent:
        status = s["status"]
        if status == "solved":
            stat_s = c(C.GREEN_L, "solved".ljust(10))
        elif status == "active":
            stat_s = c(C.CYAN_L,  "active".ljust(10))
        else:
            stat_s = c(C.GRAY,    "open".ljust(10))

        name_s  = c(C.WHITE, f"  {s['name'][:16]:<16}")
        plat_s  = c(C.GRAY,  (s.get("platform","") or "")[:12].ljust(14))
        hints_s = c(C.GRAY,  str(s.get("hints",0)))
        print(f"  {name_s}{plat_s}{stat_s}{hints_s}")

    print()
    print("  " + c(C.GRAY, "─"*50))
    print(c(C.GRAY, "  Run ") + c(C.WHITE,"thoth profile") +
          c(C.GRAY, " for your skill map  ·  ") +
          c(C.WHITE,"thoth progress") +
          c(C.GRAY, " for current session stages"))
    print()


def cmd_map(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    scan_raw = s.get("scan_data")
    header(f"Target Map — {s['target']}")
    print()
    print("  " + c(C.BOLD+C.WHITE, s["target"]))

    if not scan_raw:
        print("  " + c(C.GRAY, "└── No scan data. Run thoth scan first."))
        print()
        return

    try:
        ports = json.loads(scan_raw)
    except:
        err("Invalid scan data."); return

    tried   = json.loads(s.get("tried","[]"))
    current = s.get("stage","recon")

    for i,p in enumerate(ports):
        is_last  = i == len(ports)-1
        prefix   = "  └── " if is_last else "  ├── "
        port_s   = c(C.BOLD+C.WHITE, f"{p['port']}/{p['proto']}")
        service  = c(C.CYAN_L, p["service"])
        version  = c(C.GRAY, f"  {p['version']}") if p.get("version") else ""
        state    = p.get("state","open")

        if p["service"] in tried:
            tag = c(C.GRAY, "  [tried — dead end]")
        elif state == "open":
            tag = c(C.GREEN_L, "  [open]")
        else:
            tag = c(C.GRAY, f"  [{state}]")

        active_tag = c(C.BOLD+C.CYAN_L, "  ← active") if p.get("port") and current == "enumeration" and i==0 else ""

        print(f"{prefix}{port_s}  {service}{version}{tag}{active_tag}")

    print()
    notes = db.notes_get(s["name"])
    if notes:
        print("  " + c(C.GRAY, "─"*30))
        for n in notes[-3:]:
            print("  " + c(C.GRAY, f"[{n['stage']}] {n['timestamp']}  ") + c(C.WHITE, n["content"][:50]))
    print()

def cmd_profile(args):
    sessions = db.session_all()
    header("Player Profile")
    print()

    if not sessions:
        info("Complete some sessions to build your profile.")
        print()
        return

    # Skill map based on hint patterns
    cat_hints = {}
    for s in sessions:
        cat = s.get("category","general")
        cat_hints[cat] = cat_hints.get(cat,0) + s.get("hints",0)

    total_hints = sum(cat_hints.values()) or 1
    solved = [s for s in sessions if s["status"]=="solved"]

    print("  " + c(C.BOLD+C.CYAN_L, "Skill map  (fewer hints = stronger):"))
    print()
    for cat, hints in sorted(cat_hints.items(), key=lambda x:x[1]):
        # Invert: fewer hints = higher skill
        skill = max(0, 100 - int(hints/total_hints*100))
        color = C.GREEN_L if skill>=70 else (C.GOLD_L if skill>=40 else C.RED)
        print(f"    {c(C.WHITE,cat.ljust(14))}  {c(color,_bar(skill,16))}  {c(color,str(skill)+'%')}")

    print()
    info(f"Sessions solved : {len(solved)}/{len(sessions)}")
    info(f"Total hints     : {sum(s.get('hints',0) for s in sessions)}")

    # Preferences
    fuzzer  = db.profile_get("config.preferred_fuzzer","gobuster")
    scanner = db.profile_get("config.preferred_scanner","nmap")
    print()
    print("  " + c(C.BOLD+C.CYAN_L, "Preferences:"))
    info(f"Fuzzer  : {fuzzer}")
    info(f"Scanner : {scanner}")
    print()
