"""
THOTH Library — Smart writeup discovery at scale
4 discovery methods:
  1. Live search bar (type anything, instant results)
  2. Filter system (platform + difficulty + category)
  3. Session name auto-detect
  4. Room URL paste
"""

import json, os, sys, re, urllib.request, urllib.error
import termios, tty
from core.colors import c, C, header, ok, err, info, warn
from core import db

LIBRARY_INDEX_URL = "https://raw.githubusercontent.com/omar-tamerr/thoth-writeups/main/index.json"
LIBRARY_BASE_URL  = "https://raw.githubusercontent.com/omar-tamerr/thoth-writeups/main/writeups/"
CACHE_DIR         = os.path.expanduser("~/.thoth/library")
CACHE_INDEX       = os.path.join(CACHE_DIR, "index.json")
PAGE_SIZE         = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

DIFF_COLOR = {"Easy":C.GREEN_L,"Medium":C.GOLD_L,"Hard":C.RED,"Insane":C.BOLD+C.RED}
PLAT_COLOR = {"TryHackMe":C.CYAN_L,"HackTheBox":C.GREEN_L,
              "PicoCTF":C.PURPLE_L,"VulnHub":C.GOLD_L,"CTFTime":C.RED}

PLATFORMS   = ["All","TryHackMe","HackTheBox","PicoCTF","VulnHub","CTFTime"]
DIFFS       = ["All","Easy","Medium","Hard","Insane"]
CATEGORIES  = ["All","web","network","pwn","crypto","forensics","reversing","osint","misc"]

# ── URL patterns for room detection ──
URL_PATTERNS = [
    (r'tryhackme\.com/(?:room|r)/([a-zA-Z0-9_-]+)',   "TryHackMe"),
    (r'app\.hackthebox\.com/machines/([a-zA-Z0-9_-]+)',"HackTheBox"),
    (r'hackthebox\.eu/machines/([a-zA-Z0-9_-]+)',      "HackTheBox"),
    (r'hackthebox\.com/machines/([a-zA-Z0-9_-]+)',     "HackTheBox"),
    (r'picoctf\.org/problems/([a-zA-Z0-9_-]+)',        "PicoCTF"),
]

# ── IO ──
def _fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def _ensure_cache(): os.makedirs(CACHE_DIR, exist_ok=True)

def _load_index():
    try:
        with open(CACHE_INDEX) as f: return json.load(f)
    except: return None

def _save_index(d):
    _ensure_cache()
    with open(CACHE_INDEX,"w") as f: json.dump(d,f,indent=2)

def _load_writeup_cache(slug):
    try:
        with open(os.path.join(CACHE_DIR,f"{slug}.json")) as f:
            return json.load(f)
    except: return None

def _save_writeup_cache(slug,d):
    _ensure_cache()
    with open(os.path.join(CACHE_DIR,f"{slug}.json"),"w") as f:
        json.dump(d,f,indent=2)

def _get_index(force=False):
    if not force:
        local = _load_index()
        if local: return local, "cached"
    try:
        d = _fetch(LIBRARY_INDEX_URL)
        _save_index(d)
        return d, "online"
    except Exception as e:
        local = _load_index()
        if local: return local, "cached (offline)"
        return None, str(e)

def _get_writeup(slug):
    local = _load_writeup_cache(slug)
    if local: return local
    d = _fetch(LIBRARY_BASE_URL + slug + ".json")
    _save_writeup_cache(slug, d)
    return d

# ── Fuzzy scorer ──
def _score(w, query):
    if not query.strip(): return 1
    q      = query.lower()
    room   = w.get("room","").lower()
    slug   = w.get("slug","").lower()
    plat   = w.get("platform","").lower()
    diff   = w.get("difficulty","").lower()
    tags   = " ".join(w.get("tags",[])).lower()
    desc   = w.get("description","").lower()

    if q == slug:   return 100
    if q == room:   return 95
    score = 0
    words = q.split()
    for word in words:
        if word in slug:   score += 70
        if word in room:   score += 60
        if word in tags:   score += 30
        if word in plat:   score += 20
        if word in diff:   score += 15
        if word in desc:   score += 10
    return score

