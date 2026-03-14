import re

class C:
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    ITALIC   = "\033[3m"
    WHITE    = "\033[97m"
    GRAY     = "\033[90m"
    PURPLE_L = "\033[95m"
    CYAN_L   = "\033[96m"
    GOLD_L   = "\033[93m"
    GREEN_L  = "\033[92m"
    RED      = "\033[91m"
    BLUE_L   = "\033[94m"

def c(col, text): return f"{col}{text}{C.RESET}"
def strip(text):  return re.sub(r'\033\[[0-9;]*m', '', text)

def divider(char="─", width=46, color=C.GRAY):
    import shutil
    w = shutil.get_terminal_size((80,20)).columns
    line = char * min(width, w-4)
    print("  " + c(color, line))

def header(title, color=C.BOLD+C.CYAN_L):
    print()
    print("  " + c(color, title))
    divider()

def ok(msg):   print("  " + c(C.BOLD+C.GREEN_L, "✓") + " " + c(C.WHITE, msg))
def err(msg):  print("  " + c(C.BOLD+C.RED,     "✗") + " " + c(C.WHITE, msg))
def info(msg): print("  " + c(C.BOLD+C.CYAN_L,  "·") + " " + c(C.GRAY,  msg))
def warn(msg): print("  " + c(C.BOLD+C.GOLD_L,  "!") + " " + c(C.GOLD_L,msg))
def ai(msg):   print("  " + c(C.BOLD+C.PURPLE_L, "𓂀") + " " + c(C.WHITE, msg))
