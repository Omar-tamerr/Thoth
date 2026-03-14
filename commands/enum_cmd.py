import json
from core.colors import c, C, header, ok, err, info, warn, divider
from core import db
from data.playbooks import get_playbook

CATEGORIES = {
    "web":       ["gobuster","ffuf","nikto","whatweb","wfuzz","burpsuite","feroxbuster","dirb"],
    "smb":       ["smbclient","enum4linux","crackmapexec","smbmap","rpcclient"],
    "ftp":       ["ftp","hydra","nmap"],
    "ssh":       ["ssh","hydra","ssh-audit","ssh-keyscan"],
    "sql":       ["sqlmap","mysql","psql","sqsh","mssqlclient.py"],
    "dns":       ["dig","dnsenum","dnsrecon","fierce","sublist3r"],
    "privesc":   ["linpeas.sh","winpeas.exe","find","sudo -l","id","uname -a"],
    "forensics": ["binwalk","steghide","foremost","exiftool","strings","file","hexdump"],
    "osint":     ["theHarvester","maltego","recon-ng","sherlock","shodan"],
    "crypto":    ["hashcat","john","hash-identifier","cyberchef"],
    "reversing": ["ghidra","radare2","gdb","objdump","strace","ltrace"],
    "network":   ["nmap","masscan","rustscan","tcpdump","wireshark","netcat"],
}

def cmd_enum(args):
    """thoth enum --port <N>"""
    port = None
    if "--port" in args:
        idx = args.index("--port")
        if idx+1 < len(args):
            try: port = int(args[idx+1])
            except: pass

    if port is None:
        err("Usage: thoth enum --port <port_number>")
        print(c(C.GRAY,"  Example: ") + c(C.WHITE,"thoth enum --port 445"))
        return

    pb = get_playbook(port)
    if not pb:
        err(f"No playbook found for port {port}.")
        info("Available playbooks: " + ", ".join(str(p) for p in sorted(__import__('data.playbooks', fromlist=['get_all_ports']).get_all_ports())))
        return

    s = db.get_active()
    target = s["target"] if s else "<target>"

    header(f"Port {port} — {pb['name']}")
    print()
    info(pb["description"])
    print()

    # Default creds
    if pb["default_creds"]:
        print("  " + c(C.BOLD+C.GOLD_L, "Default credentials:"))
        for u,p in pb["default_creds"]:
            u_s = c(C.WHITE, u or "<empty>")
            p_s = c(C.GRAY,  p or "<empty>")
            print(f"    {u_s}  /  {p_s}")
        print()

    # CVEs
    if pb["cves"]:
        print("  " + c(C.BOLD+C.RED, "Known CVEs:"))
        for cve in pb["cves"]:
            print("    " + c(C.RED, cve))
        print()

    # Enum commands
    print("  " + c(C.BOLD+C.CYAN_L, "Enumeration commands:"))
    for cmd in pb["enum"]:
        filled = cmd.replace("{target}", target)
        print("    " + c(C.WHITE, filled))
    print()

    # Connect
    print("  " + c(C.BOLD+C.CYAN_L, "Connect:"))
    print("    " + c(C.WHITE, pb["connect"].replace("{target}", target)))
    print()

    # Notes
    if pb["notes"]:
        print("  " + c(C.BOLD+C.GOLD_L, "Tips:"))
        print("    " + c(C.GRAY, pb["notes"]))
    print()

    if s:
        db.log_add(s["name"], f"enum --port {port}", pb["name"])

def cmd_paths(args):
    """thoth paths — ranked attack paths from scan data"""
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    scan_raw = s.get("scan_data")
    if not scan_raw:
        err("No scan data found. Run thoth scan first.")
        return

    try:
        ports = json.loads(scan_raw)
    except:
        err("Invalid scan data. Run thoth scan again.")
        return

    header("Attack Paths")
    print()

    tried = json.loads(s.get("tried","[]"))

    scored = []
    for p in ports:
        if p["state"] != "open":
            continue
        port = p["port"]
        pb   = get_playbook(port)
        name = pb["name"] if pb else p["service"]
        cves = pb["cves"] if pb else []

        # Score: CVEs = high, web = med, everything else = low
        if cves:
            score = 3
            label = c(C.BOLD+C.RED, "HIGH  ")
        elif port in [80,443,8080,8443]:
            score = 2
            label = c(C.BOLD+C.GOLD_L, "MED   ")
        else:
            score = 1
            label = c(C.GRAY, "LOW   ")

        dead = p["service"] in tried
        scored.append((score, port, name, label, cves, dead, p["version"]))

    scored.sort(key=lambda x: -x[0])

    for i,(score,port,name,label,cves,dead,ver) in enumerate(scored,1):
        dead_tag = c(C.GRAY," [tried]") if dead else ""
        ver_s    = c(C.GRAY, f"  {ver}") if ver else ""
        print(f"  [{i}] " + label +
              c(C.WHITE, f"port {port}") + c(C.GRAY, f"/{name}") +
              ver_s + dead_tag)
        if cves:
            for cv in cves[:2]:
                print("       " + c(C.RED, cv))
        print()

    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth enum --port <N>") + c(C.GRAY," for a service playbook."))
    print()
    db.log_add(s["name"], "paths", f"{len(scored)} paths")

def cmd_cheat(args):
    """thoth cheat --category <name>"""
    category = None
    if "--category" in args:
        idx = args.index("--category")
        if idx+1 < len(args):
            category = args[idx+1].lower()

    if not category:
        print()
        print("  " + c(C.BOLD+C.WHITE, "Available categories:"))
        for k in sorted(CATEGORIES.keys()):
            print("    " + c(C.CYAN_L, k))
        print()
        print(c(C.GRAY,"  Usage: ") + c(C.WHITE,"thoth cheat --category web"))
        return

    if category not in CATEGORIES:
        err(f"Unknown category: {category}")
        info("Available: " + ", ".join(sorted(CATEGORIES.keys())))
        return

    s = db.get_active()
    target = s["target"] if s else "<target>"

    header(f"Cheatsheet — {category}")
    print()

    tools = CATEGORIES[category]
    for tool in tools:
        print("  " + c(C.WHITE, tool))

    print()
    info(f"Run: thoth enum --port <N> for target-specific commands")
    print()