def _fuzzy_filter(writeups, query, plat_f="All", diff_f="All", cat_f="All"):
    results = []
    for w in writeups:
        # Apply filters
        if plat_f != "All" and w.get("platform","") != plat_f: continue
        if diff_f != "All" and w.get("difficulty","") != diff_f: continue
        if cat_f  != "All" and cat_f not in w.get("tags",[]): continue
        s = _score(w, query)
        if query.strip() == "" or s > 0:
            results.append((w, s))
    results.sort(key=lambda x: -x[1])
    return [w for w,_ in results]

# ── URL parser ──
def _parse_room_url(url):
    """Extract room name and platform from a THM/HTB URL."""
    for pattern, platform in URL_PATTERNS:
        m = re.search(pattern, url, re.IGNORECASE)
        if m:
            return m.group(1).lower().replace("-"," ").replace("_"," "), platform
    return None, None

def _slug_match(slug, url_room):
    """Match URL room name against writeup slug — handles wgelctf → THM-Wgel."""
    clean_slug = re.sub(r"^(THM|HTB|PicoCTF)[-_]","",slug,flags=re.IGNORECASE).lower()
    url_c  = url_room.lower().replace(" ","").replace("-","").replace("_","")
    slug_c = clean_slug.replace(" ","").replace("-","").replace("_","")
    if url_c == slug_c:                                   return 90
    if url_c in slug_c or slug_c in url_c:               return 60
    if url_c in slug.lower() or slug.lower() in url_c:   return 40
    return 0

def _find_by_url(writeups, url):
    """Find best matching writeup for a room URL."""
    room_name, platform = _parse_room_url(url)
    if not room_name:
        return None

    scored = []
    for w in writeups:
        if platform and w.get("platform","") != platform:
            continue
        # Try both fuzzy score and slug match — take the higher
        s1 = _score(w, room_name)
        s2 = _slug_match(w.get("slug",""), room_name)
        s  = max(s1, s2)
        if s > 0:
            scored.append((w, s))

    scored.sort(key=lambda x: -x[1])
    return scored[0][0] if scored else None

# ── Session name detector ──
def _detect_from_session(writeups, session):
    """Try to find a matching writeup from session name."""
    if not session: return None
    name = session.get("name","")

    # Strip common prefixes: THM-, HTB-, HTB_ etc
    clean = re.sub(r'^(THM|HTB|HTB|picoCTF|CTF)[-_]', '', name, flags=re.IGNORECASE)
    clean = clean.replace("-"," ").replace("_"," ").lower()

    if not clean: return None

    # Also try matching platform from prefix
    platform = None
    if re.match(r'^THM', name, re.IGNORECASE):    platform = "TryHackMe"
    elif re.match(r'^HTB', name, re.IGNORECASE):   platform = "HackTheBox"

    scored = []
    for w in writeups:
        if platform and w.get("platform","") != platform:
            continue
        s = _score(w, clean)
        if s > 20:  # higher threshold for auto-suggest
            scored.append((w, s))

    scored.sort(key=lambda x: -x[1])
    return scored[0][0] if scored else None

# ── Arrow key reader ──
def _read_key():
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A': return 'UP'
                if ch3 == 'B': return 'DOWN'
                if ch3 == 'C': return 'RIGHT'
                if ch3 == 'D': return 'LEFT'
            return 'ESC'
        if ch in ('\r','\n'):  return 'ENTER'
        if ch == '\x7f':       return 'BACKSPACE'
        if ch == '\x03':       raise KeyboardInterrupt
        if ch == '\t':         return 'TAB'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ── Interactive browser ──
