#!/usr/bin/env python3
"""Download every course file from CyberLearn (the HES-SO Moodle used by HEG Genève).

    python heg.py login                  open a browser window, sign in yourself, session is saved
    python heg.py courses                list the courses you are enrolled in
    python heg.py download --out DIR     download files + page texts of all courses (re-run = only new files)
    python heg.py notebooklm-pack        copy the NotebookLM-friendly files into one flat folder per course
    python heg.py notebooklm-upload      (optional, unofficial) push those files into NotebookLM notebooks

Your password is never read or stored: you type it in the browser window. Only the session cookie is
kept, in ~/.heg-downloader/ (outside this repo). See README.md for the full guide.
"""
import argparse, json, os, re, shutil, sys, time, urllib.parse
from pathlib import Path

BASE = os.environ.get("HEG_BASE_URL", "https://cyberlearn.hes-so.ch").rstrip("/")
HOST = urllib.parse.urlparse(BASE).hostname
STATE = Path.home() / ".heg-downloader"
COOKIE = STATE / "cookie.json"
CONFIG = STATE / "config.json"
DEFAULT_OUT = Path.home() / "HEG-Materials"

TEXT_MODS = ("assign", "page", "choicegroup", "groupselect", "choice", "workshop", "feedback", "book", "lesson",
             "quiz", "questionnaire", "scheduler", "glossary", "data", "wiki", "h5pactivity", "lti",
             "bigbluebuttonbn", "attendance", "forum", "ratingallocate", "organizer")
# what NotebookLM accepts as a file source (check the current list in docs/notebooklm.md)
NLM_EXT = {".pdf", ".txt", ".md", ".docx", ".pptx"}
NLM_MAX_SOURCES = 50          # free plan; paid plans allow more
NLM_MAX_BYTES = 200 * 1024 * 1024


class SessionExpired(Exception):
    pass


def need(mod, pip_name=None):
    try:
        return __import__(mod)
    except ImportError:
        sys.exit(f"Missing Python package '{pip_name or mod}'. Activate your venv and run: pip install -r requirements.txt")


# ---------------------------------------------------------------- session

def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def save_config(**kw):
    STATE.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({**load_config(), **kw}, indent=1))


def session():
    requests = need("requests")
    need("bs4", "beautifulsoup4")
    if not COOKIE.exists():
        sys.exit("Not signed in yet. Run:  python heg.py login")
    s = requests.Session()
    for k, v in json.loads(COOKIE.read_text()).items():
        s.cookies.set(k, v, domain=HOST)
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
    return s


def get(s, url, **kw):
    import requests
    url = urllib.parse.urljoin(BASE + "/", url)
    for attempt in range(3):
        try:
            r = s.get(url, timeout=60, **kw)
            if "login/index.php" in r.url or "eduid.ch" in r.url or "/auth/" in r.url:
                raise SessionExpired()
            return r
        except requests.RequestException:
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"network error on {url}")


def cmd_login(a):
    need("playwright")
    from playwright.sync_api import sync_playwright
    STATE.mkdir(parents=True, exist_ok=True)
    check = "() => !!(window.M && M.cfg && parseInt(M.cfg.userId) > 1 && !document.body.classList.contains('notloggedin'))"
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(STATE / "browser_profile"), headless=False,
                                                   viewport={"width": 1100, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"{BASE}/my/courses.php")
        print("A browser window opened. Sign in with your SWITCH edu-ID (HES-SO) there.\n"
              "Waiting up to 15 minutes; do not close the window...", flush=True)
        deadline, last = time.time() + 900, 0
        while time.time() < deadline:
            ok = False
            for pg in ctx.pages:
                try:
                    if HOST in pg.url and pg.evaluate(check):
                        ok = True
                        break
                except Exception:
                    pass  # page is navigating (edu-ID redirects)
            if ok:
                break
            if time.time() - last > 20:
                last = time.time()
                print("  still waiting for sign-in...", flush=True)
            time.sleep(2)
        else:
            sys.exit("Timed out waiting for sign-in. Run the command again.")
        cookies = {c["name"]: c["value"] for c in ctx.cookies() if HOST in c["domain"]}
        COOKIE.write_text(json.dumps(cookies))
        COOKIE.chmod(0o600)
        ctx.close()
    print(f"Signed in. Session saved to {COOKIE}")
    print("Next: python heg.py courses")


