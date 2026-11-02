# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Not signed in yet` | Run `python heg.py login` first. |
| `Session expired` in the middle of a download | Normal after some hours/days. `python heg.py login`, then repeat the same command; finished files are skipped. |
| `login` window opens but the script never says "Signed in" | Finish the whole edu-ID flow (including 2FA) until you see the CyberLearn dashboard with your name at the top right. It waits 15 min. Don't close the window. |
| `No courses found` | Not actually signed in, or the dashboard has no enrolled courses yet. Open <https://cyberlearn.hes-so.ch/my/courses.php> in the login window and check. As a workaround, find the id in a course URL (`.../course/view.php?id=12345`) and use `--course 12345`. |
| `Missing Python package ...` | The venv is not active. `source .venv/bin/activate` (Windows: `.venv\Scripts\Activate.ps1`), then `pip install -r requirements.txt`. |
| `python: command not found` (Mac/Linux) | Use `python3` outside the venv; inside the venv `python` works. |
| `playwright install` fails / no browser opens | Use the cookie fallback at the end of [install.md](install.md). On Linux try `python -m playwright install-deps chromium`. |
| A course shows `N errors (see _errors.txt)` | Open `<Course>/_errors.txt`. Usually a single page that timed out; run `download` again, it retries only what is missing. |
| A file is in CyberLearn but not on disk | It may be an external video/link (see `_course-notes.md`), or released after your last run. Run again. If it persists, open the activity in your browser and download it by hand. |
| Names look odd / too long | Characters illegal on Windows/Mac (`/ : * ? " < > |`) are replaced by spaces and names are shortened to 100 characters. |
| I moved or renamed files and now they download again | The manifest is keyed by the original path. Don't move files inside the download folder; copy them elsewhere (or delete `.heg-manifest.json` accepting duplicates). |
| Want to start over for one course | Delete that course's folder and rerun. |
| Want to forget my login | Delete the folder `~/.heg-downloader` (Windows: `C:\Users\<you>\.heg-downloader`). |
| Wi-Fi blocks Google domains (some school networks) | NotebookLM audio/video downloads and Google sign-in can fail on filtered networks. Switch to a phone hotspot. |

## Still stuck?

Run the failing command again and read the last lines of output. If a download misbehaves, send the contents of
`<Course>/_errors.txt` (it contains no passwords) to whoever helps you with the repo.
