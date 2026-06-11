# -*- coding: utf-8 -*-
from pyrevit import forms

HELP = """JADE THE CLEANER - Annotation Cleanup Toolbar

Works on the ACTIVE VIEW only. Open the plan you want to clean first.
Ctrl+Z undoes the whole batch for any button.

------------------------------------------------------------
RECOMMENDED WORKFLOW
------------------------------------------------------------
1. Flag All Conflicts    - see the whole picture (changes nothing)
2. Delete Duplicate Wall Tag
3. Movers: Move Room Tags, Other tag Move, Space Wall Tags,
   Move Leadered Dim Text
4. Flag All Conflicts again - whatever remains is your manual list
5. Fix leftover dimensions / elevation markers by hand

Aim: clean 70-85% automatically. The rest is meant to be manual.

------------------------------------------------------------
BIGBOSS
------------------------------------------------------------
Flag All Conflicts (read-only)
   One report: duplicate tags, all overlapping pairs, and the
   flag-only elements (dimensions/elevations/etc) in conflict.
   Selects those so you can tab through them. Run first and last.

------------------------------------------------------------
ROOMTAG
------------------------------------------------------------
No. Room Tags        - counts room tags in the view.
Do I Overlap (read-only) - lists every overlapping pair.
Move Room Tags       - moves overlapping room tags to a clear spot
                       INSIDE the room. Won't-fit ones are flagged.

------------------------------------------------------------
MOVE OTHER
------------------------------------------------------------
Other tag Move       - nudges door/window/text/generic tags that
                       overlap. Can't-improve ones are flagged.
Space Wall Tags      - spreads wall tags apart with a real gap.
                       Run Delete Duplicate Wall Tag FIRST.
Delete Duplicate Wall Tag - deletes extra tags on the same wall,
                       keeping one. Confirms before deleting.
View Duplicates (read-only) - lists tags pointing at the same
                       element; selects extras for you to delete.

------------------------------------------------------------
DIMENSION TEXTS
------------------------------------------------------------
Nudge Dimensions Text - moves dimension TEXT only (never the line
                       or references). Ordinate/spot/equality dims
                       are listed as manual-drag-only.
Move Leadered Dim Text - moves adjustable/leadered dim text to the
                       nearest open space; the leader follows.
                       A few may still need a quick manual drag.

------------------------------------------------------------
REPORT - It doesnt pop up so you have to alt+tab and find it, 
then you can click each element it will zoom to it and you edit 
it manually.
------------------------------------------------------------
View Last Report     - reopens the most recent report (clickable).
View Report History  - pick any past report to reopen.
Check Report Lib     - diagnostic if the report viewers break.
Reports save to:  C:\\Users\\<you>\\JadeToolsReports

------------------------------------------------------------
SAFE vs MANUAL
------------------------------------------------------------
Auto-moved:  room tags, door/window/text/generic tags, wall tags,
             duplicate wall tags (delete), adjustable dim TEXT.
Flag only (never auto-moved): dimension LINES, elevation markers,
             section markers, callouts. The tool points you at
             them; you fix them by hand. By design.


"""

forms.alert(HELP, title="Jade The Cleaner - Help")