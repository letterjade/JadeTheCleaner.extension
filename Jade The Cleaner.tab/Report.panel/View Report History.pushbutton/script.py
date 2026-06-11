# -*- coding: utf-8 -*-
from pyrevit import forms, script
import jade_report

reports = jade_report.list_reports()   # newest first: (filepath, label)
if not reports:
    forms.alert("No reports saved yet.", title="View Report History")
    script.exit()

labels = [lbl for (fp, lbl) in reports]

# CommandSwitchWindow surfaces more reliably than SelectFromList on this setup
chosen = forms.CommandSwitchWindow.show(labels, message="Pick a report to view:")
if not chosen:
    script.exit()   # user cancelled / closed

fp = dict((lbl, fp) for (fp, lbl) in reports)[chosen]
data = jade_report.load_path(fp)
if data is None:
    forms.alert("Could not read that report file.", title="View Report History")
    script.exit()

# rich output window with clickable element links
out = script.get_output()
jade_report.render(data, out)
try:
    out.show()
    out.window.TopMost = True
    out.window.Activate()
    out.window.TopMost = False
except:
    pass

# guaranteed-visible summary (same mechanism that's been working for you)
lines = ["{}  ({})".format(data.get("title", "?"), data.get("time", "?")), ""]
for sec in data.get("sections", []):
    items = sec.get("items", [])
    lines.append("{}: {}".format(sec.get("heading", ""), len(items)))
    for it in items[:8]:
        lines.append("  - " + it.get("text", ""))
    if len(items) > 8:
        lines.append("  ...and {} more (see output window)".format(len(items) - 8))
forms.alert("\n".join(lines),
            title="View Report History (output window may be behind Revit)")