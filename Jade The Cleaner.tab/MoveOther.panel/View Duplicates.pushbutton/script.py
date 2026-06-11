# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView

def bic(n): return getattr(DB.BuiltInCategory, n, None)

TAG_CATS = ['OST_DoorTags','OST_WindowTags','OST_WallTags','OST_RoomTags',
            'OST_FurnitureTags','OST_KeynoteTags','OST_GenericAnnotation',
            'OST_MechanicalEquipmentTags','OST_PlumbingFixtureTags',
            'OST_SpecialityEquipmentTags']
cats = [bic(n) for n in TAG_CATS if bic(n)]

multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
tags = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()

def host_key(tag):
    """Identifies what the tag points at. Same host -> duplicates."""
    try:
        ids = list(tag.GetTaggedLocalElementIds())   # Revit 2022+
        if ids:
            return (tag.Category.Id.IntegerValue,
                    tuple(sorted(i.IntegerValue for i in ids)))
    except: pass
    try:
        tid = tag.TaggedLocalElementId               # older API
        if tid and tid.IntegerValue > 0:
            return (tag.Category.Id.IntegerValue, tid.IntegerValue)
    except: pass
    try:
        if tag.Room:                                 # RoomTag
            return ("ROOM", tag.Room.Id.IntegerValue)
    except: pass
    return None

def tag_text(tag):
    try:
        t = tag.TagText
        if t: return t
    except: pass
    try: return tag.Category.Name
    except: return "Tag"

# group by host
groups = {}
for t in tags:
    k = host_key(t)
    if k is None: continue
    groups.setdefault(k, []).append(t)

dupes = dict((k, v) for k, v in groups.items() if len(v) > 1)

# build report items; keep the first in each group, flag the rest
items = []
redundant = []
for k, group in dupes.items():
    keep = group[0]
    items.append({"id": keep.Id.IntegerValue,
                  "text": "'{}' — KEEP (tagged {}x)".format(tag_text(keep), len(group))})
    for t in group[1:]:
        items.append({"id": t.Id.IntegerValue,
                      "text": "'{}' — EXTRA, review & delete".format(tag_text(t))})
        redundant.append(t)

sections = [{"heading": "Duplicate tags (same host)", "items": items}]
summary = ("**Tags scanned:** {}  |  **Duplicate groups:** {}  |  **Redundant:** {}\n"
           "_Same tagged element = duplicate. Different elements with the same value "
           "are NOT flagged._").format(len(tags), len(dupes), len(redundant))

# save to history + render rich window
data = jade_report.save_report("View Duplicates", view.Name, sections, summary)
out = script.get_output()
jade_report.render(data, out)
try:
    out.show()
    out.window.TopMost = True
    out.window.Activate()
    out.window.TopMost = False
except:
    pass

# select the EXTRAS only (keepers stay unselected) for manual deletion
if redundant:
    try: revit.get_selection().set_to(redundant)
    except: pass

# guaranteed-visible summary
lines = ["Duplicate groups: {}".format(len(dupes)),
         "Redundant tags: {}".format(len(redundant)), ""]
for it in items[:10]:
    lines.append("  - " + it["text"])
if len(items) > 10:
    lines.appe