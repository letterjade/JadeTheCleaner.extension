# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms

doc = revit.doc
sel = revit.get_selection()
if not sel:
    forms.alert("Select the 7555 dimension first, then run.", title="Dim Text Test")
else:
    dim = list(sel)[0]
    lines = ["Class: " + dim.GetType().Name]
    try:
        base = dim.TextPosition
        lines.append("TextPosition readable: YES  ({:.3f}, {:.3f})".format(base.X, base.Y))
    except Exception as e:
        base = None
        lines.append("TextPosition readable: NO - " + str(e))

    # try to actually shove it 2 ft to the right and see if it sticks
    if base is not None:
        target = DB.XYZ(base.X + 2.0, base.Y, base.Z)
        with revit.Transaction("test move dim text"):
            try:
                dim.TextPosition = target
                doc.Regenerate()
                after = dim.TextPosition
                moved = abs(after.X - base.X)
                lines.append("After forcing +2.0 ft right: moved {:.3f} ft".format(moved))
                if moved < 0.1:
                    lines.append(">> Revit SNAPPED IT BACK. Text is pinned to the line.")
                else:
                    lines.append(">> Move STUCK. Text is free to move - it's a scoring issue.")
            except Exception as e:
                lines.append("Assignment THREW: " + str(e))
        # undo the test move
        try:
            with revit.Transaction("undo test"):
                dim.TextPosition = base
                doc.Regenerate()
        except: pass
    forms.alert("\n".join(lines), title="Dim Text Test")