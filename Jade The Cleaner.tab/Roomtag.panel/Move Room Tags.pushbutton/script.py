# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List

doc    = revit.doc
view   = doc.ActiveView
output = script.get_output()
output.set_title("Move Room Tags")

BUFFER = 0.0   # extra gap in FEET counted as overlap

def bic(n):
    return getattr(DB.BuiltInCategory, n, None)

ALL = ['OST_RoomTags','OST_DoorTags','OST_WindowTags','OST_TextNotes',
       'OST_GenericAnnotation','OST_KeynoteTags','OST_WallTags',
       'OST_FurnitureTags','OST_MechanicalEquipmentTags','OST_PlumbingFixtureTags',
       'OST_Dimensions','OST_Sections','OST_Elev','OST_Callouts']
cats = [bic(n) for n in ALL if bic(n)]

def get_bb(e):
    try:    return e.get_BoundingBox(view)
    except: return None

def overlap(a, b, buf):
    if a is None or b is None: return False
    if a.Max.X + buf < b.Min.X or b.Max.X + buf < a.Min.X: return False
    if a.Max.Y + buf < b.Min.Y or b.Max.Y + buf < a.Min.Y: return False
    return True

def count_overlaps(bb, others):
    if bb is None: return 9999
    return sum(1 for o in others if overlap(bb, o, BUFFER))

def move_xy(tag, target):
    loc = tag.Location
    if loc is None: return
    cur = loc.Point
    vec = DB.XYZ(target.X - cur.X, target.Y - cur.Y, 0.0)
    if vec.GetLength() > 1e-9:
        DB.ElementTransformUtils.MoveElement(doc, tag.Id, vec)
        doc.Regenerate()

def tag_fully_inside(tag, room, z):
    """True only if all four corners of the tag's box are inside the room."""
    bb = get_bb(tag)
    if bb is None:
        return False
    corners = [
        DB.XYZ(bb.Min.X, bb.Min.Y, z),
        DB.XYZ(bb.Max.X, bb.Min.Y, z),
        DB.XYZ(bb.Min.X, bb.Max.Y, z),
        DB.XYZ(bb.Max.X, bb.Max.Y, z),
    ]
    for c in corners:
        try:
            if not room.IsPointInRoom(c):
                return False
        except:
            return False
    return True

def room_num(tag):
    try:
        if tag.Room:
            return tag.Room.Number
    except:
        pass
    return "?"

# --- collect ---
multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()

room_tags = [e for e in elems
             if e.Category and e.Category.Id.IntegerValue == int(bic('OST_RoomTags'))]

if not forms.alert("This will reposition room tags in '{}'.\n"
                   "Only tags that currently overlap something are moved, and only "
                   "to a spot where the tag stays FULLY inside the room.\n"
                   "Tags that can't fully fit are left untouched and flagged.\n\n"
                   "Continue? (Ctrl+Z undoes the whole batch.)"
                   .format(view.Name),
                   yes=True, no=True, title="Move Room Tags"):
    script.exit()

moved   = []   # (tag, before, after)
flagged = []   # (tag, before, reason)

with revit.Transaction("Move Room Tags"):
    for tag in room_tags:
        try:
            room = tag.Room
        except:
            room = None
        if room is None or room.Location is None:
            continue
        rbb = get_bb(room)
        if rbb is None:
            continue

        others = [get_bb(o) for o in elems if o.Id != tag.Id]
        others = [b for b in others if b is not None]

        before = count_overlaps(get_bb(tag), others)
        if before == 0:
            continue   # already clean, leave it alone

        base = room.Location.Point
        z    = base.Z
        sx   = (rbb.Max.X - rbb.Min.X) * 0.22
        sy   = (rbb.Max.Y - rbb.Min.Y) * 0.22
        candidates = [
            base,
            DB.XYZ(base.X,      base.Y + sy, z),
            DB.XYZ(base.X,      base.Y - sy, z),
            DB.XYZ(base.X + sx, base.Y,      z),
            DB.XYZ(base.X - sx, base.Y,      z),
            DB.XYZ(base.X + sx, base.Y + sy, z),
            DB.XYZ(base.X - sx, base.Y + sy, z),
            DB.XYZ(base.X + sx, base.Y - sy, z),
            DB.XYZ(base.X - sx, base.Y - sy, z),
        ]

        original = tag.Location.Point   # remember where it started

        best_pt, best_score = None, None
        for c in candidates:
            move_xy(tag, c)                          # move first so bbox updates
            if not tag_fully_inside(tag, room, z):   # reject if text spills out
                continue
            s = count_overlaps(get_bb(tag), others)
            if best_score is None or s < best_score:
                best_score = s
                best_pt = c
            if s == 0:
                break

        if best_pt is not None:
            move_xy(tag, best_pt)
            moved.append((tag, before, best_score))
        else:
            move_xy(tag, original)                   # no fully-contained spot -> put it back
            flagged.append((tag, before, "no position keeps tag fully inside room"))

# --- report ---
output.print_md("# Room Tag Cleanup")
output.print_md("**View:** {}  |  **Room tags:** {}  |  **Moved:** {}  |  **Flagged:** {}"
                .format(view.Name, len(room_tags), len(moved), len(flagged)))

output.print_md("---")
output.print_md("## Moved")
if not moved:
    output.print_md("_None._")
for tag, b, a in moved:
    output.print_md("- {} Room {} — overlaps **{} -> {}**".format(
        output.linkify(tag.Id), room_num(tag), b, a))

output.print_md("---")
output.print_md("## Flagged for manual review (left untouched)")
if not flagged:
    output.print_md("_None._")
for tag, b, reason in flagged:
    output.print_md("- {} Room {} — overlaps **{}** — {}".format(
        output.linkify(tag.Id), room_num(tag), b, reason))

forms.alert("Moved {} tag(s). Flagged {} for manual review.\n"
            "See the report window — flagged tags are listed with links.\n"
            "Ctrl+Z undoes everything."
            .format(len(moved), len(flagged)), title="Move Room Tags")