# Installation

Everything runs from a terminal inside this folder. Total: about 5 minutes and ~300 MB (Python packages + the
browser Playwright uses for the login window).

## 0. Get the code

Either `git clone <repo-url>` or download the ZIP from GitHub and unzip it. Open a terminal **inside** that folder.

- **Mac:** Terminal app (Cmd+Space, type "Terminal"). Tip: type `cd ` then drag the folder into the window.
- **Windows:** open the folder in File Explorer, click the address bar, type `powershell`, Enter.
- **Linux:** any terminal.

## 1. Python 3.10 or newer

Check: `python3 --version` (Mac/Linux) or `python --version` (Windows).

- **Mac:** `brew install python` (needs [Homebrew](https://brew.sh)), or the installer from <https://www.python.org/downloads/>.
- **Windows:** installer from <https://www.python.org/downloads/>. **Tick "Add python.exe to PATH"** on the first screen.
  (Microsoft Store Python also works.)
- **Linux (Debian/Ubuntu):** `sudo apt install python3 python3-venv python3-pip`

## 2. Create an isolated environment and install packages

**Mac / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell refuses to run the activate script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer Y, retry.
(In `cmd.exe` use `.venv\Scripts\activate.bat`.)

**Linux extra:** if Chromium complains about missing libraries, run `python -m playwright install-deps chromium`.

Your prompt now starts with `(.venv)`. You must **re-activate it in every new terminal** before using `heg.py`:
`source .venv/bin/activate` (Mac/Linux) or `.venv\Scripts\Activate.ps1` (Windows).

## 3. Check it works

```bash
python heg.py --help
```

You should see the list of commands. Continue with `python heg.py login` in the [README](../README.md).

## No Playwright? (fallback login)

If Chromium will not install (locked-down laptop), skip `python -m playwright install chromium` and sign in with your
normal browser instead:

1. Log in to <https://cyberlearn.hes-so.ch> in Chrome/Edge/Firefox.
2. Open developer tools (F12) → **Application** (Chrome/Edge) or **Storage** (Firefox) → **Cookies** → `cyberlearn.hes-so.ch`.
3. Copy the **Value** of the cookie named `MoodleSession`.
4. `python heg.py set-cookie "PASTE_VALUE_HERE"`
5. `python heg.py courses` to test.

Treat that value like a password: anyone with it can act as you until it expires. Don't paste it into chats or commit it.