def cmd_set_cookie(a):
    """Fallback without Playwright: paste the MoodleSession cookie copied from your browser."""
    STATE.mkdir(parents=True, exist_ok=True)
    raw = a.value.strip()
    cookies = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k] = v
    if not cookies:
        cookies = {"MoodleSession": raw}
    COOKIE.write_text(json.dumps(cookies))
    COOKIE.chmod(0o600)
    print(f"Saved {len(cookies)} cookie(s). Test with: python heg.py courses")


# ---------------------------------------------------------------- courses

def enrolled_courses(s):
    from bs4 import BeautifulSoup
    html = get(s, f"{BASE}/my/courses.php").text
    found = {}
    m = re.search(r'"sesskey":"(\w+)"', html)
    if m:
        for cls in ("all", "hidden"):
            method = "core_course_get_enrolled_courses_by_timeline_classification"
            r = s.post(f"{BASE}/lib/ajax/service.php?sesskey={m[1]}&info={method}", timeout=60, json=[{
                "index": 0, "methodname": method,
                "args": {"offset": 0, "limit": 0, "classification": cls, "sort": "fullname",
                         "customfieldname": "", "customfieldvalue": ""}}])
            try:
                j = r.json()[0]
            except Exception:
                continue
            if not j.get("error"):
                for c in j["data"]["courses"]:
                    found[c["id"]] = c["fullname"]
    if not found:  # fallback: scrape the links on the dashboard
        for a_ in BeautifulSoup(html, "html.parser").select("a[href*='course/view.php?id=']"):
            cid = int(re.search(r"id=(\d+)", a_["href"]).group(1))
            found.setdefault(cid, a_.get_text(" ", strip=True) or f"course-{cid}")
    return [{"id": k, "name": v} for k, v in sorted(found.items(), key=lambda kv: kv[1].lower())]


def cmd_courses(a):
    try:
        courses = enrolled_courses(session())
    except SessionExpired:
        sys.exit("Session expired. Run: python heg.py login")
    if not courses:
        sys.exit("No courses found. Are you signed in? Try: python heg.py login")
    for c in courses:
        print(f"{c['id']:>7}  {c['name']}")
    print(f"\n{len(courses)} courses. Use --course ID (repeatable) or --exclude ID with 'download' to pick.")


# ---------------------------------------------------------------- download

def clean(s, limit=120):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s).strip()
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:limit] or "unnamed"


def safe_filename(name):
    p = Path(clean(name, 250))
    return clean(p.stem, 100) + p.suffix[:12]


def text_of(el):
    from bs4 import BeautifulSoup
    if el is None:
        return ""
    el = BeautifulSoup(str(el), "html.parser")
    for x in el.select(".accesshide, .visually-hidden, script, style, .activity-navigation, #jump-to-activity"):
        x.decompose()
    for a in el.select("a[href]"):
        h = a["href"]
        if h.startswith("http") and "/mod/" not in h and "/user/" not in h and a.get_text(strip=True):
            a.replace_with(f"{a.get_text(strip=True)} <{h}>")
    t = el.get_text("\n", strip=True)
    t = re.split(r"\n(?:◀︎|Jump to activity|Aller à…|Aller vers l’activité)", t)[0]
    return re.sub(r"\n{3,}", "\n\n", t)


def fname_from(r):
    cd = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd) or re.search(r'filename="?([^";]+)', cd)
    if m:
        return urllib.parse.unquote(m.group(1))
    return urllib.parse.unquote(r.url.split("?")[0].rsplit("/", 1)[-1]) or "file"


def file_links(el):
    out = [a["href"] for a in el.select("a[href*='pluginfile.php'], a[href*='/file.php/']")]
    out += [i["src"] for i in el.select("img[src*='pluginfile.php']")]
    return [h for h in dict.fromkeys(out) if "/user/icon" not in h and "/theme/" not in h]


def main_region(soup):
    return soup.select_one("#region-main") or soup.select_one("[role=main]") or soup.body


