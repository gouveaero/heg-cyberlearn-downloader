# Getting the files into Google Drive

Google Drive is optional. Pick **one** of the three options.

## Option A (easiest): download straight into a Drive-synced folder

1. Install **Google Drive for desktop**: <https://www.google.com/drive/download/> and sign in.
2. Find the Drive folder on your computer:
   - Mac: `~/Library/CloudStorage/GoogleDrive-<your email>/My Drive/`
   - Windows: the `G:` drive (or whichever letter Drive uses) → `My Drive`
3. Create a folder there, e.g. `HEG`, and download into it:

   ```bash
   python heg.py download --out "/path/to/My Drive/HEG"
   ```

   Mac example: `--out "$HOME/Library/CloudStorage/GoogleDrive-you@gmail.com/My Drive/HEG"`

4. Drive uploads the files in the background. In Drive for desktop settings, "Stream files" is fine; if you want the
   files **also on this laptop**, right-click the folder → *Offline access* → *Available offline* (or choose
   "Mirror files").

Re-running `download` later only adds new files, and Drive syncs just those.

## Option B: download locally, then upload in the browser

1. `python heg.py download --out ~/HEG-Materials`
2. Open <https://drive.google.com> → **New → Folder upload** → pick `HEG-Materials`.

Simple, but for updates you have to upload the new files by hand (the `(updated dd-mm)` suffix and the manifest help you
spot them; sort the folder by modified date).

## Option C: command line with rclone (automatic, repeatable)

Good if you update every week and don't want Drive for desktop.

1. Install rclone: <https://rclone.org/install/> (`brew install rclone` on Mac, `winget install Rclone.Rclone` on Windows).
2. `rclone config` → `n` (new remote) → name `gdrive` → storage `drive` → press Enter through the defaults →
   a browser opens to authorise. (Use scope `drive` for full access, or `drive.file` if you only want rclone to touch
   files it creates.)
3. Copy (adds new files, never deletes anything on Drive):

   ```bash
   rclone copy ~/HEG-Materials "gdrive:HEG" --progress --exclude ".heg-manifest.json"
   ```

4. Verify: `rclone check ~/HEG-Materials "gdrive:HEG" --one-way --exclude ".heg-manifest.json"`

Use `rclone copy`, not `rclone sync`: `sync` deletes from the destination whatever is missing locally.

## Tips

- Keep the folder structure: NotebookLM and your own search work better when files stay under `Course / Week`.
- Drive does not index PDFs of scanned slides well; that has nothing to do with this tool.
- If your Drive is full (15 GB free), check the size first: `du -sh ~/HEG-Materials` (Mac/Linux).
