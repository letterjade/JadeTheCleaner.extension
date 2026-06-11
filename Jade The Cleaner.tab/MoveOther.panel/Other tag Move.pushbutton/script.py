# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView
BUFFER = 0.0

def bic(n): return getattr(DB.BuiltInCategory, n, None)

SIMPLE = ['OST_DoorTags','OST_WindowTags','OST_TextNotes','OST_GenericAnnotation',
          'OST_KeynoteTags','OST_WallTags','OST_FurnitureTags',
          'OST_MechanicalEquipmentTags','OST_PlumbingFixtureTags']
ALL = SIMPLE + ['OST_RoomTags','OST_Dimensions','OST_Sections','OST_Elev','OST_Callouts']
simple_ids = set(int(bic(n)) for n in SIMPLE if bic(n))
cats = [bic(n) for n in ALL if bic(n)]

def get_bb(e):
    try: return e.get_BoundingBox(view)
    except: return None

def overlap(a, b, buf):
    if a is None or b is None: return False
    if a.Max.X + buf < b.Min.X or b.Max.X + buf < a.Min.X: return False
    if a.Max.Y + buf < b.Min.Y or b.Max.Y + buf < a.Min.Y: return False
    return True

def count_overlaps(bb, others):
    if bb is None: return 9999
    return sum(1 for o in others if overlap(bb, o, BUFFER))

def get_anchor(e):
    try: return e.TagHeadPosition
    except: pass
    try: return e.Coord
    except: pass
    loc = None
    try: loc = e.Location
    except: loc = None
    if isinstance(loc, DB.LocationPoint): return loc.Point
    bb = get_bb(e)
    if bb is not None:
        return DB.XYZ((bb.Min.X+bb.Max.X)/2.0, (bb.Min.Y+bb.Max.Y)/2.0, (bb.Min.Z+bb.Max.Z)/2.0)
    return None

def move_xy(e, target):
    cur = get_anchor(e)
    if cur is None or target is None: return
    vec = DB.XYZ(target.X - cur.X, target.Y - cur.Y, 0.0)
    if vec.GetLength() > 1e-9:
        DB.ElementTransformUtils.MoveElement(doc, e.Id, vec)
        doc.Regenerate()

def cat_name(e):
    try: return e.Category.Name
    except: return "Tag"

multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()
simple_tags = [e for e in elems
               if e.Category and e.Category.Id.IntegerValue in simple_ids]

if not forms.alert("Nudge door/window/text/generic tags in '{}'? Only overlapping tags "
                   "move, and only if a small nudge helps. (Ctrl+Z undoes everything.)"
                   .format(view.Name), yes=True, no=True, title="Nudge Simple Tags"):
    script.exit()

moved, flagged = [], []
with revit.Transaction("Nudge Simple Tags"):
    for tag in simple_tags:
        bb = get_bb(tag)
        if bb is None: continue
        others = [b for b in (get_bb(o) for o in elems if o.Id != tag.Id) if b is not None]
        before = count_overlaps(bb, others)
        if before == 0: continue
        cur = get_anchor(tag)
        if cur is None: continue
        original = cur
        dx = max((bb.Max.X - bb.Min.X) * 0.6, 0.05)
        dy = max((bb.Max.Y - bb.Min.Y) * 0.9, 0.05)
        candidates = [
            DB.XYZ(cur.X+dx, cur.Y, cur.Z), DB.XYZ(cur.X-dx, cur.Y, cur.Z),
            DB.XYZ(cur.X, cur.Y+dy, cur.Z), DB.XYZ(cur.X, cur.Y-dy, cur.Z),
            DB.XYZ(cur.X+dx, cur.Y+dy, cur.Z), DB.XYZ(cur.X-dx, cur.Y+dy, cur.Z),
            DB.XYZ(cur.X+dx, cur.Y-dy, cur.Z), DB.XYZ(cur.X-dx, cur.Y-dy, cur.Z)]
        best_pt, best_score = None, before
        for c in candidates:
            move_xy(tag, c)
            s = count_overlaps(get_bb(tag), others)
            if s < best_score:
                best_score, best_pt = s, c
            if s == 0: break
        if best_pt is not None:
            move_xy(tag, best_pt)
            moved.append((tag, before, best_score))
        else:
            move_xy(tag, original)
            flagged.append((tag, before))

sections = [
    {"heading": "Nudged", "items": [
        {"id": t.Id.IntegerValue, "text": "{} — overlaps {} -> {}".format(cat_name(t), b, a)}
        for (t, b, a) in moved]},
    {"heading": "Flagged (couldn't improve, left untouched)", "items": [
        {"id": t.Id.IntegerValue, "text": "{} — overlaps {}".format(cat_name(t), b)}
        for (t, b) in flagged]},
]
summary = "**Simple tags:** {}  |  **Nudged:** {}  |  **Flagged:** {}".format(
    len(simple_tags), len(moved), len(flagged))
jade_report.render_and_save("Nudge Simple Tags", view.Name, sections, summary)

forms.alert("Nudged {}, flagged {}. Use View Last Report to reopen the list."
            .format(len(moved), len(flagged)), title="Nudge Simple Tags")