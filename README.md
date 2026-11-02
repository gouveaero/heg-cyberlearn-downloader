# HEG CyberLearn downloader

Download **all the files of all your courses** from CyberLearn (the Moodle used by HEG Genève / HES-SO)
into a normal folder on your computer, then, if you want, put that folder in **Google Drive** and/or load it
into **NotebookLM**.

- You sign in yourself in a real browser window (SWITCH edu-ID, 2FA included). **Your password is never read or stored.**
- It finds your courses automatically. No course ids to type.
- Files are organised as `Course / Week (section) / file`. Each course also gets `_course-notes.md` with the
  page text: descriptions, deadlines, assignment instructions, links, forum announcements.
- Run it again any time: **only new or replaced files are downloaded**. If a teacher replaces a file keeping the same
  name, you get both (the new one is named `... (updated dd-mm).pdf`).
- Nothing is uploaded anywhere unless you choose to (Google Drive / NotebookLM are optional steps).

> For your own study. Course materials belong to HEG and your teachers: don't redistribute them, and check the
> school's rules before feeding them to AI tools.

## Decide what you want first

| I want... | Do this |
|---|---|
| Just the files on my computer | Steps 1 to 3 below. Done. |
| The files also in Google Drive | Step 4. Easiest: download straight into a folder that Google Drive for desktop syncs. See [docs/google-drive.md](docs/google-drive.md). |
| To ask questions about the material in NotebookLM | Step 5. See [docs/notebooklm.md](docs/notebooklm.md). |

You can combine them. Drive and NotebookLM are independent: you don't need Drive to use NotebookLM.

## Quick start

You need Python 3.10+ ([install guide for Mac / Windows / Linux](docs/install.md)). Then, in a terminal inside this folder:

```bash
# 1. One-time setup (Mac/Linux; Windows commands are in docs/install.md)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# 2. Sign in (a browser window opens; log in with edu-ID, then it closes by itself)
python heg.py login

# 3. See your courses, then download everything
python heg.py courses
python heg.py download --out ~/HEG-Materials
```

`--out` is where the files go. Choose any folder you like (your Desktop, an external disk, a Google Drive folder).
The next runs remember it, so later you only type `python heg.py download`.

### Choosing what to download

```bash
python heg.py courses                          # prints "id  name" for each course
python heg.py download --course 46185          # only this course (repeat --course for several)
python heg.py download --exclude 4981          # everything except this one
python heg.py download --participants          # also save the class lists (off by default: other people's names)
```

### Updating during the semester

Your session expires after a while (hours to days). When a command says *Session expired*, run
`python heg.py login` again and repeat the command. Nothing is lost or downloaded twice.

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python heg.py login
python heg.py download
```

## 4. Google Drive (optional)

Short version: set `--out` to a folder inside **Google Drive for desktop** and Drive uploads it for you. Other options
(web upload, command line with rclone) are in [docs/google-drive.md](docs/google-drive.md).

## 5. NotebookLM (optional)

NotebookLM takes a limited number of sources per notebook and only some file types, so first make a clean copy:

```bash
python heg.py notebooklm-pack          # creates <your folder>-notebooklm/<Course>/ with flat, compatible files
```

Then create one notebook per course at <https://notebooklm.google.com> and drag the files in
(details, limits, and an optional automatic upload in [docs/notebooklm.md](docs/notebooklm.md)).

## What is in each file here

| File | Purpose |
|---|---|
| `heg.py` | The whole tool (login, list, download, NotebookLM helpers) |
| `requirements.txt` | Python packages: requests, beautifulsoup4, playwright |
| `docs/install.md` | Installing Python and the packages on Mac, Windows, Linux |
| `docs/google-drive.md` | Three ways to get the folder into Google Drive |
| `docs/notebooklm.md` | Loading the material into NotebookLM, manual and automatic |
| `docs/troubleshooting.md` | Common errors and fixes |

## How it works (for the curious)

1. `login` opens Chromium with a private profile stored in `~/.heg-downloader/`. You sign in; the tool waits until
   Moodle reports a logged-in user and saves the session cookie (`~/.heg-downloader/cookie.json`, readable only by you).
2. `courses` / `download` use that cookie like your browser would: they read the dashboard, every course page, and
   follow each resource, folder, assignment, page and forum link to fetch the attached files.
3. A small `.heg-manifest.json` inside each course folder records what was fetched, so reruns skip it.

Delete `~/.heg-downloader/` to remove the saved session at any time. The code only uses standard Moodle pages, so it
may work on other Moodle sites: set the environment variable `HEG_BASE_URL=https://your-moodle.example` (untested).

## Limits

- Videos hosted on external players (Panopto, Switch tube, Teams recordings) are saved as links in
  `_course-notes.md`, not downloaded. Files uploaded directly to CyberLearn are downloaded.
- Quizzes/tests are saved as text pages only.
- The tool reads what is visible to you, nothing more. Hidden or not-yet-released content is not downloaded.
