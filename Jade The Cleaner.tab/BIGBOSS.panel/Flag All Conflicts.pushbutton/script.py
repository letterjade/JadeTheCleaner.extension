# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView
BUFFER = 0.0

def bic(n): return getattr(DB.BuiltInCategory, n, None)

# tags we can check for true duplicates (same host)
TAG_CATS = ['OST_DoorTags','OST_WindowTags','OST_WallTags','OST_RoomTags',
            'OST_FurnitureTags','OST_KeynoteTags','OST_GenericAnnotation',
            'OST_MechanicalEquipmentTags','OST_PlumbingFixtureTags',
            'OST_SpecialityEquipmentTags']
# the "never auto-move, manual fix" family
FLAG_ONLY = ['OST_Dimensions','OST_Sections','OST_Elev','OST_Callouts']
# everything participates in overlap detection
ALL = TAG_CATS + FLAG_ONLY + ['OST_TextNotes']

tag_ids  = set(int(bic(n)) for n in TAG_CATS if bic(n))
flag_ids = set(int(bic(n)) for n in FLAG_ONLY if bic(n))
cats = [bic(n) for n in ALL if bic(n)]

def get_bb(e):
    try: return e.get_BoundingBox(view)
    except: return None

def overlap(a, b, buf):
    if a is None or b is None: return False
    if a.Max.X + buf < b.Min.X or b.Max.X + buf < a.Min.X: return False
    if a.Max.Y + buf < b.Min.Y or b.Max.Y + buf < a.Min.Y: return False
    return True

def cat_name(e):
    try: return e.Category.Name
    except: return "Annotation"

def cat_id(e):
    try: return e.Category.Id.IntegerValue
    except: return None

def host_key(tag):
    try:
        ids = list(tag.GetTaggedLocalElementIds())   # Revit 2022+
        if ids: return (tag.Category.Id.IntegerValue,
                        tuple(sorted(i.IntegerValue for i in ids)))
    except: pass
    try:
        tid = tag.TaggedLocalElementId               # older API
        if tid and tid.IntegerValue > 0:
            return (tag.Category.Id.IntegerValue, tid.IntegerValue)
    except: pass
    try:
        if tag.Room: return ("ROOM", tag.Room.Id.IntegerValue)
    except: pass
    return None

def tag_text(tag):
    try:
        t = tag.TagText
        if t: return t
    except: pass
    return cat_name(tag)

# --- collect ---
multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()

bbs = [(e, get_bb(e)) for e in elems]
no_box = [e for (e, b) in bbs if b is None]
bbs = [(e, b) for (e, b) in bbs if b is not None]

# --- 1. duplicate tags (same host) ---
groups = {}
for e in elems:
    if cat_id(e) in tag_ids:
        k = host_key(e)
        if k is None: continue
        groups.setdefault(k, []).append(e)
dupe_items = []
dupe_groups = 0
for k, g in groups.items():
    if len(g) > 1:
        dupe_groups += 1
        dupe_items.append({"id": g[0].Id.IntegerValue,
                           "text": "'{}' KEEP (tagged {}x)".format(tag_text(g[0]), len(g))})
        for t in g[1:]:
            dupe_items.append({"id": t.Id.IntegerValue,
                               "text": "'{}' EXTRA - review & delete".format(tag_text(t))})

# --- 2. all overlapping pairs ---
pair_items = []
flagonly_hit = {}   # flag-only elements caught in any overlap
for i in range(len(bbs)):
    ea, ba = bbs[i]
    for j in range(i + 1, len(bbs)):
        eb, bb = bbs[j]
        if overlap(ba, bb, BUFFER):
            pair_items.append({"id": ea.Id.IntegerValue,
                               "text": "{} overlaps {} (id {})".format(
                                   cat_name(ea), cat_name(eb), eb.Id.IntegerValue)})
            for e in (ea, eb):
                if cat_id(e) in flag_ids:
                    flagonly_hit[e.Id.IntegerValue] = e

# --- 3. flag-only manual-fix pile ---
flag_items = [{"id": e.Id.IntegerValue,
               "text": "{} - manual fix (do not auto-move)".format(cat_name(e))}
              for e in flagonly_hit.values()]

sections = [
    {"heading": "Duplicate tags (same host)", "items": dupe_items},
    {"heading": "Overlapping pairs (all annotations)", "items": pair_items},
    {"heading": "Flag-only elements in conflict (dimensions / elevations / sections / callouts)",
     "items": flag_items},
]
summary = ("**Scanned:** {} (no box: {})  |  **Dup groups:** {}  |  "
           "**Overlap pairs:** {}  |  **Manual-fix elements:** {}").format(
           len(bbs), len(no_box), dupe_groups, len(pair_items), len(flag_items))

data = jade_report.save_report("Flag All Conflicts", view.Name, sections, summary)
out = script.get_output()
jade_report.render(data, out)
try:
    out.show(); out.window.TopMost = True; out.window.Activate(); out.window.TopMost = False
except: pass

# select the flag-only manual-fix elements so you can tab through them
if flagonly_hit:
    try: revit.get_selection().set_to(list(flagonly_hit.values()))
    except: pass

forms.alert("Duplicate tag groups: {}\nOverlapping pairs: {}\nManual-fix elements: {}\n\n"
            "Manual-fix elements are selected. Full clickable list in View Last Report."
            .format(dupe_groups, len(pair_items), len(flag_items)),
            title="Flag All Conflicts")