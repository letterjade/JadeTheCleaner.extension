# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import jade_report

doc  = revit.doc
view = doc.ActiveView

SCALE = view.Scale if (view.Scale and view.Scale > 0) else 100

def bic(n): return getattr(DB.BuiltInCategory, n, None)

ALL = ['OST_Dimensions','OST_Elev','OST_Sections','OST_Callouts','OST_WallTags',
       'OST_DoorTags','OST_WindowTags','OST_RoomTags','OST_TextNotes',
       'OST_GenericAnnotation','OST_KeynoteTags']
cats = [bic(n) for n in ALL if bic(n)]
DIM_ID = int(bic('OST_Dimensions'))

def get_bb(e):
    try: return e.get_BoundingBox(view)
    except: return None

def segments(dim):
    try:
        segs = dim.Segments
        if segs and segs.Size > 0:
            return [s for s in segs]
    except: pass
    return [dim]

def adjustable(seg):
    try: return bool(seg.IsTextPositionAdjustable())
    except:
        try: return bool(seg.IsTextPositionAdjustable)
        except: return False

def model_text_size(dim):
    th = 0.008
    try:
        v = dim.DimensionType.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).AsDouble()
        if v and v > 0: th = v
    except: pass
    return th * SCALE

def text_halfsize(dim, value_string):
    mh = model_text_size(dim)
    half_h = max(mh * 0.6, 0.05)
    n = max(len(value_string), 1)
    half_w = max(n * mh * 0.35, 0.05)
    return half_w, half_h

def box_at(cx, cy, hw, hh):
    return (cx - hw, cy - hh, cx + hw, cy + hh)

# --- collect ---
multi = DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](cats))
elems = DB.FilteredElementCollector(doc, view.Id) \
    .WherePasses(multi).WhereElementIsNotElementType().ToElements()
all_dims = [e for e in elems if e.Category and e.Category.Id.IntegerValue == DIM_ID]

def build_obstacles(exclude_id):
    """Element bounding boxes PLUS every dimension's TEXT footprint (scaled)."""
    obs = []
    for o in elems:
        if o.Id == exclude_id: continue
        b = get_bb(o)
        if b is None: continue
        obs.append((b.Min.X, b.Min.Y, b.Max.X, b.Max.Y))
    for d in all_dims:
        if d.Id == exclude_id: continue
        for s in segments(d):
            try:    tp = s.TextPosition
            except: continue
            if tp is None: continue
            try:    txt = s.ValueString or ""
            except: txt = "0"
            hw, hh = text_halfsize(d, txt)
            obs.append(box_at(tp.X, tp.Y, hw, hh))
    return obs

def hits(box, obstacles, gap):
    minx, miny, maxx, maxy = box
    n = 0
    for (ox0, oy0, ox1, oy1) in obstacles:
        if maxx + gap < ox0 or ox1 + gap < minx: continue
        if maxy + gap < oy0 or oy1 + gap < miny: continue
        n += 1
    return n

if not forms.alert("Move adjustable dimension TEXT to the nearest clear space in "
                   "'{}' (1:{})?\nPrefers the more OPEN side so the leader runs "
                   "through clear area and stays short. Dimension lines, references "
                   "and elevation markers are NOT touched.\n\n"
                   "Note: the leader PATH is drawn by Revit and can't be routed by "
                   "script - a few may still need a quick manual drag.\n\n"
                   "Continue? (Ctrl+Z undoes everything.)".format(view.Name, SCALE),
                   yes=True, no=True, title="Move Leadered Dim Text"):
    script.exit()

moved, flagged, not_adjustable = [], [], []

with revit.Transaction("Move Leadered Dim Text"):
    for dim in all_dims:
        bb = get_bb(dim)
        if bb is None: continue
        obstacles = build_obstacles(dim.Id)
        mh = model_text_size(dim)
        GAP = mh * 0.5

        any_adjustable = False
        improved_any = False
        before_flag = False

        for seg in segments(dim):
            if not adjustable(seg):
                continue
            any_adjustable = True
            try:    base = seg.TextPosition
            except: continue
            if base is None: continue

            try:    txt = seg.ValueString or ""
            except: txt = "0"
            hw, hh = text_halfsize(dim, txt)

            start = hits(box_at(base.X, base.Y, hw, hh), obstacles, GAP)
            if start == 0:
                continue
            before_flag = True

            step = max(mh * 1.2, 0.2)

            # figure out which horizontal side has open space
            def side_clear(sign):
                c = DB.XYZ(base.X + sign * step * 3, base.Y, base.Z)
                return hits(box_at(c.X, c.Y, hw, hh), obstacles, GAP) == 0
            right_open = side_clear(1)
            left_open  = side_clear(-1)
            hsign = 1 if (right_open or not left_open) else -1

            # search nearest ring first; on the open side first
            best_pt = None
            for ring in range(1, 9):       # up to 8 rings (~MAX travel)
                r = step * ring
                ring_cands = [
                    DB.XYZ(base.X + hsign * r, base.Y,     base.Z),   # open side
                    DB.XYZ(base.X + hsign * r, base.Y + r, base.Z),
                    DB.XYZ(base.X + hsign * r, base.Y - r, base.Z),
                    DB.XYZ(base.X,             base.Y + r, base.Z),   # vertical
                    DB.XYZ(base.X,             base.Y - r, base.Z),
                    DB.XYZ(base.X - hsign * r, base.Y,     base.Z),   # other side last
                ]
                for c in ring_cands:
                    if hits(box_at(c.X, c.Y, hw, hh), obstacles, GAP) == 0:
                        best_pt = c
                        break
                if best_pt is not None:
                    break

            if best_pt is not None:
                try:
                    seg.TextPosition = best_pt
                    doc.Regenerate()
                    improved_any = True
                    obstacles = build_obstacles(dim.Id)   # refresh for next dims
                except: pass
            # no clear spot within reach -> leave it, gets flagged

        if not any_adjustable:
            not_adjustable.append(dim)
        elif improved_any:
            moved.append(dim)
        elif before_flag:
            flagged.append(dim)

# --- report ---
sections = [
    {"heading": "Text moved to nearest open side (leader follows)", "items": [
        {"id": d.Id.IntegerValue, "text": "Dimension text relocated"} for d in moved]},
    {"heading": "Adjustable but no clear space within reach (fix by hand)", "items": [
        {"id": d.Id.IntegerValue, "text": "Dimension - manual review"} for d in flagged]},
    {"heading": "Non-adjustable text (ordinate / spot-slope / equality - drag by hand)",
     "items": [{"id": d.Id.IntegerValue, "text": "Dimension - manual drag only"}
               for d in not_adjustable]},
]
summary = ("**Dimensions:** {}  |  **Moved:** {}  |  **Flagged:** {}  |  "
           "**Non-adjustable:** {}  |  **Scale:** 1:{}").format(
           len(all_dims), len(moved), len(flagged), len(not_adjustable), SCALE)
data = jade_report.save_report("Move Leadered Dim Text", view.Name, sections, summary)

out = script.get_output()
jade_report.render(data, out)
try:
    out.show(); out.window.TopMost = True; out.window.Activate(); out.window.TopMost = False
except: pass

forms.alert("Scale 1:{}. Moved {} text(s) to the open side, flagged {}, "
            "non-adjustable {}.\nSee View Last Report.".format(
            SCALE, len(moved), len(flagged), len(not_adjustable)),
            title="Move Leadered Dim Text")