def _run_browser(writeups, initial_query="", initial_plat="All",
                 initial_diff="All", initial_cat="All"):
    """
    Full interactive browser with:
    - Live search bar
    - Tab to toggle filter panel
    - Paginated results (10 per page)
    - Arrow keys to navigate
    """
    import shutil
    W = shutil.get_terminal_size((80,24)).columns

    query      = initial_query
    plat_f     = initial_plat
    diff_f     = initial_diff
    cat_f      = initial_cat
    selected   = 0
    page       = 0
    mode       = "search"   # search | filter
    filter_idx = 0           # which filter row is focused
    filter_col = 0           # which option in the filter row

    FILTERS = [
        ("Platform", PLATFORMS, "plat"),
        ("Difficulty",DIFFS,    "diff"),
        ("Category",  CATEGORIES,"cat"),
    ]

    def _get_filter(key):
        if key == "plat": return plat_f
        if key == "diff": return diff_f
        if key == "cat":  return cat_f

    def _set_filter(key, val):
        nonlocal plat_f, diff_f, cat_f
        if key == "plat": plat_f = val
        if key == "diff": diff_f = val
        if key == "cat":  cat_f  = val

    def _results():
        return _fuzzy_filter(writeups, query, plat_f, diff_f, cat_f)

    def _page_items(results):
        start = page * PAGE_SIZE
        return results[start:start+PAGE_SIZE], start

    def _render():
        nonlocal selected
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

        results           = _results()
        total             = len(results)
        total_pages       = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page_items, start = _page_items(results)

        # Clamp selected
        if selected >= len(page_items): selected = max(0, len(page_items)-1)

        # ── Header ──
        print(c(C.BOLD+C.WHITE, "  𓂀  THOTH Writeup Library"))
        print(c(C.GRAY, "  ─"*25))
        print()

        # ── Search bar ──
        search_indicator = c(C.BOLD+C.CYAN_L,"[SEARCH]") if mode=="search" else c(C.GRAY,"[search]")
        filter_indicator = c(C.BOLD+C.GOLD_L, "[FILTER]") if mode=="filter" else c(C.GRAY,"[filter]")
        print(f"  {search_indicator}  {c(C.GRAY,'Search: ')}"
              f"{c(C.BOLD+C.WHITE, query)}"
              f"{c(C.CYAN_L,'█') if mode=='search' else ''}"
              f"   {filter_indicator}")
        print()

        # ── Active filters ──
        filters_active = []
        if plat_f != "All": filters_active.append(c(PLAT_COLOR.get(plat_f,C.GRAY), plat_f))
        if diff_f != "All": filters_active.append(c(DIFF_COLOR.get(diff_f,C.GRAY), diff_f))
        if cat_f  != "All": filters_active.append(c(C.PURPLE_L, cat_f))
        if filters_active:
            print("  " + c(C.GRAY,"Filters: ") + "  ".join(filters_active))
            print()

        # ── Filter panel ──
        if mode == "filter":
            for fi, (fname, fopts, fkey) in enumerate(FILTERS):
                is_row = (fi == filter_idx)
                cur    = _get_filter(fkey)
                row_s  = c(C.BOLD+C.GOLD_L if is_row else C.GRAY, f"  {fname:<12}")
                opts_s = ""
                for oi, opt in enumerate(fopts):
                    is_opt = is_row and (oi == filter_col)
                    is_sel = (opt == cur)
                    if is_opt:
                        opts_s += c(C.BOLD+C.WHITE, f"[{opt}]") + " "
                    elif is_sel:
                        opts_s += c(C.BOLD+C.CYAN_L, opt) + " "
                    else:
                        opts_s += c(C.GRAY, opt) + " "
                print(f"  {row_s}  {opts_s}")
            print()
            print(c(C.GRAY,"  ↑↓ switch filter row  ·  ←→ change value  ·  Tab back to search  ·  q quit"))
            print()

        # ── Results ──
        print("  " + c(C.GRAY,
            "   " + "ROOM".ljust(22) +
            "PLATFORM".ljust(13) +
            "DIFF".ljust(8) +
            "TAGS"))
        print("  " + c(C.GRAY, "  "+"─"*58))

        if not page_items:
            print()
            print(c(C.GRAY, "  No writeups match your search."))
            if query:
                print(c(C.GRAY, f"  Try a shorter search or clear filters."))
        else:
            for i, w in enumerate(page_items):
                is_sel   = (i == selected)
                prefix   = c(C.BOLD+C.CYAN_L,"  ►") if is_sel else "   "
                room     = w.get("room","")[:20]
                plat     = w.get("platform","")[:11]
                diff     = w.get("difficulty","")[:6]
                tags     = ", ".join(w.get("tags",[])[:2])
                auth     = w.get("author","")
                pc       = PLAT_COLOR.get(w.get("platform",""),C.GRAY)
                dc       = DIFF_COLOR.get(w.get("difficulty",""),C.GRAY)
                auth_s   = c(C.GRAY, f" ✎{auth}") if auth and auth != "Omar Tamer" else ""

                if is_sel:
                    print(f"  {prefix} {c(C.BOLD+C.WHITE,room.ljust(22))}"
                          f"{c(C.BOLD+pc,plat.ljust(13))}"
                          f"{c(C.BOLD+dc,diff.ljust(8))}"
                          f"{c(C.WHITE,tags)}{auth_s}")
                else:
                    print(f"  {prefix} {c(C.WHITE,room.ljust(22))}"
                          f"{c(pc,plat.ljust(13))}"
                          f"{c(dc,diff.ljust(8))}"
                          f"{c(C.GRAY,tags)}{auth_s}")

        # ── Pagination ──
        print()
        if total_pages > 1:
            prev_s = c(C.WHITE,"← prev") if page > 0 else c(C.GRAY,"← prev")
            next_s = c(C.WHITE,"next →") if page < total_pages-1 else c(C.GRAY,"next →")
            print(f"  {prev_s}   "
                  f"{c(C.GRAY,f'page {page+1}/{total_pages}  ({total} rooms)')}   "
                  f"{next_s}")
        else:
            print(c(C.GRAY, f"  {total} writeup(s) found"))

        # ── Selected item detail ──
        if page_items and 0 <= selected < len(page_items):
            sel  = page_items[selected]
            desc = sel.get("description","")
            slug = sel.get("slug","")
            print()
            if desc: print(c(C.GRAY, f"  {desc[:70]}"))
            print(c(C.GRAY,f"  slug: ")+c(C.DIM+C.WHITE,slug)+
                  c(C.GRAY,"  ·  Enter to load"))

        if mode == "search":
            print()
            print(c(C.GRAY,"  Type to search  ·  Tab for filters  ·  ↑↓ navigate  ·  ←→ pages  ·  q quit"))

        sys.stdout.flush()

    # ── Main loop ──
    try:
        while True:
            _render()
            key = _read_key()
            results           = _results()
            total             = len(results)
            total_pages       = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
            page_items, start = _page_items(results)

            if mode == "search":
                if key == 'UP':
                    selected = max(0, selected-1)
                elif key == 'DOWN':
                    selected = min(len(page_items)-1, selected+1) if page_items else 0
                elif key == 'LEFT':
                    if page > 0: page -= 1; selected = 0
                elif key == 'RIGHT':
                    if page < total_pages-1: page += 1; selected = 0
                elif key == 'ENTER':
                    sys.stdout.write("\033[2J\033[H")
                    sys.stdout.flush()
                    if page_items and 0 <= selected < len(page_items):
                        return page_items[selected]
                    return None
                elif key == 'TAB':
                    mode = "filter"; filter_idx = 0; filter_col = 0
                elif key == 'BACKSPACE':
                    query = query[:-1]; page = 0; selected = 0
                elif key in ('QUIT','q','ESC'):
                    sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
                    return None
                elif len(key) == 1 and key.isprintable():
                    query += key; page = 0; selected = 0

            elif mode == "filter":
                if key == 'UP':
                    filter_idx = max(0, filter_idx-1); filter_col = 0
                elif key == 'DOWN':
                    filter_idx = min(len(FILTERS)-1, filter_idx+1); filter_col = 0
                elif key == 'LEFT':
                    filter_col = max(0, filter_col-1)
                elif key == 'RIGHT':
                    _, fopts, fkey = FILTERS[filter_idx]
                    filter_col = min(len(fopts)-1, filter_col+1)
                elif key == 'ENTER':
                    _, fopts, fkey = FILTERS[filter_idx]
                    _set_filter(fkey, fopts[filter_col])
                    page = 0; selected = 0
                elif key == 'TAB' or key == 'ESC':
                    mode = "search"
                elif key in ('QUIT','q'):
                    sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
                    return None

    except KeyboardInterrupt:
        sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
        return None

