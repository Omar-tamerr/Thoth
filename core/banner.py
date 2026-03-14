import shutil, re
from core.colors import c, C

def center(text, w):
    clean = re.sub(r'\033\[[0-9;]*m','',text)
    pad   = max(0,(w-len(clean))//2)
    return " "*pad + text

LOGO = [
    (" ████████╗██╗  ██╗ ██████╗ ████████╗██╗  ██╗", C.BOLD+C.PURPLE_L),
    ("    ██╔══╝██║  ██║██╔═══██╗╚══██╔══╝██║  ██║", C.BOLD+C.WHITE),
    ("    ██║   ███████║██║   ██║   ██║   ███████║", C.BOLD+C.CYAN_L),
    ("    ██║   ██╔══██║██║   ██║   ██║   ██╔══██║", C.BOLD+C.WHITE),
    ("    ██║   ██║  ██║╚██████╔╝   ██║   ██║  ██║", C.BOLD+C.PURPLE_L),
    ("    ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝", C.DIM+C.WHITE),
]

EYE = [
    ("         .·´¯`·.         ", C.GRAY),
    ("       ·´         `·     ", C.GRAY),
    ("      /    𓂀   𓃭    \\   ", C.DIM+C.WHITE),
    ("     |   ──────────  |   ", C.BOLD+C.WHITE),
    ("      \\    𓂀   𓃭    /   ", C.DIM+C.WHITE),
    ("       `·.         .·´   ", C.GRAY),
    ("           `·._.·´       ", C.GRAY),
]

def banner():
    w = shutil.get_terminal_size((80,20)).columns
    print()
    hbar = c(C.BOLD+C.WHITE,"𓂀")+c(C.GRAY,"  𓃭  𓆣  𓇋  𓈖  𓉐  𓊃  𓋴  𓌀  𓍿  𓎛  𓏏  ")+c(C.BOLD+C.WHITE,"𓂀")
    print(center(hbar,w)); print()
    for line,col in EYE: print(center(c(col,line),w))
    print()
    for line,col in LOGO: print(center(c(col,line),w))
    print()
    sub = c(C.BOLD+C.PURPLE_L,"CTF AI Mentor")+"  "+c(C.GRAY,"·")+"  "+c(C.BOLD+C.WHITE,"Learn. Solve. Grow.")+"  "+c(C.GRAY,"·")+"  "+c(C.BOLD+C.CYAN_L,"AI-Powered")
    print(center(sub,w)); print()
    div = c(C.GRAY,"─"*10)+c(C.DIM+C.WHITE,"  𓃭 𓆣 𓇋 𓈖 𓉐 𓊃 𓋴  ")+c(C.GRAY,"─"*10)
    print(center(div,w)); print()
    info = (
        c(C.BOLD+C.CYAN_L,"CTF AI Mentor")    +c(C.GRAY,"  ·  ")+
        c(C.GRAY,"v1.0.0")                    +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.WHITE,"All CTF Platforms") +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.PURPLE_L,"AI-Powered")     +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.GOLD_L,"ExploitDB")
    )
    print(center(info,w)); print()
    made = (
        c(C.GRAY,"Made with ")+c(C.BOLD+C.RED,"♥")+c(C.GRAY," by ")+
        c(C.BOLD+C.WHITE,"Omar Tamer")+c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.GOLD_L,"EG")+c(C.GRAY,"  ·  ")+
        c(C.DIM+C.WHITE,"github.com/omartamer/thoth")
    )
    print(center(made,w)); print()
    print(center(c(C.GRAY,"─"*46),w)); print()
    cmds = (
        c(C.BOLD+C.WHITE,"thoth new")  +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.WHITE,"thoth scan") +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.WHITE,"thoth hint") +c(C.GRAY,"  ·  ")+
        c(C.BOLD+C.WHITE,"thoth help")
    )
    print(center(cmds,w)); print()
    print(center(hbar,w)); print()
