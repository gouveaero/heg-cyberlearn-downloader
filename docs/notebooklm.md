# Using the material in NotebookLM

[NotebookLM](https://notebooklm.google.com) (Google) answers questions, makes summaries, quizzes, flashcards and audio
overviews **from the sources you load into a notebook**. You don't need Google Drive to use it, and you can use Drive
without it.

## Recommended structure

**One notebook per course** (e.g. `HEG - International Trade`). Mixing courses makes answers vague and hits the source limit.

## What NotebookLM accepts (check the current list in the app)

| Supported as file | Not supported (convert first) |
|---|---|
| PDF, TXT, Markdown (.md), DOCX, PPTX*, audio files | XLSX, ZIP, images, video files, old .doc/.ppt |

\* Google keeps adding formats. If a file is rejected, open it and **Save as PDF**, or upload it to Drive and open it as
a Google Doc/Slides, which NotebookLM can also import directly ("Add source → Google Drive").

Limits at the time of writing (they change, see the in-app help): **50 sources per notebook on the free plan**
(more on paid plans), each source up to **500,000 words or 200 MB**. A course with many weekly PDFs can exceed 50: load the
current term's material first, or merge related PDFs (Print → Save as PDF, or any PDF merge tool).

## Step 1: make a clean, flat copy of your downloads

```bash
python heg.py notebooklm-pack
```

This creates `<your download folder>-notebooklm/<Course>/` containing only compatible files, with the week prefixed in
the name (`Week 3 - Slides.pdf`) because NotebookLM shows a flat list. It prints a warning when a course has more than 50
files and writes `_not-included.txt` listing what was left out. `_course-notes.md` is included on purpose: it has the
deadlines and assignment descriptions, so you can ask "what is due next week?".

## Option A (no extra software): drag and drop

1. Go to <https://notebooklm.google.com> → **Create new**.
2. Drag all files from one `<Course>` folder into the *Add sources* window (you can select many at once).
3. Rename the notebook (`HEG - <Course>`). Repeat per course.

Tips: ask in the language you want the answer in; start with "Summarise the syllabus and list every graded deliverable
with its date", then use the *Studio* panel for audio overview, quiz, flashcards, mind map.

## Option B (optional, unofficial): automatic upload

For people comfortable with a terminal. It uses [`notebooklm-py`](https://github.com/teng-lin/notebooklm-py), an
**unofficial** open-source CLI that drives NotebookLM with your own Google login. It can break when Google changes things
and its use is at your own risk. Skip it if you don't need it.

```bash
pip install "notebooklm-py[browser]"                  # same venv as heg.py is fine
python -m playwright install chromium                 # already done if you followed install.md
notebooklm login                                      # browser opens, sign in to Google, then press ENTER in the terminal
notebooklm list                                       # sanity check: prints your notebooks
python heg.py notebooklm-upload --dry                 # preview: what would be created/added
python heg.py notebooklm-upload                       # creates "HEG - <Course>" notebooks and adds the files
python heg.py notebooklm-upload --only "Supply Chain" # just one course
```

It never deletes sources; it skips files whose names are already in the notebook, so you can run it again after each
`download`. If `notebooklm` is not on your PATH, pass `--cli /full/path/to/notebooklm`.

If `login` asks "Save authentication anyway? [y/N]" (Google sometimes lands on a different NotebookLM address), answer `y`.
If the CLI cannot be installed or acts up, fall back to Option A: it takes a few minutes per course.

## After the semester

NotebookLM notebooks are independent of your local folder. Keep the downloaded folder (or the Drive copy) as the archive of
record, because CyberLearn courses are usually hidden after the term.
