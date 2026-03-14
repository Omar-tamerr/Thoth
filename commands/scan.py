import subprocess, json, re
from core.colors import c, C, header, ok, err, info, warn
from commands.gamify import get_vpn_ip
from core import db
from core.ai import ask, build_system

# Known port → service map for offline fallback
PORT_MAP = {
    21:"FTP", 22:"SSH", 23:"Telnet", 25:"SMTP", 53:"DNS",
    80:"HTTP", 110:"POP3", 111:"RPCbind", 135:"MSRPC",
    139:"NetBIOS", 143:"IMAP", 443:"HTTPS", 445:"SMB",
    512:"Rexec", 513:"Rlogin", 514:"RSH", 993:"IMAPS",
    995:"POP3S", 1099:"RMI", 1433:"MSSQL", 2049:"NFS",
    3306:"MySQL", 3389:"RDP", 5432:"PostgreSQL", 5900:"VNC",
    6379:"Redis", 6667:"IRC", 8080:"HTTP-Alt", 8443:"HTTPS-Alt",
    27017:"MongoDB", 11211:"Memcached",
}

def _parse_nmap(output):
    """Parse nmap output into list of {port, proto, state, service, version}"""
    results = []
    for line in output.splitlines():
        m = re.match(r'(\d+)/(tcp|udp)\s+(\w+)\s+([\w\-]+)\s*(.*)', line)
        if m:
            results.append({
                "port":    int(m.group(1)),
                "proto":   m.group(2),
                "state":   m.group(3),
                "service": m.group(4),
                "version": m.group(5).strip(),
            })
    return results

def cmd_scan(args):
    s = db.get_active()
    if not s:
        err("No active session. Run thoth new or thoth resume first.")
        return

    target = s["target"]
    use_ai = "--ai" in args

    # Auto-detect VPN IP and save for other commands
    vpn_ip, vpn_iface = get_vpn_ip()
    if vpn_ip:
        from core import db as _db
        _db.profile_set("vpn_ip", vpn_ip)
    fast   = "--fast" in args

    header(f"Scanning {target}")
    print()
    info("Running nmap...")

    nmap_cmd = ["nmap", "-sV", "-sC", "--open"]
    if fast:
        nmap_cmd += ["-F"]
    else:
        nmap_cmd += ["-p-", "--min-rate", "3000"]
    nmap_cmd.append(target)

    try:
        result = subprocess.run(
            nmap_cmd, capture_output=True, text=True, timeout=300
        )
        raw_output = result.stdout
    except FileNotFoundError:
        err("nmap not found. Install nmap first: sudo apt install nmap")
        return
    except subprocess.TimeoutExpired:
        err("Scan timed out. Try --fast flag for a quicker scan.")
        return
    except Exception as e:
        err(f"Scan failed: {e}")
        return

    ports = _parse_nmap(raw_output)

    if not ports:
        warn("No open ports found.")
        info("Try: thoth scan --fast  for a quicker scan")
        print()
        return

    # Display results
    print()
    print("  " + c(C.GRAY, "PORT".ljust(10) + "STATE".ljust(10) + "SERVICE".ljust(14) + "VERSION"))
    print("  " + c(C.GRAY, "─"*60))
    for p in ports:
        port_s    = c(C.BOLD+C.WHITE, f"{p['port']}/{p['proto']}".ljust(10))
        state_s   = c(C.GREEN_L,       p["state"].ljust(10))
        service_s = c(C.CYAN_L,        p["service"].ljust(14))
        version_s = c(C.GRAY,          p["version"])
        print(f"  {port_s}{state_s}{service_s}{version_s}")

    print()
    info(f"Found {len(ports)} open port(s)")

    # Save scan data to session
    db.session_update(s["name"], scan_data=json.dumps(ports), stage="enumeration")
    db.log_add(s["name"], "scan", f"{len(ports)} ports found: {','.join(str(p['port']) for p in ports)}")

    # Playbook hints
    print()
    print("  " + c(C.GRAY, "Playbooks available:"))
    for p in ports:
        if p["state"] == "open":
            print(c(C.GRAY,"    thoth enum --port ") + c(C.WHITE, str(p["port"])))

    print()
    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth exploit --auto") + c(C.GRAY," to search exploits for all services."))

    # AI interpretation
    if use_ai:
        print()
        print("  " + c(C.BOLD+C.PURPLE_L,"𓂀 AI Analysis"))
        print("  " + c(C.GRAY,"─"*40))
        prompt_msg = f"Analyze this nmap scan for {target}:\n{raw_output}\nGive a brief 3-4 sentence analysis: what stands out, what is the strongest attack path, and what to do first."
        response = ask(build_system(s), [{"role":"user","content":prompt_msg}])
        # wrap output
        for line in response.splitlines():
            print("  " + c(C.WHITE, line))

    print()