class Course:
    """Download state of one course: target folder + manifest of what was already fetched."""

    def __init__(self, root):
        self.root = root
        self.mf = root / ".heg-manifest.json"
        try:
            self.manifest = json.loads(self.mf.read_text())
        except Exception:
            self.manifest = {}
        self.new, self.errors = [], []

    def save_manifest(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.mf.write_text(json.dumps(self.manifest, indent=0, ensure_ascii=False))

    def save_file(self, s, url, dest_dir):
        """Download one file unless we already have it. Returns the response if the URL was a page, not a file."""
        r = get(s, url, stream=True)
        if "text/html" in r.headers.get("content-type", "") and "pluginfile" not in r.url:
            return r
        name = safe_filename(fname_from(r))
        size = int(r.headers.get("content-length") or 0)
        p = dest_dir / name
        rel = p.relative_to(self.root).as_posix()
        have = self.manifest.get(rel, p.stat().st_size if p.exists() else None)
        if have is not None:
            if not size or size == have:
                r.close()
                return None
            # same name, different content: the teacher replaced the file. Keep both.
            p = dest_dir / f"{Path(name).stem} (updated {time.strftime('%d-%m')}){Path(name).suffix}"
            rel = p.relative_to(self.root).as_posix()
            if rel in self.manifest:
                r.close()
                return None
        p.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(p, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
                written += len(chunk)
        self.manifest[rel] = written
        self.new.append(rel)
        print(f"    + {rel}", flush=True)
        return None


def crawl_course(s, c, root, participants):
    from bs4 import BeautifulSoup
    cs = Course(root)
    notes = [f"# {c['name']}\n", f"CyberLearn: {BASE}/course/view.php?id={c['id']}\n"]
    soup = BeautifulSoup(get(s, f"{BASE}/course/view.php?id={c['id']}").text, "html.parser")
    try:
        for sec in soup.select("li.section.course-section") or soup.select("li.section"):
            name_el = sec.select_one(".sectionname") or sec.select_one("h3")
            sname = clean(name_el.get_text(strip=True)) if name_el else f"Section {sec.get('data-number', '?')}"
            notes.append(f"\n## {sname}\n")
            sdir = root / sname
            summ = sec.select_one(".summarytext, .section-summary, .summary")
            if summ:
                st = text_of(summ)
                if st:
                    notes.append(st + "\n")
                for h in file_links(summ):
                    try:
                        cs.save_file(s, h, sdir)
                    except SessionExpired:
                        raise
                    except Exception as e:
                        cs.errors.append(f"summary {sname}: {e}")
            for act in sec.select("li.activity"):
                m = re.search(r"modtype_(\w+)", " ".join(act.get("class", [])))
                mod = m.group(1) if m else "?"
                aname = clean(text_of(act.select_one(".instancename"))) if act.select_one(".instancename") else ""
                a = act.select_one(".activityname a, a.aalink")
                href = a["href"] if a else None
                dates = text_of(act.select_one("[data-region=activity-dates]"))
                desc = text_of(act.select_one(".activity-altcontent, .contentafterlink, .description"))
                try:
                    if mod == "label":
                        notes.append(f"- [text] {desc or aname}\n")
                        for h in file_links(act):
                            cs.save_file(s, h, sdir)
                        continue
                    notes.append(f"- [{mod}] **{aname}** {('- ' + dates.replace(chr(10), ' ')) if dates else ''}\n")
                    if desc:
                        notes.append("  > " + desc.replace("\n", "\n  > ") + "\n")
                    if not href:
                        continue
                    if mod == "resource":
                        rr = cs.save_file(s, href + ("&" if "?" in href else "?") + "redirect=1", sdir)
                        if rr is not None:  # the resource page embeds the file instead of redirecting
                            for h in file_links(main_region(BeautifulSoup(rr.text, "html.parser"))):
                                cs.save_file(s, h, sdir)
                    elif mod == "folder":
                        for h in file_links(main_region(BeautifulSoup(get(s, href).text, "html.parser"))):
                            cs.save_file(s, h, sdir / (aname or "folder"))
                    elif mod == "url":
                        rr = get(s, href + ("&" if "?" in href else "?") + "redirect=1", allow_redirects=False)
                        loc = rr.headers.get("location") or ""
                        if not loc:
                            u = BeautifulSoup(rr.text, "html.parser").select_one(".urlworkaround a, #region-main a[href^=http]")
                            loc = u["href"] if u else href
                        notes.append(f"  link: {loc}\n")
                    elif mod in TEXT_MODS:
                        s2 = BeautifulSoup(get(s, href).text, "html.parser")
                        mr = main_region(s2)
                        for h in file_links(mr):
                            cs.save_file(s, h, sdir / (aname or mod))
                        notes.append("  <details>\n\n  " + text_of(mr)[:6000].replace("\n", "\n  ") + "\n  </details>\n")
                        if mod == "forum":
                            seen = set()
                            for d in s2.select("a[href*='discuss.php?d=']"):
                                dh = d["href"].split("#")[0].split("&")[0]
                                if dh in seen or len(seen) >= 25:
                                    continue
                                seen.add(dh)
                                m3 = main_region(BeautifulSoup(get(s, dh).text, "html.parser"))
                                title = m3.select_one("h3, h2")
                                for h in file_links(m3):
                                    cs.save_file(s, h, sdir / (aname or "forum"))
                                notes.append(f"\n  ### Post: {clean(title.get_text(strip=True)) if title else dh}\n  "
                                             + text_of(m3)[:4000].replace("\n", "\n  ") + "\n")
                except SessionExpired:
                    raise
                except Exception as e:
                    cs.errors.append(f"{mod} {aname}: {e}")
        if participants:
            tbl = BeautifulSoup(get(s, f"{BASE}/user/index.php?id={c['id']}&perpage=5000").text, "html.parser").select_one("table#participants")
            if tbl:
                rows = [" | ".join(t for t in (td.get_text(" ", strip=True) for td in tr.select("th, td")) if t)
                        for tr in tbl.select("tbody tr")]
                root.mkdir(parents=True, exist_ok=True)
                (root / "_participants.txt").write_text("\n".join(r for r in rows if r))
    finally:
        root.mkdir(parents=True, exist_ok=True)
        (root / "_course-notes.md").write_text("".join(notes))
        cs.save_manifest()
    return cs


def cmd_download(a):
    cfg = load_config()
    out = Path(a.out or cfg.get("out") or DEFAULT_OUT).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    save_config(out=str(out))
    s = session()
    try:
        courses = enrolled_courses(s)
        if a.course:
            courses = [c for c in courses if str(c["id"]) in a.course]
        courses = [c for c in courses if str(c["id"]) not in (a.exclude or [])]
        if not courses:
            sys.exit("No matching courses. Run 'python heg.py courses' to see the ids.")
        names = {}
        for c in courses:  # two courses with the same title must not share a folder
            n = clean(c["name"])
            names[n] = names.get(n, 0) + 1
            c["folder"] = n if names[n] == 1 else f"{n} [{c['id']}]"
        print(f"Saving to {out}\n")
        total_new = total_err = 0
        for c in courses:
            print(f"== {c['name']}", flush=True)
            cs = crawl_course(s, c, out / c["folder"], a.participants)
            total_new += len(cs.new)
            total_err += len(cs.errors)
            (out / c["folder"] / "_errors.txt").write_text("\n".join(cs.errors))
            print(f"   {len(cs.new)} new files" + (f", {len(cs.errors)} errors (see _errors.txt)" if cs.errors else ""), flush=True)
    except SessionExpired:
        sys.exit("\nSession expired. Run 'python heg.py login' and then the same command again "
                 "(files already downloaded are kept and skipped).")
    print(f"\nDone: {total_new} new files, {total_err} errors. Folder: {out}")


# ---------------------------------------------------------------- NotebookLM helpers

def course_dirs(src):
    return sorted(d for d in src.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))


def nlm_candidates(cdir):
    """(file, flat_name) for every NotebookLM-compatible file in a course folder."""
    keep, skipped = [], []
    for p in sorted(cdir.rglob("*")):
        if not p.is_file() or p.name.startswith((".", "_errors", "_participants")):
            continue
        rel = p.relative_to(cdir)
        flat = " - ".join(rel.parts) if len(rel.parts) > 1 else rel.name
        (keep if p.suffix.lower() in NLM_EXT and p.stat().st_size <= NLM_MAX_BYTES else skipped).append((p, flat))
    return keep, skipped


def cmd_pack(a):
    src = Path(a.src or load_config().get("out") or DEFAULT_OUT).expanduser()
    dest = Path(a.dest).expanduser() if a.dest else src.parent / (src.name + "-notebooklm")
    if not src.exists():
        sys.exit(f"{src} does not exist. Run 'download' first.")
    for cdir in course_dirs(src):
        keep, skipped = nlm_candidates(cdir)
        out = dest / cdir.name
        out.mkdir(parents=True, exist_ok=True)
        for p, flat in keep:
            shutil.copy2(p, out / clean(flat, 200))
        (out / "_not-included.txt").write_text("\n".join(f"{p.relative_to(cdir)}" for p, _ in skipped))
        warn = f"  WARNING: {len(keep)} files > {NLM_MAX_SOURCES}, the free plan limit per notebook; use Plus or split by topic" if len(keep) > NLM_MAX_SOURCES else ""
        print(f"{cdir.name}: {len(keep)} files for NotebookLM, {len(skipped)} left out{warn}")
    print(f"\nReady to drag into NotebookLM: {dest}")


def cmd_nlm_upload(a):
    """Optional and unofficial: uses the 'notebooklm' CLI from the notebooklm-py package (see docs/notebooklm.md)."""
    import subprocess
    cli = a.cli or shutil.which("notebooklm")
    if not cli:
        sys.exit("The 'notebooklm' CLI is not installed. Follow docs/notebooklm.md (option B) or use the manual drag-and-drop.")
    src = Path(a.src or load_config().get("out") or DEFAULT_OUT).expanduser()

    def run(*args):
        r = subprocess.run([cli, *args], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def books():
        rc, out, err = run("list", "--json")
        if rc:
            sys.exit(f"'notebooklm list' failed. Sign in first with: notebooklm login\n{err.strip()[-300:]}")
        return {n["title"]: n["id"] for n in json.loads(out)["notebooks"]}

    def norm(t):
        return re.sub(r"[^a-z0-9]+", "", re.sub(r"\.(pdf|docx|pptx|md|txt)$", "", t.lower()))

    have_books = books()
    for cdir in course_dirs(src):
        if a.only and not any(o.lower() in cdir.name.lower() for o in a.only):
            continue
        title = f"{a.prefix}{cdir.name}"
        keep, _ = nlm_candidates(cdir)
        if not keep:
            continue
        if title not in have_books and not a.dry:
            run("create", title)
            have_books = books()
        nid = have_books.get(title)
        existing = set()
        if nid:
            rc, out, _ = run("source", "list", "--notebook", nid, "--json")
            try:
                existing = {norm(x["title"]) for x in json.loads(out)["sources"]}
            except Exception:
                pass  # some versions fail on unusual source types; worst case we re-add a duplicate
        todo = [(p, f) for p, f in keep if norm(f) not in existing and norm(p.name) not in existing]
        print(f"== {title}: {len(todo)} to add ({len(keep) - len(todo)} already there)", flush=True)
        if len(existing) + len(todo) > NLM_MAX_SOURCES:
            print(f"   note: more than {NLM_MAX_SOURCES} sources; the free plan will reject the extras")
        for p, flat in todo:
            if a.dry:
                print(f"   would add {flat}")
                continue
            rc, out, err = run("source", "add", str(p), "--notebook", nid, "--title", flat, "--json")
            print(f"   {'+' if rc == 0 else 'FAILED'} {flat}" + ("" if rc == 0 else f": {(err or out).strip()[-160:]}"), flush=True)


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="open a browser to sign in and save the session").set_defaults(fn=cmd_login)
    p = sub.add_parser("set-cookie", help="save a MoodleSession cookie copied from your browser (no Playwright needed)")
    p.add_argument("value")
    p.set_defaults(fn=cmd_set_cookie)
    sub.add_parser("courses", help="list your courses and their ids").set_defaults(fn=cmd_courses)
    p = sub.add_parser("download", help="download files and page texts")
    p.add_argument("--out", help=f"destination folder (default: last used, else {DEFAULT_OUT})")
    p.add_argument("--course", action="append", help="only this course id (repeatable)")
    p.add_argument("--exclude", action="append", help="skip this course id (repeatable)")
    p.add_argument("--participants", action="store_true", help="also save the participant list of each course")
    p.set_defaults(fn=cmd_download)
    p = sub.add_parser("notebooklm-pack", help="copy NotebookLM-compatible files into one flat folder per course")
    p.add_argument("--src", help="folder produced by 'download'")
    p.add_argument("--dest", help="where to put the packed folders (default: <src>-notebooklm)")
    p.set_defaults(fn=cmd_pack)
    p = sub.add_parser("notebooklm-upload", help="(optional, unofficial) create one notebook per course and upload")
    p.add_argument("--src")
    p.add_argument("--prefix", default="HEG - ", help="notebook title prefix (default 'HEG - ')")
    p.add_argument("--only", action="append", help="only courses whose folder name contains this text (repeatable)")
    p.add_argument("--cli", help="path to the notebooklm executable if it is not on PATH")
    p.add_argument("--dry", action="store_true", help="show what would be uploaded")
    p.set_defaults(fn=cmd_nlm_upload)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
