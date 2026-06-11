# Jade The Cleaner — Annotation Cleanup Toolbar

A pyRevit toolbar for cleaning up annotation clutter in Revit floor plans:
repositioning safe tags, detecting overlaps, removing duplicate tags, and
flagging the messy spots that need a human.

Everything works on the **active view only** — open the plan you want to clean
before clicking anything.

Every action is wrapped in one transaction, so **Ctrl+Z undoes the whole batch**.

---

## Before you start

- `lib\jade_report.py` must stay in the `lib` folder at the extension root.
  All the report viewers and most buttons depend on it.
- If you edit `jade_report.py`, **fully restart Revit** (not just Reload) —
  the module is cached for the whole session.
- Most buttons show a confirmation popup first and a result popup at the end.
  Some also open a **report window** with clickable links; if you don't see it,
  Alt+Tab or check the taskbar — it sometimes opens behind Revit.

---

## Recommended workflow

1. **Flag All Conflicts** — see the whole picture first (changes nothing).
2. **Delete Duplicate Wall Tag** — remove redundant tags (same wall tagged twice).
3. Run the movers: **Move Room Tags**, **Other tag Move**, **Space Wall Tags**,
   **Move Leadered Dim Text**.
4. **Flag All Conflicts** again — whatever still shows up is your manual list.
5. Fix the leftovers (dimensions, elevation/section markers) by hand.

The tool aims to clean **70–85%** automatically. The rest is meant to be manual.

---

## Buttons by panel

### BIGBOSS.panel

**Flag All Conflicts** *(read-only)*
Scans the active view and produces one report with three sections: duplicate
tags (same host), all overlapping annotation pairs, and the flag-only elements
(dimensions, elevations, sections, callouts) caught in any overlap. Selects the
flag-only elements so you can tab through them. Run this first and last.

---

### Roomtag.panel

**No. Room Tags**
Counts the room tags in the active view. Quick sanity check.

**Do I Overlap** *(read-only)*
Detects every overlapping annotation pair in the view and lists them with
clickable links. Changes nothing — just shows you where the problems are.

**Move Room Tags** *(moves elements)*
Repositions room tags that overlap something. Only moves a tag to a spot where
it stays **fully inside its room**. Tags that can't fit anywhere clean (small
closets, etc.) are left untouched and flagged for manual review.

---

### MoveOther.panel

**Other tag Move** *(moves elements)*
Nudges door, window, text, generic, and keynote tags that overlap something.
Small nudges only. Tags it can't improve are left where they are and flagged.

**Space Wall Tags** *(moves elements)*
Spreads out wall tags that overlap, keeping a real gap between them (not just
touching). Run **Delete Duplicate Wall Tag first** — two tags on the same wall
can't be spaced apart, only deleted.

**Delete Duplicate Wall Tag** *(deletes elements)*
Finds walls tagged more than once and deletes the extras, keeping one tag per
wall. Shows a diagnostic of what it found, then asks to confirm before deleting.
Which duplicate it keeps is arbitrary — glance at the result, Ctrl+Z if needed.

**View Duplicates** *(read-only)*
Lists duplicate tags (two tags pointing at the same element) across all tag
types. Selects the extras so you can review and delete them yourself. Never
deletes automatically. Note: two tags with the same *text* on *different*
elements are NOT duplicates and won't be flagged.

---

### Dimension Texts.panel

**Nudge Dimensions Text** *(moves text only)*
Moves the *text* of overlapping dimensions a small amount — never the dimension
line or its references. Elevation markers are never touched. Dimensions whose
text the API can't move (ordinate / spot-slope / equality types) are listed as
manual-drag-only.

**Move Leadered Dim Text** *(moves text only)*
For dimensions with adjustable/leadered text: moves the text to the nearest open
space and lets the leader stretch to follow, preferring the more open side so the
leader stays short. The leader *path* is drawn by Revit and can't be routed by
script, so a few may still need a quick manual drag.

---

### Report.panel

**View Last Report**
Reopens the most recent report with clickable element links.

**View Report History**
Lists all past reports (timestamped) and lets you reopen any one.

**Check Report Lib**
Diagnostic. Confirms `jade_report.py` is loaded correctly and writable.
Run this if the report viewers ever stop working.

Reports are saved to `C:\Users\<you>\JadeToolsReports` as timestamped files.

---

### Test.Panel (diagnostics — keep or delete)

**What Is This** — select an element, shows its category, class, and what it tags.
**Dim Text Test** — select a dimension, tests whether its text can be moved.
**Dim Leader Test** — select a dimension, checks its leader/text-position members.

These were built for troubleshooting. Handy to keep, safe to delete.

---

## Safe vs. manual — the rule

**Safe to auto-move:** room tags, door/window/text/generic tags, wall tags,
duplicate wall tags (delete), adjustable dimension *text*.

**Never auto-moved (flag only):** dimension *lines*, elevation markers, section
markers, callouts. These carry drawing references and intentional placement —
the tool points you at them, but you fix them by hand. That's by design.
