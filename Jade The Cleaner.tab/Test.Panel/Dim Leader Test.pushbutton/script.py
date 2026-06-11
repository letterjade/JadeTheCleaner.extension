# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms

doc = revit.doc
sel = revit.get_selection()
if not sel:
    forms.alert("Select the leadered 7555 dimension first, then run.",
                title="Dim Leader Test")
else:
    dim = list(sel)[0]
    lines = ["Class: " + dim.GetType().Name]

    # is it actually leadered / free text?
    for prop in ("HasLeader",):
        try: lines.append(prop + ": " + str(getattr(dim, prop)))
        except Exception as e: lines.append(prop + ": n/a (" + str(e) + ")")

    # which text-position properties exist and are readable?
    for prop in ("TextPosition", "LeaderEndPosition"):
        try:
            v = getattr(dim, prop)
            lines.append(prop + " READ: ({:.3f}, {:.3f})".format(v.X, v.Y))
        except Exception as e:
            lines.append(prop + " READ: throws - " + str(e)[:60])

    # list any settable members with 'text' or 'leader' in the name
    members = []
    for name in dir(dim):
        low = name.lower()
        if "leader" in low or ("text" in low and "position" in low):
            members.append(name)
    lines.append("Relevant members: " + ", ".join(members))

    forms.alert("\n".join(lines), title="Dim Leader Test")