# ── Load into session ──
def _load_into_session(writeup, session):
    def _conv(stages):
        out = {}
        for stage, hints in stages.items():
            paras = []
            for k in ("nudge","clue","near_solve"):
                if hints.get(k): paras.append(hints[k])
            if paras: out[stage] = paras
        return out

    db.profile_set(f"writeup.{session['name']}", json.dumps({
        "url":       writeup.get("full_writeup_url",""),
        "stages":    _conv(writeup.get("stages",{})),
        "key_facts": writeup.get("key_facts",[]),
        "full_text": json.dumps(writeup.get("stages",{})),
        "locked":    True,
        "source":    "library",
        "author":    writeup.get("author","Omar Tamer"),
        "room":      writeup.get("room",""),
    }))
    db.session_update(session["name"], writeup=f"library:{writeup['slug']}")

def _confirm_and_load(writeup, session):
    print()
    print(c(C.BOLD+C.WHITE, f"  Found: {writeup['room']}") +
          c(C.GRAY, f"  ({writeup.get('platform','')} · {writeup.get('difficulty','')})"))
    print(c(C.GRAY, f"  Author: {writeup.get('author','Omar Tamer')}"))
    print()
    if not session:
        warn("No active session.")
        print(c(C.GRAY,"  Start one first: ") + c(C.WHITE,"thoth new"))
        print(c(C.GRAY,"  Then: ") + c(C.WHITE,f"thoth library --load {writeup['slug']}"))
        print()
        return

    try:
        yn = input(c(C.GRAY, f"  Load into '{session['name']}'? [Y/n]: ")).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(); return

    if yn == "n":
        info("Cancelled."); print(); return

    info("Fetching writeup...")
    try:
        full = _get_writeup(writeup["slug"])
    except Exception as e:
        err(str(e)); return

    _load_into_session(full, session)
    print()
    ok(f"Writeup loaded: {full.get('room','')}")
    info(f"Stages : {', '.join(full.get('stages',{}).keys())}")
    print()
    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth hint") +
          c(C.GRAY," — hints now guided by this writeup."))
    print()
    db.log_add(session["name"], "library --load", writeup["slug"])

