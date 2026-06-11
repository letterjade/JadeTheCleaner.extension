# -*- coding: utf-8 -*-
from pyrevit import forms

lines = []
try:
    import jade_report
    lines.append("import jade_report: OK")
    lines.append("file: " + getattr(jade_report, "__file__", "?"))
    lines.append("render_and_save present: " + str(hasattr(jade_report, "render_and_save")))
    lines.append("load_latest present: " + str(hasattr(jade_report, "load_latest")))
    try:
        d = jade_report.save_report("Diagnostic", "test",
                                    [{"heading": "ok", "items": []}], "write test")
        lines.append("save_report: OK (file written)")
    except Exception as e2:
        lines.append("save_report FAILED: " + str(e2))
    try:
        d = jade_report.load_latest()
        lines.append("existing report: " + ("found" if d else "none yet"))
    except Exception as e3:
        lines.append("load_latest FAILED: " + str(e3))
except Exception as e:
    lines.append("IMPORT FAILED: " + str(e))

forms.alert("\n".join(lines), title="Check Report Lib")