# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
import jade_report

doc  = revit.doc
view = doc.ActiveView

WALLTAG = DB.BuiltInCategory.OST_WallTags

tags = list(DB.FilteredElementCollector(doc, view.Id)
            .OfCategory(WALLTAG).WhereElementIsNotElementType().ToElements())

def host_key(tag):
    try:
        ids = list(tag.GetTaggedLocalElementIds())      # Revit 2022+
        if ids: return tuple(sorted(i.IntegerValue for i in ids))
    except: pass
    try:
        tid = tag.TaggedLocalElementId                  # older API
        if tid and tid.IntegerValue > 0: return (tid.IntegerValue,)
    except: pass
    return None

groups = {}
nohost = 0
for t in tags:
    k = host_key(t)
    if k is None:
        nohost += 1
        continue
    groups.setdefault(k, []).append(t)

redundant = []
for k, g in groups.items():
    if len(g) > 1:
        redundant += g[1:]

# STEP 1 - always show what was found, before doing anything
forms.alert("DIAGNOSTIC\n"
            "Wall tags in view: {}\n"
            "Tags with no host: {}\n"
            "Unique hosts: {}\n"
            "Duplicate groups (host tagged >1x): {}\n"
            "Redundant tags to delete: {}".format(
                len(tags), nohost, len(groups),
                sum(1 for g in groups.values() if len(g) > 1),
                len(redundant)),
            title="Delete Duplicate Wall Tags - Step 1")

if not redundant:
    forms.alert("Nothing flagged as redundant. If you EXPECTED duplicates, the host "
                "lookup may be returning different ids - tell me and I'll adjust.",
                title="Delete Duplicate Wall Tags")
    script.exit()

# STEP 2 - confirm
go = forms.alert("About to DELETE {} redundant wall tag(s), keeping one per wall.\n\n"
                 "Ids to delete: {}\n\n"
                 "Proceed? (Ctrl+Z undoes everything.)".format(
                     len(redundant), [t.Id.IntegerValue for t in redundant]),
                 yes=True, no=True, title="Delete Duplicate Wall Tags - Confirm")
if not go:
    forms.alert("Cancelled - nothing deleted.", title="Delete Duplicate Wall Tags")
    script.exit()

# STEP 3 - delete
deleted, failed = [], []
with revit.Transaction("Delete Duplicate Wall Tags"):
    for t in redundant:
        tid = t.Id.IntegerValue
        try:
            doc.Delete(t.Id)
            deleted.append(tid)
        except Exception as e:
            failed.append((tid, str(e)))

sections = [
    {"heading": "Deleted", "items": [{"id": None, "text": "Wall tag id {}".format(i)}
                                     for i in deleted]},
    {"heading": "Failed to delete", "items": [{"id": None, "text": "id {} - {}".format(i, m)}
                                              for (i, m) in failed]},
]
summary = "**Wall tags:** {}  |  **Deleted:** {}  |  **Failed:** {}".format(
    len(tags), len(deleted), len(failed))
jade_report.render_and_save("Delete Duplicate Wall Tags", view.Name, sections, summary)

forms.alert("Deleted {} tag(s). Failed {}.\nCtrl+Z undoes it.".format(
    len(deleted), len(failed)), title="Delete Duplicate Wall Tags - Done")