# ── Main command ──
def cmd_library(args):
    s = db.get_active()

    # ── --update ──
    if "--update" in args:
        header("Library Update"); print()
        info("Fetching from GitHub...")
        index, src = _get_index(force=True)
        if not index: err(f"Update failed: {src}"); return
        writeups = index.get("writeups",[])
        print()
        ok(f"{len(writeups)} writeups available")
        info(f"Cached to {CACHE_DIR}")
        print()
        for w in writeups[-3:]:
            print("  " + c(C.WHITE, w.get("room","")[:22].ljust(24)) +
                  c(PLAT_COLOR.get(w.get("platform",""),C.GRAY), w.get("platform","")[:12].ljust(13)) +
                  c(DIFF_COLOR.get(w.get("difficulty",""),C.GRAY), w.get("difficulty","")))
        print()
        print(c(C.GRAY,"  Run: ") + c(C.WHITE,"thoth library") + c(C.GRAY," to browse"))
        print(); return

    # ── --url : Room URL paste ──
    if "--url" in args:
        idx = args.index("--url")
        url = " ".join(args[idx+1:]).strip() if idx+1 < len(args) else ""
        if not url:
            err("Usage: thoth library --url <room-url>")
            print(c(C.GRAY,"  Example: thoth library --url https://tryhackme.com/room/wgelctf"))
            return

        index, _ = _get_index()
        if not index: err("Library not available. Run thoth library --update"); return

        writeups = index.get("writeups",[])
        match    = _find_by_url(writeups, url)

        header("Room URL Detection"); print()

        if not match:
            room_name, platform = _parse_room_url(url)
            if room_name:
                warn(f"No writeup found for '{room_name}' ({platform or 'unknown platform'}).")
                print(c(C.GRAY,"  This room may not be in the library yet."))
                print(c(C.GRAY,"  Request it: ") + c(C.WHITE,"github.com/omar-tamerr/thoth-writeups/issues"))
            else:
                err("Could not parse room name from URL.")
                print(c(C.GRAY,"  Supported: tryhackme.com/room/... · app.hackthebox.com/machines/..."))
            print(); return

        _confirm_and_load(match, s)
        return

    # ── --load : Fuzzy name load ──
    if "--load" in args:
        idx   = args.index("--load")
        query = " ".join(args[idx+1:]).strip() if idx+1 < len(args) else ""
        if not query:
            err("Usage: thoth library --load <room name or slug>"); return

        if not s:
            err("No active session. Run thoth new or thoth resume first."); return

        index, _ = _get_index()
        if not index: err("Library not available. Run thoth library --update"); return

        writeups = index.get("writeups",[])
        results  = _fuzzy_filter(writeups, query)

        if not results:
            err(f"No writeup found matching '{query}'.")
            print(c(C.GRAY,"  Browse all: ") + c(C.WHITE,"thoth library"))
            return

        match = results[0]

        # If multiple close matches, show top 3
        if len(results) > 1 and _score(results[0],query) < 80:
            print()
            print(c(C.GRAY,"  Multiple matches found:"))
            for i,w in enumerate(results[:3],1):
                print(c(C.GRAY,f"  [{i}] ")+c(C.WHITE,w.get("room","")[:20].ljust(22))+
                      c(PLAT_COLOR.get(w.get("platform",""),C.GRAY),w.get("platform","")))
            print()
            try:
                pick = input(c(C.GRAY,"  Choose [1]: ")).strip()
                idx2 = int(pick)-1 if pick else 0
                match = results[min(idx2, len(results)-1)]
            except (ValueError, KeyboardInterrupt):
                match = results[0]

        header(f"Loading — {match['room']}"); print()
        info("Fetching writeup...")
        try:
            writeup = _get_writeup(match["slug"])
        except Exception as e:
            err(str(e)); return

        _load_into_session(writeup, s)
        print()
        ok(f"Writeup loaded: {writeup.get('room','')}")
        info(f"Platform   : {writeup.get('platform','')}")
        info(f"Difficulty : {writeup.get('difficulty','')}")
        info(f"Author     : {writeup.get('author','Omar Tamer')}")
        info(f"Stages     : {', '.join(writeup.get('stages',{}).keys())}")
        print()
        print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth hint") +
              c(C.GRAY," — hints now guided by this writeup."))
        print()
        db.log_add(s["name"],"library --load", match["slug"])
        return

    # ── --search : Plain text search ──
    if "--search" in args:
        idx   = args.index("--search")
        query = " ".join(args[idx+1:]).strip() if idx+1 < len(args) else ""
        index, src = _get_index()
        if not index: err(f"Library not available: {src}"); return

        writeups = index.get("writeups",[])
        results  = _fuzzy_filter(writeups, query)
        total    = len(results)
        pages    = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)

        # Try to get page number
        page = 0
        if "--page" in args:
            pi = args.index("--page")
            try: page = int(args[pi+1])-1
            except: pass

        header(f"Library Search — {query or 'all'}")
        print()
        info(f"{total} result(s)  ·  page {page+1}/{pages}  ·  {src}")
        print()

        if not results:
            warn(f"No writeups found matching '{query}'.")
            print(c(C.GRAY,"  Browse: ") + c(C.WHITE,"thoth library"))
            return

        print("  " + c(C.GRAY,
              "    "+"ROOM".ljust(22)+"PLATFORM".ljust(13)+"DIFF".ljust(8)+"TAGS"))
        print("  " + c(C.GRAY,"  "+"─"*58))

        start = page*PAGE_SIZE
        for i,w in enumerate(results[start:start+PAGE_SIZE],start+1):
            print(
                c(C.GRAY,f"  [{i}] ")+
                c(C.BOLD+C.WHITE, w.get("room","")[:20].ljust(22))+
                c(PLAT_COLOR.get(w.get("platform",""),C.GRAY),w.get("platform","")[:11].ljust(13))+
                c(DIFF_COLOR.get(w.get("difficulty",""),C.GRAY),w.get("difficulty","")[:6].ljust(8))+
                c(C.GRAY,", ".join(w.get("tags",[])[:3]))
            )

        print()
        if pages > 1:
            print(c(C.GRAY,f"  Page {page+1}/{pages}  ·  ") +
                  c(C.WHITE,f"thoth library --search {query} --page {page+2}") +
                  c(C.GRAY," for next page"))
        print()
        print(c(C.GRAY,"  Load: ") + c(C.WHITE,"thoth library --load <room-name>"))
        print()
        return

    # ── Default: interactive browser ──
    index, src = _get_index()

    if not index:
        warn("Library not available offline.")
        print(c(C.GRAY,"  Run: ") + c(C.WHITE,"thoth library --update"))
        print(); return

    writeups = index.get("writeups",[])
    if not writeups:
        warn("Library is empty.")
        print(c(C.GRAY,"  Run: ") + c(C.WHITE,"thoth library --update"))
        return

    # ── Auto-detect from session name ──
    if s:
        auto = _detect_from_session(writeups, s)
        if auto:
            print()
            print(c(C.BOLD+C.PURPLE_L,"  𓂀 Auto-detected writeup from session name:"))
            print()
            print("  " +
                  c(C.BOLD+C.WHITE, auto.get("room","")[:22].ljust(24)) +
                  c(PLAT_COLOR.get(auto.get("platform",""),C.GRAY),
                    auto.get("platform","")[:12].ljust(13)) +
                  c(DIFF_COLOR.get(auto.get("difficulty",""),C.GRAY),
                    auto.get("difficulty","")))
            print()
            try:
                yn = input(c(C.GRAY,"  Load this? [Y/n/b(rowse)]: ")).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print(); yn = "b"

            if yn == "" or yn == "y":
                info("Fetching writeup...")
                try:
                    full = _get_writeup(auto["slug"])
                    _load_into_session(full, s)
                    print()
                    ok(f"Writeup loaded: {full.get('room','')}")
                    info(f"Stages: {', '.join(full.get('stages',{}).keys())}")
                    print()
                    print(c(C.GRAY,"  Run ") + c(C.WHITE,"thoth hint") +
                          c(C.GRAY," for guided hints."))
                    print()
                    db.log_add(s["name"],"library auto-load", auto["slug"])
                    return
                except Exception as e:
                    err(str(e)); return
            elif yn == "b":
                pass  # fall through to browser
            else:
                print(); return

    # Not a real TTY — plain list
    if not sys.stdin.isatty():
        header("THOTH Writeup Library"); print()
        info(f"{len(writeups)} writeups  ·  {src}")
        print()
        print(c(C.GRAY,"  Use: thoth library --search <keyword>"))
        print(c(C.GRAY,"       thoth library --load <room-name>"))
        print(c(C.GRAY,"       thoth library --url <room-url>"))
        print(); return

    # Launch interactive browser
    chosen = _run_browser(writeups)

    if not chosen:
        print()
        info("No writeup selected.")
        print(); return

    _confirm_and_load(chosen, s)
