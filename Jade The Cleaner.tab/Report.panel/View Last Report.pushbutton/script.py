# -*- coding: utf-8 -*-
from pyrevit import forms, script
import jade_report

data = jade_report.load_latest()
if data is None:
    forms.alert("No report saved yet. Run a cleanup button first.", title="View Last Report")
    script.exit()

# render into the output window (clickable links live here)
out = script.get_output()
jade_report.render(data, out)

# force the window to the front - the part your setup needs
try:
    out.show()
    out.window.TopMost = True
    out.window.Activate()
    out.window.TopMost = False
except:
    pass

# guaranteed-visible fallback summary so you ALWAYS see the result
lines = ["{}  ({})".format(data.get("title", "?"), data.get("time", "?")), ""]
for sec in data.get("sections", []):
    items = sec.get("items", [])
    lines.append("{}: {}".format(sec.get("heading", ""), len(items)))
    for it in items[:8]:
        lines.append("  - " + it.get("text", ""))
    if len(items) > 8:
        lines.append("  ...and {} more (see output window)".format(len(items) - 8))
forms.alert("\n".join(lines),
            title="View Last Report (output window opened behind Revit if not visible)")