# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List

doc    = revit.doc
view   = doc.ActiveView
output = script.get_output()
output.set_title("Overlap Report")

BUFFER = 0.0   # extra gap in FEET that still counts as overlap. Try 0.05 if too few hits.

def bic(n):
    return getattr(DB.BuiltInCategory, n, None)

MOVABLE   = ['OST_RoomTags','OST_DoorTags','OST_WindowTags','OST_TextNotes',
             'OST_GenericAnnotation','OST_KeynoteTags','OST_WallTags',
             'OST_FurnitureTags','OST_MechanicalEquipmentTags','OST_PlumbingFixtureTags']
FLAG_ONLY = ['OST_Dimensions','OST_Sections','OST_Elev','OST_Callouts']
cats = [bic(n) for n in (MOVABLE + FLAG_ONLY) if bic(n)]

def get_bb(e):
    try:    return e.get_BoundingBox(view)
    except: return None

def overlap(a, b, buf):
    if a is None or b is None: return False
    if a.Max.X + buf < b.Min.X or b.Max.X + buf < a.Min.X: return False
    if a.Max.Y + buf < b.Min.Y or b.Max.Y + buf < a.Min.Y: return False
    return True

def name_of(e):
    try:    return e.Category.Name
    except: return "Annotation"

try:
    multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
    elems = DB.FilteredElementCollector(doc, view.Id) \
        .WherePasses(multi).WhereElementIsNotElementType().ToElements()

    bbs    = [(e, get_bb(e)) for e in elems]
    no_box = [e for (e, b) in bbs if b is None]
    bbs    = [(e, b) for (e, b) in bbs if b is not None]

    pairs = []
    for i in range(len(bbs)):
        ea, ba = bbs[i]
        for j in range(i + 1, len(bbs)):
            eb, bb = bbs[j]
            if overlap(ba, bb, BUFFER):
                pairs.append((ea, eb))

    output.print_md("# Overlap Report")
    output.print_md("**View:** {}".format(view.Name))
    output.print_md("**Boxed:** {}  |  **No box (skipped):** {}  |  **Overlapping pairs:** {}"
                    .format(len(bbs), len(no_box), len(pairs)))
    output.print_md("---")
    if not pairs:
        output.print_md("No overlapping bounding boxes found. "
                        "If the plan looks messy, raise BUFFER to 0.05 and re-run.")
    for ea, eb in pairs:
        output.print_md("- {} {}  vs  {} {}".format(
            name_of(ea), output.linkify(ea.Id),
            name_of(eb), output.linkify(eb.Id)))

    forms.alert("Scanned {} annotations, found {} overlapping pairs.\n\n"
                "Click the links in the Overlap Report window to jump to each one."
                .format(len(bbs), len(pairs)), title="Detect Overlaps")

except Exception:
    import traceback
    output.print_md("## ERROR")
    output.print_md("```\n{}\n```".format(traceback.format_exc()))
    forms.alert("Script hit an error — see the Overlap Report window.", title="Detect Overlaps")