# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView

# REQUIRED GAP between tag boxes, in FEET. ~0.05 ft = 5/8". Raise for more space.
GAP = 0.05

def bic(n): return getattr(DB.BuiltInCategory, n, None)

ALL = ['OST_WallTags','OST_DoorTags','OST_WindowTags','OST_RoomTags','OST_TextNotes',
       'OST_GenericAnnotation','OST_KeynoteTags','OST_Dimensions','OST_Sections',
       'OST_Elev','OST_Callouts']
cats = [bic(n) for n in ALL if bic(n)]
WALLTAG_ID = int(bic('OST_WallTags'))

def get_bb(e):
    try: return e.get_BoundingBox(view)
    except: return None

def overlap(a, b, gap):
    """True if boxes are closer than `gap` apart (touching counts as overlap)."""
    if a is None or b is None: return False
    if a.Max.X + gap < b.Min.X or b.Max.X + gap < a.Min.X: return False
    if a.Max.Y + gap < b.Min.Y or b.Max.Y + gap < a.Min.Y: return False
    return True

def count_overlaps(bb, others):
    if bb is None: return 9999
    return sum(1 for o in others if overlap(bb, o, GAP))

def get_anchor(e):
    try: return e.TagHeadPosition
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

multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()
wall_tags = [e for e in elems if e.Category and e.Category.Id.IntegerValue == WALLTAG_ID]

if not forms.alert("Space out wall tags in '{}' with a real gap between boxes?\n"
                   "Tip: run Delete Duplicate Wall Tags FIRST - two tags on the same "
                   "wall can't be spaced apart, only deleted.\n\n"
                   "Continue? (Ctrl+Z undoes everything.)".format(view.Name),
                   yes=True, no=True, title="Space Wall Tags"):
    script.exit()

moved, flagged = [], []
with revit.Transaction("Space Wall Tags"):
    for tag in wall_tags:
        bb = get_bb(tag)
        if bb is None: continue
        others = [b for b in (get_bb(o) for o in elems if o.Id != tag.Id) if b is not None]
        before = count_overlaps(bb, others)
        if before == 0: continue

        cur = get_anchor(tag)
        if cur is None: continue
        original = cur
        w = bb.Max.X - bb.Min.X
        h = bb.Max.Y - bb.Min.Y
        # step = full tag size + the required gap, so one move clears the neighbour
        dx = max(w + GAP, 0.1)
        dy = max(h + GAP, 0.1)

        # search outward in bigger rings until a clear spot is found
        candidates = []
        for ring in (1, 2, 3, 4, 5):
            rx, ry = dx * ring, dy * ring
            candidates += [
                DB.XYZ(cur.X + rx, cur.Y,      cur.Z), DB.XYZ(cur.X - rx, cur.Y,      cur.Z),
                DB.XYZ(cur.X,      cur.Y + ry, cur.Z), DB.XYZ(cur.X,      cur.Y - ry, cur.Z),
                DB.XYZ(cur.X + rx, cur.Y + ry, cur.Z), DB.XYZ(cur.X - rx, cur.Y + ry, cur.Z),
                DB.XYZ(cur.X + rx, cur.Y - ry, cur.Z), DB.XYZ(cur.X - rx, cur.Y - ry, cur.Z)]

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
    {"heading": "Spaced", "items": [
        {"id": t.Id.IntegerValue, "text": "Wall tag - overlaps {} -> {}".format(b, a)}
        for (t, b, a) in moved]},
    {"heading": "Flagged (couldn't clear - likely duplicate on same wall, DELETE instead)",
     "items": [{"id": t.Id.IntegerValue, "text": "Wall tag - overlaps {}".format(b)}
               for (t, b) in flagged]},
]
summary = "**Wall tags:** {}  |  **Spaced:** {}  |  **Flagged:** {}  |  **Gap:** {} ft".format(
    len(wall_tags), len(moved), len(flagged), GAP)
jade_report.render_and_save("Space Wall Tags", view.Name, sections, summary)

forms.alert("Spaced {}, flagged {}. Flagged ones are likely duplicates on the same "
            "wall - run Delete Duplicate Wall Tags on those.\nSee View Last Report."
            .format(len(moved), len(flagged)), title="Space Wall Tags")