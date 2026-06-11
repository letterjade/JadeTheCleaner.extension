# -*- coding: utf-8 -*-
import os, json, codecs, glob, datetime
from pyrevit import script
from Autodesk.Revit.DB import ElementId

REPORT_DIR = os.path.join(os.path.expanduser("~"), "JadeToolsReports")

def _dir():
    if not os.path.isdir(REPORT_DIR):
        try: os.makedirs(REPORT_DIR)
        except: pass
    return REPORT_DIR

def save_report(title, view_name, sections, summary=""):
    stamp = datetime.datetime.now()
    data = {"title": title, "view": view_name,
            "time": stamp.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary, "sections": sections}
    fname = "report_{}.json".format(stamp.strftime("%Y%m%d_%H%M%S"))
    try:
        with codecs.open(os.path.join(_dir(), fname), "w", "utf-8") as f:
            json.dump(data, f)
    except: pass
    return data

def list_reports():
    """Newest first. Returns list of (filepath, label)."""
    files = glob.glob(os.path.join(_dir(), "report_*.json"))
    files.sort(reverse=True)   # timestamp in name sorts chronologically
    out = []
    for fp in files:
        try:
            with codecs.open(fp, "r", "utf-8") as f:
                d = json.load(f)
            out.append((fp, "{}  —  {}  ({})".format(
                d.get("time", "?"), d.get("title", "?"), d.get("view", "?"))))
        except: pass
    return out

def load_path(fp):
    try:
        with codecs.open(fp, "r", "utf-8") as f:
            return json.load(f)
    except: return None

def load_latest():
    files = glob.glob(os.path.join(_dir(), "report_*.json"))
    if not files: return None
    files.sort(reverse=True)
    return load_path(files[0])

def render(data, output=None):
    out = output or script.get_output()
    if data is None:
        out.print_md("# No report yet")
        out.print_md("Run an Annotation cleanup button first, then come back here.")
        return out
    try: out.set_title(data.get("title", "Report"))
    except: pass
    out.print_md("# {}".format(data.get("title", "Report")))
    out.print_md("**View:** {}  |  **Run:** {}".format(
        data.get("view", "?"), data.get("time", "?")))
    if data.get("summary"):
        out.print_md(data["summary"])
    for sec in data.get("sections", []):
        out.print_md("---")
        out.print_md("## {}".format(sec.get("heading", "")))
        items = sec.get("items", [])
        if not items:
            out.print_md("_None._")
        for it in items:
            eid, text = it.get("id"), it.get("text", "")
            if eid:
                try:
                    out.print_md("- {} {}".format(out.linkify(ElementId(int(eid))), text))
                    continue
                except: pass
            out.print_md("- {}".format(text))
    try: out.show()
    except: pass
    return out

def render_and_save(title, view_name, sections, summary=""):
    return render(save_report(title, view_name, sections, summary))