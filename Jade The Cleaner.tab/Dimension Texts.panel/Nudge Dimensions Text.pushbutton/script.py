# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView

# Required clear gap (in FEET) between a dimension's TEXT and anything else.
# ~0.03 ft = ~3/8". Raise it if you want text to sit further from neighbours.
GAP_DIM = 0.03

def bic(n): return getattr(DB.BuiltInCategory, n, None)

# everything a dimension's text might clash with
ALL = ['OST_Dimensions','OST_Elev','OST_Sections','OST_Callouts','OST_WallTags',
       'OST_DoorTags','OST_WindowTags','OST_RoomTags','OST_TextNotes',
       'OST_GenericAnnotation','OST_KeynoteTags']
cats = [bic(n) for n in ALL if bic(n)]
DIM_ID = int(bic('OST_Dimensions'))

def get_bb(e):
    try: return e.get_BoundingBox(view)
    except: return None

def segments(dim):
    """A dimension may be single- or multi-segment. Yield each segment object
    (each carries its own TextPosition). Single-segment dims carry it directly."""
    try:
        segs = dim.Segments
        if segs and segs.Size > 0:
            return [s for s in segs]
    except: pass
    return [dim]

def text_is_settable(dim):
    """LinearDimension TextPosition THROWS for SpotSlope, equality-formula, and
    ordinate dimensions - Revit exposes no movable text point for those.
    Probe by reading it; a throw means the API cannot move this one at all."""
    try:
        for seg in segments(dim):
            _ = seg.TextPosition       # raises for the unsupported types
        return True
    except:
        return False

# --- collect ---
multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()
all_dims = [e for e in elems if e.Category and e.Category.Id.IntegerValue == DIM_ID]

# split: ones we can touch vs ones the API refuses (ordinate/spot-slope/equality)
unsettable = [d for d in all_dims if not text_is_settable(d)]
dims       = [d for d in all_dims if text_is_settable(d)]

if not forms.alert("Nudge the TEXT of overlapping dimensions in '{}'?\n\n"
                   "Only the dimension TEXT moves - the dimension line and its "
                   "references are NOT touched, and elevation/section markers are "
                   "never moved.\n\n"
                   "Note: {} dimension(s) are ordinate / spot-slope / equality types "
                   "that Revit won't let any script move - those get listed as "
                   "manual-drag-only.\n\n"
                   "Continue? (Ctrl+Z undoes everything.)"
                   .format(view.Name, len(unsettable)),
                   yes=True, no=True, title="Nudge Dimension Text"):
    script.exit()

moved, flagged, skipped = [], [], 0

with revit.Transaction("Nudge Dimension Text"):
    for dim in dims:
        bb = get_bb(dim)
        if bb is None:
            continue

        # boxes of everything except this dimension
        others = [get_bb(o) for o in elems if o.Id != dim.Id]
        others = [b for b in others if b is not None]

        # quick skip: if the whole dimension box is clear, nothing to do
        clear = True
        for o in others:
            if not (bb.Max.X < o.Min.X or o.Max.X < bb.Min.X or
                    bb.Max.Y < o.Min.Y or o.Max.Y < bb.Min.Y):
                clear = False
                break
        if clear:
            continue

        # text size from the dimension type (fallback if unavailable)
        try:
            th = dim.DimensionType.get_Parameter(
                DB.BuiltInParameter.TEXT_SIZE).AsDouble()
        except:
            th = 0.01
        if not th or th <= 0:
            th = 0.01

        improved_any = False
        before_flag = False

        for seg in segments(dim):
            try:
                base = seg.TextPosition
            except:
                skipped += 1
                continue
            if base is None:
                skipped += 1
                continue

            # estimate this segment's text footprint
            try:
                txt = seg.ValueString or ""
            except:
                txt = "0000"
            half_h = max(th, 0.008)
            half_w = max(len(txt) * th * 0.4, 0.02)

            def text_overlaps(center):
                """Count boxes that intrude on the text footprint around `center`."""
                tminx, tmaxx = center.X - half_w, center.X + half_w
                tminy, tmaxy = center.Y - half_h, center.Y + half_h
                n = 0
                for o in others:
                    if tmaxx + GAP_DIM < o.Min.X or o.Max.X + GAP_DIM < tminx:
                        continue
                    if tmaxy + GAP_DIM < o.Min.Y or o.Max.Y + GAP_DIM < tminy:
                        continue
                    n += 1
                return n

            start_score = text_overlaps(base)
            if start_score == 0:
                continue  # this segment's text is already clear
            before_flag = True

            # search outward in rings; try SIDEWAYS first (better for marker clashes)
            dx = max(half_w * 2.0, 0.05)
            dy = max(half_h * 3.0, 0.05)
            cands = []
            for ring in (1, 2, 3, 4, 5, 6):
                rx, ry = dx * ring, dy * ring
                cands += [
                    DB.XYZ(base.X + rx, base.Y,      base.Z),   # right
                    DB.XYZ(base.X - rx, base.Y,      base.Z),   # left
                    DB.XYZ(base.X,      base.Y + ry, base.Z),   # up
                    DB.XYZ(base.X,      base.Y - ry, base.Z),   # down
                    DB.XYZ(base.X + rx, base.Y + ry, base.Z),
                    DB.XYZ(base.X - rx, base.Y + ry, base.Z),
                    DB.XYZ(base.X + rx, base.Y - ry, base.Z),
                    DB.XYZ(base.X - rx, base.Y - ry, base.Z)]

            best_pt, best_score = None, start_score
            for c in cands:
                s = text_overlaps(c)
                if s < best_score:
                    best_score, best_pt = s, c
                if s == 0:
                    break

            if best_pt is not None:
                try:
                    seg.TextPosition = best_pt
                    doc.Regenerate()
                    improved_any = True
                except:
                    pass
            # if no better spot found, leave text where it was (no harm)

        if improved_any:
            moved.append(dim)
        elif before_flag:
            flagged.append(dim)

# --- report ---
sections = [
    {"heading": "Dimension text nudged clear", "items": [
        {"id": d.Id.IntegerValue, "text": "Dimension text moved off neighbour"}
        for d in moved]},
    {"heading": "Flagged - text couldn't clear (likely the dimension LINE overlaps, "
                "or no open space; fix by hand)", "items": [
        {"id": d.Id.IntegerValue, "text": "Dimension - manual review"}
        for d in flagged]},
    {"heading": "Cannot move via API - ordinate / spot-slope / equality dims "
                "(drag the text grip by hand in Revit)", "items": [
        {"id": d.Id.IntegerValue, "text": "Dimension - manual drag only"}
        for d in unsettable]},
]
summary = ("**Dimensions:** {}  |  **Text nudged:** {}  |  **Flagged:** {}  |  "
           "**API-unmovable:** {}  |  **Segments w/o movable text:** {}  |  "
           "**Gap:** {} ft").format(
           len(all_dims), len(moved), len(flagged), len(unsettable), skipped, GAP_DIM)
data = jade_report.save_report("Nudge Dimension Text", view.Name, sections, summary)

out = script.get_output()
jade_report.render(data, out)
try:
    out.show(); out.window.TopMost = True; out.window.Activate(); out.window.TopMost = False
except: pass

forms.alert("Nudged text on {} dimension(s).\nFlagged {} for manual review.\n"
            "{} are ordinate/spot-slope/equality dims the API can't move - drag "
            "those by hand.\nSee View Last Report for the clickable list."
            .format(len(moved), len(flagged), len(unsettable)),
            title="Nudge Dimension Text")