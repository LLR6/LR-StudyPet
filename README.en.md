# LR StudyPet · Xingli v0.4.0


**A blue anime desktop companion that helps you return to your next small step.**

[简体中文](README.md) · [Download Windows beta](https://github.com/LLR6/LR-StudyPet/releases) · [Report a problem](https://github.com/LLR6/LR-StudyPet/issues)

![Study space](preview.png)

## New in v0.4

Event-driven Windows keyboard reactions, alternating hand taps and highlighted keys, smooth idle/sleep transitions, and continuous state GIFs. A local Workshop imports, previews, creates, switches and exports data-only PNG/GIF/WebP pet packs with seven optional action states.

One idle image is enough for a breathing character with a keyboard overlay. Full pose animation requires separate assets; the app does not generate an animation rig from a photo. No online marketplace or built-in cloud image generation.

[Workshop guide](docs/WORKSHOP.md) · The Chinese display name is 星梨桌宠. GitHub repository slugs cannot contain Chinese characters, so the existing URL is retained.

## Study features

- Five-minute restart using your interruption bookmark.
- 28-day activity grid and Markdown weekly reports.
- UTF-8 CSV review-card import/export with validation and duplicate skipping.
- Custom subjects; historical subjects remain visible.
- Multi-monitor pet positioning and recovery after screen removal.

CSV headers: `question,answer,subject`. CSV exports card content; JSON backups retain schedules.

Independent companion tools: [ResumeDock](companions/LR-ResumeDock) for interruption bookmarks and a restart dock, and [DeskTidy](companions/LR-DeskTidy) for previewed, selective, undoable file organization. Separate repositories have not been created yet. Windows artifacts are built in Actions.

## Why another desktop pet?

A timer tells you when to stop. Xingli also helps you remember where to restart:
leave a resume bookmark, log the exact step that blocked you, and turn the mistake into a recall card for tomorrow.

## What it does

- Transparent, draggable anime companion with reading, rest, celebration and idle poses.
- Keyboard reactions: enable the setting and the pet taps a little keyboard while you type. No typed characters are decoded or saved.
- Previous clipboard text: opt in to a memory-only 60-second buffer, restore the previous item, or clear it instantly. No disk history.
- Desktop organization advice: scan one folder level, group by extension and flag large files or similarly named items. Suggestions only; no file movement.
- Command palette: `Ctrl+Alt+Space` on Windows, search in Chinese or by command prefix, inspect explanations and copy. No command execution or terminal interception.
- Focus/break timer, pause/resume, tasks, daily targets, custom countdown and local reminders.
- Resume bookmarks, five offline stuck-point guides, spaced recall cards and study journals.
- Subject statistics, XP, configurable pet size, gentle reminders, rain noise and optional startup after Windows login.
- Optional AI question-and-answer via an HTTPS Chat Completions compatible endpoint.

## Download and run

Download the Windows ZIP from Releases. **Extract the entire archive**, open the folder and run `Start.cmd`.
Do not run the launcher from inside the ZIP or move it away from the rest of the package.
Beta builds are created on Windows and gate publication on unit tests plus source and packaged GUI smoke tests. This is not a claim that every Windows setup has been tested.

## Privacy by design

Keyboard interaction reads activity only. Clipboard text lives in memory and expires after 60 seconds; this does not clear the Windows clipboard itself. Desktop filenames remain local. AI receives only messages explicitly entered in its chat box. No screenshot capture, shell execution, keyboard text logging or cloud sync.

## Development

Python 3.12 + PySide6 Essentials + SQLite.

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python app.py
```

Set `LR_PET_API_KEY` locally only if you want online chat. Select your provider URL and model in settings. Online chat may incur provider charges.

## Boundaries

The character uses four generated poses plus procedural overlay effects, not a Live2D rig. Command suggestions are a curated catalog, not a model reading your terminal. Global keyboard reactions, hotkeys, notifications, rain sound and startup are Windows features. No uniqueness claim: the distinctive part is connecting resume bookmarks, energy-aware tasks and recall practice.

MIT application code; see THIRD_PARTY.md for dependencies. Created and maintained by LR.
